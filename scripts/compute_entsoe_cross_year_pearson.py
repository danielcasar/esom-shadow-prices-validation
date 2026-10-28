"""
ENTSO-E cross-year Pearson benchmark.

For each country × temporal dimension, compute Pearson r between the
group-mean price profiles of every pair of years.

A "profile" for a given country × year × dimension is the vector of
group means (e.g. 24 hourly means for dimension='hour').

All countries and years are taken from config.py, so adding FR (or any
other country) to COUNTRIES is sufficient to include it in the output.

Output
------
results/intermediate/entsoe_cross_year_pearson.csv

Columns: country, dimension, year1, year2, rho, p_value, n_groups
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
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTSOE_FILE = os.path.join(BASE, 'data', 'ENTSOE_day_ahead_prices.csv')
OUTPUT_FILE = os.path.join(BASE, 'results', 'intermediate',
                           'entsoe_cross_year_pearson.csv')

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


def load_profiles(country: str) -> dict[int, dict[str, pd.Series]]:
    """
    Load all yearly profiles for one country.

    Returns
    -------
    dict  year -> {dimension -> group-mean Series (index = group values)}
    """
    df_raw = pd.read_csv(ENTSOE_FILE, index_col=0, parse_dates=True)
    if country not in df_raw.columns:
        return {}

    series = df_raw[[country]].rename(columns={country: 'price'}).dropna()
    series = _add_time_dims(series)

    profiles: dict[int, dict[str, pd.Series]] = {}
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
            profiles[year] = year_profiles

    return profiles


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('=' * 70)
    print('ENTSO-E cross-year Pearson benchmark')
    print(f'Countries : {COUNTRIES}')
    print(f'Years     : {ENTSOE_YEARS}')
    print(f'Year-pairs: {len(list(itertools.combinations(ENTSOE_YEARS, 2)))}')
    print('=' * 70)

    year_pairs = list(itertools.combinations(ENTSOE_YEARS, 2))
    rows = []

    for country in COUNTRIES:
        print(f'  {country} ...', end=' ')
        profiles = load_profiles(country)

        if not profiles:
            print('no data')
            continue

        for y1, y2 in year_pairs:
            if y1 not in profiles or y2 not in profiles:
                continue
            for dim in TIME_DIMENSIONS:
                if dim not in profiles[y1] or dim not in profiles[y2]:
                    continue

                p1 = profiles[y1][dim]
                p2 = profiles[y2][dim]

                # align on common groups
                common = p1.index.intersection(p2.index)
                if len(common) < 3:
                    continue

                v1, v2 = p1.loc[common].values, p2.loc[common].values
                rho, pval = pearsonr(v1, v2)

                rows.append({
                    'country'  : country,
                    'dimension': dim,
                    'year1'    : y1,
                    'year2'    : y2,
                    'rho'      : round(rho, 6),
                    'p_value'  : pval,
                    'n_groups' : len(common),
                })

        print(f'{len([r for r in rows if r["country"] == country])} pairs')

    result = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    result.to_csv(OUTPUT_FILE, index=False)
    print(f'\nExported {len(result):,} rows  ->  {OUTPUT_FILE}')

    # ── quick summary ────────────────────────────────────────────────────────
    print('\nMean rho per dimension (averaged over all countries and year-pairs):')
    for dim in TIME_DIMENSIONS:
        sub = result[result['dimension'] == dim]
        print(f'  {dim:8s}: mean={sub["rho"].mean():.3f}  '
              f'min={sub["rho"].min():.3f}  max={sub["rho"].max():.3f}')
