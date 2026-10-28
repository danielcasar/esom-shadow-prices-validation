"""
Stage 3: Profile-correlation analysis (Pearson r and Spearman ρ).

For each (country, scenario, dimension):
  - ENTSO-E profile  = group-mean prices averaged over all ENTSO-E years
  - GENeSYS profile  = group-mean prices averaged over all GENeSYS years
                       for that specific scenario  (scenarios kept separate)
  - Correlation of the two k-element profile vectors

A "profile" is the vector of group-mean prices for one temporal dimension
(e.g. 24 hourly means, 12 monthly means, …).

Input  : results/intermediate/stage2_ttest_groups_detail.csv
Output : results/intermediate/stage3_pearson_correlations.csv
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
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE  = os.path.join(BASE, 'results', 'intermediate',
                           'stage2_ttest_groups_detail.csv')
OUTPUT_FILE = os.path.join(BASE, 'results', 'intermediate',
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
