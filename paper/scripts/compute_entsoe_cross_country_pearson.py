"""
ENTSO-E cross-country Pearson correlations.

For each year × temporal dimension, compute Pearson r between the
group-mean price profiles of every pair of countries.

A "profile" for a given country × year × dimension is the vector of
group means (e.g. 24 hourly means for dimension='hour').

Output
------
results/calendar_effects/entsoe_cross_country_pearson.csv

Columns: dimension, year, country1, country2, rho, p_value, n_groups
"""

import os
import itertools
import pandas as pd
import numpy as np
from scipy.stats import pearsonr
import warnings
warnings.filterwarnings('ignore')

import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import COUNTRIES, ENTSOE_YEARS

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENTSOE_FILE = os.path.join(BASE, 'data', 'ENTSOE_day_ahead_prices.csv')
OUTPUT_FILE = os.path.join(BASE, 'results', 'calendar_effects',
                           'entsoe_cross_country_pearson.csv')

TIME_DIMENSIONS = ['hour', 'weekday', 'month', 'season']

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
    df['hour']    = df.index.hour
    df['weekday'] = df.index.weekday
    df['month']   = df.index.month
    df['season']  = df['month'].map(MONTH_TO_SEASON)
    return df


def load_all_profiles() -> dict[str, dict[int, dict[str, pd.Series]]]:
    """
    Load profiles for all countries and years.

    Returns
    -------
    dict  country -> year -> {dimension -> group-mean Series}
    """
    df_raw = pd.read_csv(ENTSOE_FILE, index_col=0, parse_dates=True)
    df_raw = _add_time_dims(df_raw)

    all_profiles: dict[str, dict[int, dict[str, pd.Series]]] = {}

    for country in COUNTRIES:
        if country not in df_raw.columns:
            continue
        series = df_raw[[country, 'hour', 'weekday', 'month', 'season']].copy()
        series = series.rename(columns={country: 'price'}).dropna(subset=['price'])

        country_profiles: dict[int, dict[str, pd.Series]] = {}
        for year in ENTSOE_YEARS:
            df_y = series[series.index.year == year]
            if len(df_y) < 100:
                continue
            year_profiles = {}
            for dim in TIME_DIMENSIONS:
                gm = df_y.groupby(dim)['price'].mean()
                if len(gm) >= 2:
                    year_profiles[dim] = gm
            if year_profiles:
                country_profiles[year] = year_profiles

        if country_profiles:
            all_profiles[country] = country_profiles

    return all_profiles


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    country_pairs = list(itertools.combinations(COUNTRIES, 2))

    print('=' * 70)
    print('ENTSO-E cross-country Pearson correlations')
    print(f'Countries     : {COUNTRIES}')
    print(f'Years         : {ENTSOE_YEARS}')
    print(f'Country-pairs : {len(country_pairs)}')
    print('=' * 70)

    print('Loading profiles ...')
    all_profiles = load_all_profiles()
    print(f'Loaded data for {len(all_profiles)} countries.\n')

    rows = []

    for year in ENTSOE_YEARS:
        print(f'  Year {year} ...', end=' ')
        n_before = len(rows)

        for c1, c2 in country_pairs:
            if c1 not in all_profiles or c2 not in all_profiles:
                continue
            if year not in all_profiles[c1] or year not in all_profiles[c2]:
                continue

            for dim in TIME_DIMENSIONS:
                p1 = all_profiles[c1][year].get(dim)
                p2 = all_profiles[c2][year].get(dim)
                if p1 is None or p2 is None:
                    continue

                common = p1.index.intersection(p2.index)
                if len(common) < 3:
                    continue

                v1, v2 = p1.loc[common].values, p2.loc[common].values
                rho, pval = pearsonr(v1, v2)

                rows.append({
                    'dimension': dim,
                    'year'     : year,
                    'country1' : c1,
                    'country2' : c2,
                    'rho'      : round(rho, 6),
                    'p_value'  : pval,
                    'n_groups' : len(common),
                })

        print(f'{len(rows) - n_before} pairs')

    result = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    result.to_csv(OUTPUT_FILE, index=False)
    print(f'\nExported {len(result):,} rows -> {OUTPUT_FILE}')

    # ── quick summary ────────────────────────────────────────────────────────
    print('\nMean rho per dimension (averaged over all country-pairs and years):')
    for dim in TIME_DIMENSIONS:
        sub = result[result['dimension'] == dim]
        print(f'  {dim:8s}: mean={sub["rho"].mean():.3f}  '
              f'min={sub["rho"].min():.3f}  max={sub["rho"].max():.3f}')
