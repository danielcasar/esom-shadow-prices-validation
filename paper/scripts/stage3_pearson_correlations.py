"""
Stage 3: Profile-correlation analysis (Pearson r and Spearman ρ).

For each (country, scenario, dimension):
  - ENTSO-E profile  = group-mean prices averaged over all ENTSO-E years
  - GENeSYS profile  = group-mean prices averaged over all GENeSYS years
                       for that specific scenario  (scenarios kept separate)
  - Correlation of the two k-element profile vectors

A "profile" is the vector of group-mean prices for one temporal dimension
(e.g. 24 hourly means, 12 monthly means, …).

Input  : results/calendar_effects/stage2_ttest_groups_detail.csv
Output : results/calendar_effects/stage3_pearson_correlations.csv
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import COUNTRIES, SCENARIOS, GENESYS_YEARS, ENTSOE_YEARS
import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INPUT_FILE  = os.path.join(BASE, 'results', 'calendar_effects',
                           'stage2_ttest_groups_detail.csv')
OUTPUT_FILE = os.path.join(BASE, 'results', 'calendar_effects',
                           'stage3_pearson_correlations.csv')

TIME_DIMENSIONS = ['hour', 'weekday', 'month', 'season']
MIN_GROUPS      = 3


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _corr(x: pd.Series, y: pd.Series) -> dict:
    x, y   = x.values, y.values
    r,  pr = pearsonr(x, y)
    rho, ps = spearmanr(x, y)
    return {
        'pearson_r' : round(r,   6),
        'pearson_p' : pr,
        'spearman_r': round(rho, 6),
        'spearman_p': ps,
        'n_groups'  : len(x),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('=' * 70)
    print('Stage 3: Profile correlations (Pearson r / Spearman ρ)')
    print('=' * 70)

    df = pd.read_csv(INPUT_FILE)

    # ENTSO-E pooled profile: mean over all years per (country, dimension, group)
    entsoe_pooled = (
        df[df['source'] == 'ENTSOE']
        .groupby(['country', 'dimension', 'group'])['mean_group']
        .mean()
        .reset_index()
        .rename(columns={'mean_group': 'entsoe_mean'})
    )

    # GENeSYS profile: mean over years, per (country, scenario, dimension, group)
    genesys_by_scenario = (
        df[df['source'] == 'GENeSYS-MOD']
        .groupby(['country', 'scenario', 'dimension', 'group'])['mean_group']
        .mean()
        .reset_index()
        .rename(columns={'mean_group': 'genesys_mean'})
    )

    rows = []
    for (country, scenario, dim), grp_g in genesys_by_scenario.groupby(
            ['country', 'scenario', 'dimension']):

        grp_e = entsoe_pooled[
            (entsoe_pooled['country']   == country) &
            (entsoe_pooled['dimension'] == dim)
        ]

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

        c = _corr(merged['entsoe_mean'], merged['genesys_mean'])
        rows.append({
            'country'  : country,
            'scenario' : scenario,
            'dimension': dim,
            **c,
        })

    result = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    result.to_csv(OUTPUT_FILE, index=False)
    print(f'\nExported {len(result):,} rows  ->  {OUTPUT_FILE}')

    # ---- Summary -----------------------------------------------------------
    print('\nMean correlations per scenario × dimension:')
    for scenario in result['scenario'].unique():
        print(f'\n  {scenario}')
        sub = result[result['scenario'] == scenario]
        for dim in TIME_DIMENSIONS:
            d = sub[sub['dimension'] == dim]
            if d.empty:
                continue
            print(f'    {dim:8s}:  '
                  f'mean r={d["pearson_r"].mean():+.4f}  '
                  f'mean ρ={d["spearman_r"].mean():+.4f}  '
                  f'(n={len(d)} countries)')

    # =========================================================================
    # Year-specific hour-of-day correlations:
    #   GENeSYS years : 2025, 2030
    #   ENTSO-E years : 2024, 2025
    #   Dimension     : hour only
    # =========================================================================
    YEAR_OUTPUT_FILE = os.path.join(
        BASE, 'results', 'calendar_effects',
        'stage3_pearson_hour_year_specific.csv'
    )

    print('\n' + '=' * 70)
    print('Year-specific hour-of-day correlations (GENeSYS 2025/2030 vs ENTSO-E 2024/2025)')
    print('=' * 70)

    genesys_years = [2025, 2030]
    entsoe_years  = [2024, 2025]

    hour_df = df[df['dimension'] == 'hour'].copy()

    # Per-year group-mean profiles (no averaging across years)
    entsoe_hour = (
        hour_df[
            (hour_df['source'] == 'ENTSOE') &
            (hour_df['year'].isin(entsoe_years))
        ]
        .groupby(['country', 'year', 'group'])['mean_group']
        .mean()
        .reset_index()
        .rename(columns={'mean_group': 'entsoe_mean', 'year': 'entsoe_year'})
    )

    genesys_hour = (
        hour_df[
            (hour_df['source'] == 'GENeSYS-MOD') &
            (hour_df['year'].isin(genesys_years))
        ]
        .groupby(['country', 'scenario', 'year', 'group'])['mean_group']
        .mean()
        .reset_index()
        .rename(columns={'mean_group': 'genesys_mean', 'year': 'genesys_year'})
    )

    year_rows = []
    for (country, scenario, g_year), grp_g in genesys_hour.groupby(
            ['country', 'scenario', 'genesys_year']):

        for e_year, grp_e in entsoe_hour[
                entsoe_hour['country'] == country].groupby('entsoe_year'):

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

            c = _corr(merged['entsoe_mean'], merged['genesys_mean'])
            year_rows.append({
                'country'     : country,
                'scenario'    : scenario,
                'genesys_year': g_year,
                'entsoe_year' : e_year,
                **c,
            })

    year_result = pd.DataFrame(year_rows)
    year_result.to_csv(YEAR_OUTPUT_FILE, index=False)
    print(f'\nExported {len(year_result):,} rows  ->  {YEAR_OUTPUT_FILE}')

    print('\nMean Pearson r by scenario × genesys_year × entsoe_year:')
    summary = (
        year_result
        .groupby(['scenario', 'genesys_year', 'entsoe_year'])['pearson_r']
        .mean()
        .round(4)
    )
    print(summary.to_string())
