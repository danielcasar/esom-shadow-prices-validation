"""
compute_model_market_correlations.py — Pearson correlations between
GENeSYS-MOD and ENTSO-E group-mean price profiles.

For each country × scenario × dimension × GENeSYS-MOD year × ENTSO-E year,
Pearson r between the two profiles (vectors of group-mean prices).

1. Analysis years (GENeSYS-MOD 2018, 2025, 2030): profiles from the Stage 2
   output (Figures 9, C.6–C.9).
2. All model years (2018–2060): GENeSYS-MOD profiles computed directly from
   the price data (Hour 1–8760 mapped to an hourly calendar starting
   January 1 of the model year). Supports the Section 3.4.2 footnote on model
   years after 2030; for 2018, 2025 and 2030 the values equal those of (1).

Inputs
------
results/intermediate/stage2_ttest_groups_detail.csv
data/GENeSYS_MOD_prices.csv

Outputs
-------
results/intermediate/genesys_vs_entsoe_year_pearson.csv
results/intermediate/genesys_vs_entsoe_all_years_pearson.csv
    country, scenario, dimension, genesys_year, entsoe_year,
    pearson_r, p_value, n_groups
"""

import warnings

import pandas as pd
from scipy.stats import pearsonr

from config import COUNTRIES, GENESYS_PRICES_FILE, GENESYS_YEARS, RESULTS_DIR

warnings.filterwarnings('ignore')

TIME_DIMS = ['hour', 'weekday', 'month', 'season']
MIN_GROUPS = 3
MONTH_TO_SEASON = {12: 1, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2,
                   6: 3, 7: 3, 8: 3, 9: 4, 10: 4, 11: 4}


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


# ---------------------------------------------------------------------------
# 1. Analysis years, profiles from Stage 2
# ---------------------------------------------------------------------------

def analysis_years(detail: pd.DataFrame, entsoe: pd.DataFrame) -> pd.DataFrame:
    genesys = (detail[(detail['source'] == 'GENeSYS-MOD') & detail['year'].isin(GENESYS_YEARS)]
               .groupby(['country', 'scenario', 'year', 'dimension', 'group'])['mean_group'].mean()
               .reset_index()
               .rename(columns={'mean_group': 'genesys_mean', 'year': 'genesys_year'}))
    return correlate(genesys, entsoe)


# ---------------------------------------------------------------------------
# 2. All model years, profiles from the price data
# ---------------------------------------------------------------------------

def _model_time_map(year: int) -> pd.DataFrame:
    idx = pd.date_range(start=f'{year}-01-01', periods=8760, freq='h')
    return pd.DataFrame({
        'Hour':    range(1, 8761),
        'hour':    idx.hour,
        'weekday': idx.weekday,
        'month':   idx.month,
        'season':  idx.month.map(MONTH_TO_SEASON),
    })


def all_model_years(prices: pd.DataFrame, entsoe: pd.DataFrame) -> pd.DataFrame:
    results = []
    for g_year in sorted(prices['year'].unique()):
        sub = prices[prices['year'] == g_year].merge(_model_time_map(g_year), on='Hour', how='left')
        frames = []
        for scenario, sc in sub.groupby('scenario'):
            for country in COUNTRIES:
                for dim in TIME_DIMS:
                    gm = sc.groupby(dim)[country].mean().rename('genesys_mean').reset_index()
                    gm = gm.rename(columns={dim: 'group'})
                    gm[['country', 'scenario', 'dimension', 'genesys_year']] = country, scenario, dim, g_year
                    frames.append(gm)
        results.append(correlate(pd.concat(frames, ignore_index=True), entsoe))
    return pd.concat(results, ignore_index=True)


def main():
    detail = pd.read_csv(RESULTS_DIR / 'stage2_ttest_groups_detail.csv')
    entsoe = entsoe_profiles(detail)

    outputs = {
        'genesys_vs_entsoe_year_pearson.csv':      analysis_years(detail, entsoe),
        'genesys_vs_entsoe_all_years_pearson.csv': all_model_years(pd.read_csv(GENESYS_PRICES_FILE), entsoe),
    }
    for name, df in outputs.items():
        df.to_csv(RESULTS_DIR / name, index=False)
        print(f'Exported {len(df):,} rows -> {RESULTS_DIR / name}')


if __name__ == '__main__':
    main()
