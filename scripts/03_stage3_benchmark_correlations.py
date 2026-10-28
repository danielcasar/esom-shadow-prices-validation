"""
03_stage3_benchmark_correlations.py — Stage 3 benchmark: Pearson correlations between years and between countries.
profiles of different years and of different countries.

A "profile" is the vector of group-mean prices of one temporal dimension
(e.g. the 24 hourly means for dimension = 'hour').

1. ENTSO-E cross-year: for each country × dimension, Pearson r between the
   profiles of every pair of years 2018–2025. This is the market benchmark of
   Stage 3 (Table 8, Table C.4; Figures 8, 9, C.5–C.9).
2. ENTSO-E cross-country: for each year × dimension, Pearson r between the
   profiles of every pair of countries (Table 4, Figure C.1).
3. GENeSYS-MOD cross-country: the same for each model year × scenario
   (Table 4).

Outputs
-------
results/intermediate/entsoe_cross_year_pearson.csv
    country, dimension, year1, year2, rho, p_value, n_groups
results/intermediate/entsoe_cross_country_pearson.csv
    dimension, year, country1, country2, rho, p_value, n_groups
results/intermediate/genesys_cross_country_pearson.csv
    dimension, year, scenario, country1, country2, rho, p_value, n_groups
"""

import itertools
import warnings

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

from config import (COUNTRIES, ENTSOE_PRICES_FILE, ENTSOE_YEARS, GENESYS_PRICES_FILE,
                    GENESYS_YEARS, RESULTS_DIR, SCENARIOS)

warnings.filterwarnings('ignore')

TIME_DIMENSIONS = ['hour', 'weekday', 'month', 'season']

MONTH_TO_SEASON = {
    12: 1,  1: 1,  2: 1,
     3: 2,  4: 2,  5: 2,
     6: 3,  7: 3,  8: 3,
     9: 4, 10: 4, 11: 4,
}


def _add_time_dims(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['hour']    = df.index.hour
    df['weekday'] = df.index.weekday
    df['month']   = df.index.month
    df['season']  = df['month'].map(MONTH_TO_SEASON)
    return df


def _yearly_profiles(series: pd.DataFrame) -> dict[int, dict[str, pd.Series]]:
    """year -> {dimension -> group-mean Series} for one country."""
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
# 1. ENTSO-E cross-year
# ---------------------------------------------------------------------------

def entsoe_cross_year(entsoe: pd.DataFrame) -> pd.DataFrame:
    year_pairs = list(itertools.combinations(ENTSOE_YEARS, 2))
    rows = []
    for country in COUNTRIES:
        if country not in entsoe.columns:
            continue
        series = entsoe[[country]].rename(columns={country: 'price'}).dropna()
        profiles = _yearly_profiles(_add_time_dims(series))

        for y1, y2 in year_pairs:
            if y1 not in profiles or y2 not in profiles:
                continue
            for dim in TIME_DIMENSIONS:
                if dim not in profiles[y1] or dim not in profiles[y2]:
                    continue
                p1, p2 = profiles[y1][dim], profiles[y2][dim]
                common = p1.index.intersection(p2.index)
                if len(common) < 3:
                    continue
                rho, pval = pearsonr(p1.loc[common].values, p2.loc[common].values)
                rows.append({
                    'country'  : country,
                    'dimension': dim,
                    'year1'    : y1,
                    'year2'    : y2,
                    'rho'      : round(rho, 6),
                    'p_value'  : pval,
                    'n_groups' : len(common),
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. ENTSO-E cross-country
# ---------------------------------------------------------------------------

def entsoe_cross_country(entsoe: pd.DataFrame) -> pd.DataFrame:
    df = _add_time_dims(entsoe)
    all_profiles = {}
    for country in COUNTRIES:
        if country not in df.columns:
            continue
        series = df[[country, 'hour', 'weekday', 'month', 'season']].copy()
        series = series.rename(columns={country: 'price'}).dropna(subset=['price'])
        profiles = _yearly_profiles(series)
        if profiles:
            all_profiles[country] = profiles

    rows = []
    for year in ENTSOE_YEARS:
        for c1, c2 in itertools.combinations(COUNTRIES, 2):
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
                rho, pval = pearsonr(p1.loc[common].values, p2.loc[common].values)
                rows.append({
                    'dimension': dim,
                    'year'     : year,
                    'country1' : c1,
                    'country2' : c2,
                    'rho'      : round(rho, 6),
                    'p_value'  : pval,
                    'n_groups' : len(common),
                })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. GENeSYS-MOD cross-country
# ---------------------------------------------------------------------------

def _model_time_map(year: int) -> pd.DataFrame:
    """Map Hour 1-8760 to calendar dimensions for a given model year."""
    idx = pd.date_range(start=f'{year}-01-01', periods=8760, freq='h')
    tm = pd.DataFrame({
        'Hour'   : range(1, 8761),
        'hour'   : idx.hour,
        'weekday': idx.weekday,
        'month'  : idx.month,
    })
    tm['season'] = tm['month'].map(MONTH_TO_SEASON)
    return tm


def genesys_cross_country(genesys: pd.DataFrame) -> pd.DataFrame:
    available = [c for c in COUNTRIES if c in genesys.columns]
    rows = []
    for year in GENESYS_YEARS:
        tm = _model_time_map(year)
        for scenario in SCENARIOS:
            sub = genesys[(genesys['year'] == year) & (genesys['scenario'] == scenario)].copy()
            if sub.empty:
                continue
            sub = sub.merge(tm, on='Hour', how='left')
            for c1, c2 in itertools.combinations(available, 2):
                for dim in TIME_DIMENSIONS:
                    p1 = sub.groupby(dim)[c1].mean()
                    p2 = sub.groupby(dim)[c2].mean()
                    common = p1.index.intersection(p2.index)
                    if len(common) < 3:
                        continue
                    v1, v2 = p1.loc[common].values, p2.loc[common].values
                    if np.std(v1) == 0 or np.std(v2) == 0:
                        continue
                    rho, pval = pearsonr(v1, v2)
                    rows.append({
                        'dimension': dim,
                        'year'     : year,
                        'scenario' : scenario,
                        'country1' : c1,
                        'country2' : c2,
                        'rho'      : round(rho, 6),
                        'p_value'  : pval,
                        'n_groups' : len(common),
                    })
    return pd.DataFrame(rows)


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    entsoe = pd.read_csv(ENTSOE_PRICES_FILE, index_col=0, parse_dates=True)
    genesys = pd.read_csv(GENESYS_PRICES_FILE)

    outputs = {
        'entsoe_cross_year_pearson.csv':     entsoe_cross_year(entsoe),
        'entsoe_cross_country_pearson.csv':  entsoe_cross_country(entsoe),
        'genesys_cross_country_pearson.csv': genesys_cross_country(genesys),
    }
    for name, df in outputs.items():
        df.to_csv(RESULTS_DIR / name, index=False)
        print(f'Exported {len(df):,} rows -> {RESULTS_DIR / name}')


if __name__ == '__main__':
    main()
