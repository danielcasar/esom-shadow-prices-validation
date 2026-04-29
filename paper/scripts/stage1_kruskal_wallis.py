"""
Stage 1: Kruskal-Wallis H-test for calendar effects.

For each combination of (source, country [, scenario]):
  - test H0: all temporal groups share the same central tendency
    via the non-parametric Kruskal-Wallis H-test
  - compute effect size ε² = H / (N - 1) with 95 % CI
  - repeat per year (yearly slice)

Outputs
-------
results/calendar_effects/stage1_kw_pooled.csv   (pooled over all years)
results/calendar_effects/stage1_kw_yearly.csv  (one row per country-year)
"""

import os
import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import chi2
import warnings
warnings.filterwarnings('ignore')

import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import COUNTRIES, SCENARIOS, ENTSOE_YEARS, GENESYS_YEARS

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENTSOE_FILE   = os.path.join(BASE, 'data', 'ENTSOE_day_ahead_prices.csv')
GENESYS_FILE  = os.path.join(BASE, 'data', 'GENeSYS_MOD_prices.csv')
OUTPUT_FOLDER = os.path.join(BASE, 'results', 'calendar_effects')

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TIME_DIMENSIONS = ['hour', 'weekday', 'month', 'season']
CI_ALPHA        = 0.05

# Degrees of freedom (k - 1) per dimension
DIMENSION_DF = {
    'hour'   : 23,   # 24 hours  - 1
    'weekday':  6,   # 7 days    - 1
    'month'  : 11,   # 12 months - 1
    'season' :  3,   # 4 seasons - 1
}

MONTH_TO_SEASON = {
    12: 1,  1: 1,  2: 1,
     3: 2,  4: 2,  5: 2,
     6: 3,  7: 3,  8: 3,
     9: 4, 10: 4, 11: 4,
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _add_time_dims(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
    df['hour']    = df.index.hour
    df['weekday'] = df.index.weekday
    df['month']   = df.index.month
    df['year']    = df.index.year
    df['season']  = df['month'].map(MONTH_TO_SEASON)
    return df


def load_entsoe(country: str, years: list) -> pd.DataFrame | None:
    df = pd.read_csv(ENTSOE_FILE, index_col=0, parse_dates=True)
    if country not in df.columns:
        return None
    s = df[[country]].rename(columns={country: 'price'}).dropna()
    s = s[s.index.year.isin(years)]
    return _add_time_dims(s) if len(s) > 100 else None


def load_genesys(country: str, scenario: str, years: list) -> pd.DataFrame | None:
    df = pd.read_csv(GENESYS_FILE)
    if country not in df.columns:
        return None
    df = df[(df['scenario'] == scenario) & (df['year'].isin(years))].copy()
    if len(df) == 0:
        return None
    parts = []
    for year in sorted(df['year'].unique()):
        chunk = df[df['year'] == year].reset_index(drop=True)
        start = pd.Timestamp(f'{year}-01-01')
        chunk['timestamp'] = [start + pd.Timedelta(hours=h) for h in range(len(chunk))]
        parts.append(chunk[['timestamp', country]])
    combined = (pd.concat(parts, ignore_index=True)
                  .rename(columns={country: 'price'})
                  .set_index('timestamp')
                  .dropna())
    return _add_time_dims(combined) if len(combined) > 100 else None


# ---------------------------------------------------------------------------
# Kruskal-Wallis test + ε² effect size
# ---------------------------------------------------------------------------

def _epsilon_squared_ci(H: float, N: int, df: int,
                         alpha: float = CI_ALPHA) -> tuple[float, tuple]:
    """ε² = H / (N-1) with chi-square-based 95 % CI."""
    eps2       = H / (N - 1)
    chi_lo     = chi2.ppf(alpha / 2,     df)
    chi_hi     = chi2.ppf(1 - alpha / 2, df)
    eps2_lower = max(0.0, (H - chi_hi) / (N - 1))
    eps2_upper =          (H + chi_lo) / (N - 1)
    return eps2, (eps2_lower, eps2_upper)


def kruskal_wallis(df: pd.DataFrame, dimension: str) -> dict | None:
    """
    Kruskal-Wallis H-test for one temporal dimension.

    H0: all k groups share the same central tendency.
    """
    if dimension not in df.columns:
        return None

    groups = [df.loc[df[dimension] == v, 'price'].values
              for v in sorted(df[dimension].unique())]
    groups = [g for g in groups if len(g) > 0]
    if len(groups) < 2:
        return None

    try:
        H, p = stats.kruskal(*groups)
    except ValueError as e:
        if 'identical' in str(e).lower():
            return None
        raise

    N    = sum(len(g) for g in groups)
    dof  = DIMENSION_DF.get(dimension, len(groups) - 1)
    eps2, ci = _epsilon_squared_ci(H, N, dof)

    return {
        'test'            : 'Kruskal-Wallis',
        'statistic'       : H,
        'p_value'         : p,
        'effect_size'     : eps2,
        'effect_ci_lower' : ci[0],
        'effect_ci_upper' : ci[1],
        'n_groups'        : len(groups),
        'n_total'         : N,
    }


def _sig_stars(p: float) -> str:
    if p < 0.001: return '***'
    if p < 0.01:  return '**'
    if p < 0.05:  return '*'
    return 'n.s.'


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def _build_rows(key: tuple, dim_results: dict) -> list[dict]:
    source, scenario, country = key
    rows = []
    for dim, res in dim_results.items():
        rows.append({
            'source'          : source,
            'scenario'        : scenario,
            'country'         : country,
            'dimension'       : dim,
            'test'            : res['test'],
            'statistic'       : res['statistic'],
            'p_value'         : res['p_value'],
            'effect_size'     : res['effect_size'],
            'effect_ci_lower' : res['effect_ci_lower'],
            'effect_ci_upper' : res['effect_ci_upper'],
            'significance'    : _sig_stars(res['p_value']),
            'n_groups'        : res['n_groups'],
            'n_total'         : res['n_total'],
        })
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('=' * 70)
    print('Stage 1: Kruskal-Wallis H-test for calendar effects')
    print('=' * 70)

    pooled_rows = []
    yearly_rows = []

    # ---- ENTSO-E -----------------------------------------------------------
    print(f'\nENTSO-E  |  {len(COUNTRIES)} countries  ×  {len(ENTSOE_YEARS)} years (pooled)')
    for country in COUNTRIES:
        df = load_entsoe(country, ENTSOE_YEARS)
        if df is None:
            continue

        # Pooled (all years together)
        key = ('ENTSOE', 'Historical', country)
        res = {dim: r for dim in TIME_DIMENSIONS
               if (r := kruskal_wallis(df, dim)) is not None}
        pooled_rows.extend(_build_rows(key, res))

        # Per year
        for year in sorted(df['year'].unique()):
            df_y = df[df['year'] == year]
            if len(df_y) < 100:
                continue
            for dim in TIME_DIMENSIONS:
                r = kruskal_wallis(df_y, dim)
                if r is None:
                    continue
                yearly_rows.append({
                    'source': 'ENTSOE', 'scenario': 'Historical',
                    'country': country, 'year': int(year), 'dimension': dim,
                    **{k: r[k] for k in ('test', 'statistic', 'p_value',
                                          'effect_size', 'effect_ci_lower',
                                          'effect_ci_upper', 'n_groups', 'n_total')},
                    'significance': _sig_stars(r['p_value']),
                })
        print(f'  {country}: done')

    # ---- GENeSYS-MOD -------------------------------------------------------
    print(f'\nGENeSYS-MOD  |  {len(SCENARIOS)} scenarios  ×  {len(COUNTRIES)} countries  ×  {len(GENESYS_YEARS)} years')
    for scenario in SCENARIOS:
        for country in COUNTRIES:
            df = load_genesys(country, scenario, GENESYS_YEARS)
            if df is None:
                continue

            # Pooled (all years together)
            key = ('GENeSYS-MOD', scenario, country)
            res = {dim: r for dim in TIME_DIMENSIONS
                   if (r := kruskal_wallis(df, dim)) is not None}
            pooled_rows.extend(_build_rows(key, res))

            # Per year
            for year in sorted(df['year'].unique()):
                df_y = df[df['year'] == year]
                if len(df_y) < 100:
                    continue
                for dim in TIME_DIMENSIONS:
                    r = kruskal_wallis(df_y, dim)
                    if r is None:
                        continue
                    yearly_rows.append({
                        'source': 'GENeSYS-MOD', 'scenario': scenario,
                        'country': country, 'year': int(year), 'dimension': dim,
                        **{k: r[k] for k in ('test', 'statistic', 'p_value',
                                              'effect_size', 'effect_ci_lower',
                                              'effect_ci_upper', 'n_groups', 'n_total')},
                        'significance': _sig_stars(r['p_value']),
                    })
        print(f'  scenario {scenario}: done')

    # ---- Export ------------------------------------------------------------
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    pooled_path = os.path.join(OUTPUT_FOLDER, 'stage1_kw_pooled.csv')
    pd.DataFrame(pooled_rows).to_csv(pooled_path, index=False)
    print(f'\nExported {len(pooled_rows):,} rows  -> {pooled_path}')

    yearly_path = os.path.join(OUTPUT_FOLDER, 'stage1_kw_yearly.csv')
    pd.DataFrame(yearly_rows).to_csv(yearly_path, index=False)
    print(f'Exported {len(yearly_rows):,} rows  -> {yearly_path}')

    # ---- Quick summary -----------------------------------------------------
    df_p = pd.DataFrame(pooled_rows)
    print('\nSummary — fraction significant (p < 0.05) per source × dimension:')
    for source in df_p['source'].unique():
        sub = df_p[df_p['source'] == source]
        for dim in TIME_DIMENSIONS:
            d   = sub[sub['dimension'] == dim]
            sig = (d['p_value'] < 0.05).mean()
            print(f'  {source:12s}  {dim:8s}: {sig*100:5.1f}% significant  '
                  f'(mean ε² = {d["effect_size"].mean():.4f})')
