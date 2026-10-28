"""
02_stage2_t_tests.py — Stage 2: one-sample t-tests of each calendar group against the annual mean.

For each combination of (source, country, year [, scenario]):
  - compute the annual mean price mu_D across the full price series
  - for each temporal dimension (hour, weekday, month, season) and
    each group g within that dimension, test H0: mu_g = mu_D via a
    one-sample t-test (scipy.stats.ttest_1samp, two-sided)
  - record Δ_g = mu_g - mu_D  (€/MWh)
  - record Δ_g% = Δ_g / mu_D * 100  (%)
  - p-values are unadjusted; significance threshold α = 0.05

Outputs:
  results/intermediate/stage2_ttest_groups_detail.csv
"""

import os
from functools import lru_cache
import pandas as pd
import numpy as np
from scipy.stats import ttest_1samp
import warnings
warnings.filterwarnings('ignore')

import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import COUNTRIES, SCENARIOS, ENTSOE_YEARS, GENESYS_YEARS

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTSOE_FILE   = os.path.join(BASE, 'data', 'ENTSOE_day_ahead_prices.csv')
GENESYS_FILE  = os.path.join(BASE, 'data', 'GENeSYS_MOD_prices.csv')
OUTPUT_FOLDER = os.path.join(BASE, 'results', 'intermediate')
OUTPUT_FILE   = os.path.join(OUTPUT_FOLDER, 'stage2_ttest_groups_detail.csv')

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TIME_DIMENSIONS = ['hour', 'weekday', 'month', 'season']
ALPHA           = 0.05
MIN_OBS         = 30   # minimum observations per group to run t-test

MONTH_TO_SEASON = {
    12: 1,  1: 1,  2: 1,   # Winter
     3: 2,  4: 2,  5: 2,   # Spring
     6: 3,  7: 3,  8: 3,   # Summer
     9: 4, 10: 4, 11: 4,   # Autumn
}


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _read_entsoe() -> pd.DataFrame:
    """Read the ENTSO-E CSV once per run (cached)."""
    return pd.read_csv(ENTSOE_FILE, index_col=0, parse_dates=True)


@lru_cache(maxsize=None)
def _read_genesys() -> pd.DataFrame:
    """Read the GENeSYS-MOD CSV once per run (cached)."""
    return pd.read_csv(GENESYS_FILE)


def _add_time_dims(df: pd.DataFrame) -> pd.DataFrame:
    """Attach hour / weekday / month / season / year columns."""
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
    df['hour']    = df.index.hour         # 0–23
    df['weekday'] = df.index.weekday      # 0=Mon … 6=Sun
    df['month']   = df.index.month        # 1–12
    df['year']    = df.index.year
    df['season']  = df['month'].map(MONTH_TO_SEASON)   # 1=Winter … 4=Autumn
    return df


def load_entsoe(country: str, year: int) -> pd.DataFrame | None:
    """Load one country × year slice from the ENTSO-E CSV."""
    df = _read_entsoe()
    if country not in df.columns:
        return None
    series = (df[[country]]
              .rename(columns={country: 'price'})
              .dropna())
    series = series[series.index.year == year]
    if len(series) < MIN_OBS:
        return None
    return _add_time_dims(series)


def load_genesys(country: str, scenario: str, year: int) -> pd.DataFrame | None:
    """Load one country × scenario × year slice from the GENeSYS-MOD CSV."""
    df = _read_genesys()
    if country not in df.columns:
        return None
    df = (df[(df['scenario'] == scenario) & (df['year'] == year)]
          .reset_index(drop=True))
    if len(df) == 0:
        return None
    # Reconstruct hourly timestamps (GENeSYS rows are ordered hour 0 … 8759)
    start      = pd.Timestamp(f'{year}-01-01')
    df['timestamp'] = [start + pd.Timedelta(hours=h) for h in range(len(df))]
    series = (df[['timestamp', country]]
              .rename(columns={country: 'price'})
              .set_index('timestamp')
              .dropna())
    if len(series) < MIN_OBS:
        return None
    return _add_time_dims(series)


# ---------------------------------------------------------------------------
# Stage 2 core
# ---------------------------------------------------------------------------

def stage2_ttests(
    df: pd.DataFrame,
    source: str,
    scenario: str,
    country: str,
    year: int,
) -> list[dict]:
    """
    Run one-sample t-tests for all groups in all temporal dimensions.

    H0: mu_g = mu_D  where mu_D = annual mean of the full price series.

    Parameters
    ----------
    df       : price DataFrame with temporal dimension columns attached
    source   : 'ENTSOE' or 'GENeSYS-MOD'
    scenario : scenario label (e.g. 'Historical' or 'GreenHydrogen')
    country  : ISO country code
    year     : calendar year of the data slice

    Returns
    -------
    list of result dicts (one per group × dimension)
    """
    mu_D     = df['price'].mean()
    median_D = df['price'].median()
    rows     = []

    for dim in TIME_DIMENSIONS:
        for g in sorted(df[dim].unique()):
            data = df.loc[df[dim] == g, 'price'].values
            if len(data) < MIN_OBS:
                continue

            t_stat, p_value = ttest_1samp(data, mu_D)
            mu_g  = data.mean()
            delta = mu_g - mu_D

            rows.append({
                'source'               : source,
                'scenario'             : scenario,
                'country'              : country,
                'year'                 : year,
                'dimension'            : dim,
                'group'                : g,
                'mean_total'           : round(mu_D,     4),
                'median_total'         : round(median_D, 4),
                'mean_group'           : round(mu_g,     4),
                'deviation'            : round(delta,    4),   # Δ_g  (€/MWh)
                'deviation_from_median': round(mu_g - median_D, 4),
                'deviation_pct'        : round(delta / mu_D * 100, 4) if mu_D != 0 else np.nan,  # Δ_g%
                't_stat'               : round(t_stat,   4),
                'p_value'              : p_value,
                'significant'          : p_value < ALPHA,
                'n'                    : len(data),
            })

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('=' * 70)
    print('Stage 2: One-sample t-tests for calendar-effect groups')
    print('=' * 70)

    all_rows: list[dict] = []

    # ---- ENTSO-E -----------------------------------------------------------
    print(f'\nENTSO-E  |  {len(COUNTRIES)} countries  ×  {len(ENTSOE_YEARS)} years')
    for country in COUNTRIES:
        for year in ENTSOE_YEARS:
            df = load_entsoe(country, year)
            if df is None:
                continue
            rows = stage2_ttests(df, 'ENTSOE', 'Historical', country, year)
            all_rows.extend(rows)
            print(f'  {country} {year}: {len(rows)} group-tests')

    # ---- GENeSYS-MOD -------------------------------------------------------
    print(f'\nGENeSYS-MOD  |  {len(SCENARIOS)} scenarios  ×  {len(COUNTRIES)} countries  ×  {len(GENESYS_YEARS)} years')
    for scenario in SCENARIOS:
        for country in COUNTRIES:
            for year in GENESYS_YEARS:
                df = load_genesys(country, scenario, year)
                if df is None:
                    continue
                rows = stage2_ttests(df, 'GENeSYS-MOD', scenario, country, year)
                all_rows.extend(rows)
        print(f'  scenario {scenario}: done')

    # ---- Export ------------------------------------------------------------
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    result_df = pd.DataFrame(all_rows)
    result_df.to_csv(OUTPUT_FILE, index=False)

    print(f'\nExported {len(result_df):,} rows -> {OUTPUT_FILE}')

    # ---- Deviation summary (range & ratio per country × dimension × scenario) --
    summary_rows = []
    for (country, dim), grp in result_df.groupby(['country', 'dimension']):
        e = grp[grp['source'] == 'ENTSOE']
        if e.empty:
            continue
        e_range = e['deviation'].max() - e['deviation'].min()
        e_max   = e['deviation'].abs().max()
        for scenario in SCENARIOS:
            m = grp[(grp['source'] == 'GENeSYS-MOD') & (grp['scenario'] == scenario)]
            if m.empty:
                continue
            m_range = m['deviation'].max() - m['deviation'].min()
            m_max   = m['deviation'].abs().max()
            summary_rows.append({
                'country'       : country,
                'dimension'     : dim,
                'model_scenario': scenario,
                'entsoe_range'  : e_range,
                'entsoe_max_dev': e_max,
                'model_range'   : m_range,
                'model_max_dev' : m_max,
                'range_ratio'   : e_range / m_range if m_range > 0 else np.nan,
            })

    summary_path = os.path.join(OUTPUT_FOLDER, 'deviation_summary.csv')
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False)
    print(f'Exported {len(summary_rows):,} rows  -> {summary_path}')

    # ---- Quick sanity summary ----------------------------------------------
    print('\nSummary — fraction significant (p < 0.05) per source × dimension:')
    for source in result_df['source'].unique():
        sub = result_df[result_df['source'] == source]
        for dim in TIME_DIMENSIONS:
            d   = sub[sub['dimension'] == dim]
            sig = d['significant'].mean()
            print(f'  {source:12s}  {dim:8s}: {sig*100:5.1f}% significant  '
                  f'(mean |Δ_g| = {d["deviation"].abs().mean():.2f} €/MWh)')
