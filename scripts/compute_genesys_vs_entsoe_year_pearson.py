"""
GENeSYS-MOD vs ENTSO-E cross-year Pearson correlation.

For each (country, scenario, dimension, genesys_year, entsoe_year):
  - GENeSYS profile = group-mean prices for that specific year/scenario
  - ENTSO-E profile = group-mean prices for that specific year
  - Pearson r between the two k-element profile vectors

Input : results/intermediate/stage2_ttest_groups_detail.csv
Output: results/intermediate/genesys_vs_entsoe_year_pearson.csv
        results/intermediate/genesys_vs_entsoe_matched_year_pearson.csv
           (year-matched subset: genesys_year == entsoe_year, i.e. 2018 & 2025)

Columns: country, scenario, dimension, genesys_year, entsoe_year,
         pearson_r, p_value, n_groups
"""

import os
import sys
from pathlib import Path
import pandas as pd
from scipy.stats import pearsonr
import warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, str(Path(__file__).parent))
from config import COUNTRIES, SCENARIOS, GENESYS_YEARS

# ---------------------------------------------------------------------------
BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT      = os.path.join(BASE, 'results', 'intermediate',
                          'stage2_ttest_groups_detail.csv')
OUTPUT        = os.path.join(BASE, 'results', 'intermediate',
                             'genesys_vs_entsoe_year_pearson.csv')
OUTPUT_MATCHED = os.path.join(BASE, 'results', 'intermediate',
                              'genesys_vs_entsoe_matched_year_pearson.csv')

TIME_DIMS      = ['hour', 'weekday', 'month', 'season']
MIN_GROUPS     = 3

# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('=' * 70)
    print('GENeSYS-MOD vs ENTSO-E cross-year Pearson correlations')
    print('=' * 70)

    df = pd.read_csv(INPUT)

    # Build per-year profiles (no averaging across years)
    entsoe = (
        df[df['source'] == 'ENTSOE']
        .groupby(['country', 'year', 'dimension', 'group'])['mean_group']
        .mean()
        .reset_index()
        .rename(columns={'mean_group': 'entsoe_mean', 'year': 'entsoe_year'})
    )

    genesys = (
        df[
            (df['source'] == 'GENeSYS-MOD') &
            (df['year'].isin(GENESYS_YEARS))
        ]
        .groupby(['country', 'scenario', 'year', 'dimension', 'group'])['mean_group']
        .mean()
        .reset_index()
        .rename(columns={'mean_group': 'genesys_mean', 'year': 'genesys_year'})
    )

    rows = []
    for (country, scenario, g_year, dim), grp_g in genesys.groupby(
            ['country', 'scenario', 'genesys_year', 'dimension']):

        e_sub = entsoe[
            (entsoe['country']   == country) &
            (entsoe['dimension'] == dim)
        ]

        for e_year, grp_e in e_sub.groupby('entsoe_year'):
            merged = (
                pd.merge(
                    grp_e[['group', 'entsoe_mean']],
                    grp_g[['group', 'genesys_mean']],
                    on='group'
                )
                .sort_values('group')
                .dropna()
            )

            if len(merged) < MIN_GROUPS:
                continue

            r, p = pearsonr(merged['entsoe_mean'].values,
                            merged['genesys_mean'].values)
            rows.append({
                'country'     : country,
                'scenario'    : scenario,
                'dimension'   : dim,
                'genesys_year': g_year,
                'entsoe_year' : e_year,
                'pearson_r'   : round(r, 6),
                'p_value'     : p,
                'n_groups'    : len(merged),
            })

    result = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    result.to_csv(OUTPUT, index=False)
    print(f'\nExported {len(result):,} rows  ->  {OUTPUT}')

    # ── year-matched subset (genesys_year == entsoe_year) ────────────────────
    matched = (
        result[result['genesys_year'] == result['entsoe_year']]
        .rename(columns={'genesys_year': 'year'})
        .drop(columns=['entsoe_year'])
        .reset_index(drop=True)
    )
    matched.to_csv(OUTPUT_MATCHED, index=False)
    print(f'Exported {len(matched):,} rows (year-matched)  ->  {OUTPUT_MATCHED}')

    # ── summary ──────────────────────────────────────────────────────────────
    print('\nMean Pearson r (across countries & scenarios):')
    summary = (
        result
        .groupby(['dimension', 'genesys_year', 'entsoe_year'])['pearson_r']
        .mean()
        .round(3)
    )
    for dim in TIME_DIMS:
        print(f'\n  {dim}')
        sub = summary.loc[dim] if dim in summary.index.get_level_values(0) else None
        if sub is not None:
            print(sub.to_string())
