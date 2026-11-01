"""
04_stage3_model_market_correlations.py — Stage 3: Pearson correlations between GENeSYS-MOD and ENTSO-E profiles.

For each country × scenario × dimension × GENeSYS-MOD year (2018, 2025, 2030)
× ENTSO-E year, Pearson r between the two group-mean price profiles from the
Stage 2 output (Figures 9, C.6–C.9).

Input
-----
results/intermediate/stage2_ttest_groups_detail.csv

Output
------
results/intermediate/genesys_vs_entsoe_year_pearson.csv
    country, scenario, dimension, genesys_year, entsoe_year,
    pearson_r, p_value, n_groups
"""

import warnings

import pandas as pd
from scipy.stats import pearsonr

from config import GENESYS_YEARS, RESULTS_DIR

warnings.filterwarnings('ignore')

MIN_GROUPS = 3


def entsoe_profiles(detail: pd.DataFrame) -> pd.DataFrame:
    return (detail[detail['source'] == 'ENTSOE']
            .groupby(['country', 'year', 'dimension', 'group'])['mean_group'].mean()
            .reset_index()
            .rename(columns={'mean_group': 'entsoe_mean', 'year': 'entsoe_year'}))


def correlate(genesys: pd.DataFrame, entsoe: pd.DataFrame) -> pd.DataFrame:
    """Pearson r for every GENeSYS-MOD profile against every ENTSO-E year."""
    rows = []
    for (country, scenario, g_year, dim), grp_g in genesys.groupby(
            ['country', 'scenario', 'genesys_year', 'dimension']):
        e_sub = entsoe[(entsoe['country'] == country) & (entsoe['dimension'] == dim)]
        for e_year, grp_e in e_sub.groupby('entsoe_year'):
            merged = (pd.merge(grp_e[['group', 'entsoe_mean']],
                               grp_g[['group', 'genesys_mean']], on='group')
                      .sort_values('group').dropna())
            if len(merged) < MIN_GROUPS:
                continue
            r, p = pearsonr(merged['entsoe_mean'].values, merged['genesys_mean'].values)
            rows.append({
                'country'     : country,
                'scenario'    : scenario,
                'dimension'   : dim,
                'genesys_year': int(g_year),
                'entsoe_year' : int(e_year),
                'pearson_r'   : round(r, 6),
                'p_value'     : p,
                'n_groups'    : len(merged),
            })
    return pd.DataFrame(rows)


def model_profiles(detail: pd.DataFrame) -> pd.DataFrame:
    return (detail[(detail['source'] == 'GENeSYS-MOD') & detail['year'].isin(GENESYS_YEARS)]
            .groupby(['country', 'scenario', 'year', 'dimension', 'group'])['mean_group'].mean()
            .reset_index()
            .rename(columns={'mean_group': 'genesys_mean', 'year': 'genesys_year'}))


def main():
    detail = pd.read_csv(RESULTS_DIR / 'stage2_ttest_groups_detail.csv')
    df = correlate(model_profiles(detail), entsoe_profiles(detail))
    out = RESULTS_DIR / 'genesys_vs_entsoe_year_pearson.csv'
    df.to_csv(out, index=False)
    print(f'Exported {len(df):,} rows -> {out}')


if __name__ == '__main__':
    main()
