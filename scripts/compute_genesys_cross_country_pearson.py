"""
compute_genesys_cross_country_pearson.py

Cross-country Pearson correlations from GENeSYS-MOD shadow prices
(GENeSYS-MOD column of Table 4).

For each year × scenario × temporal dimension, compute Pearson r between
the group-mean price profiles of every country pair.

Hour 1-8760 is mapped to calendar groups using an hourly datetime index
starting on January 1 of the snapshot year (8760 h, no leap day).

Output
------
results/intermediate/genesys_cross_country_pearson.csv

Columns: dimension, year, scenario, country1, country2, rho, p_value, n_groups
"""

import itertools
import warnings

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

from config import COUNTRIES, GENESYS_YEARS, SCENARIOS, GENESYS_PRICES_FILE, RESULTS_DIR

warnings.filterwarnings('ignore')

OUTPUT_FILE = RESULTS_DIR / 'genesys_cross_country_pearson.csv'

TIME_DIMENSIONS = ['hour', 'weekday', 'month', 'season']

MONTH_TO_SEASON = {
    12: 1,  1: 1,  2: 1,
     3: 2,  4: 2,  5: 2,
     6: 3,  7: 3,  8: 3,
     9: 4, 10: 4, 11: 4,
}


def build_time_map(year: int) -> pd.DataFrame:
    """Map Hour 1-8760 to calendar dimensions for a given year."""
    idx = pd.date_range(start=f'{year}-01-01', periods=8760, freq='h')
    tm = pd.DataFrame({
        'Hour'   : range(1, 8761),
        'hour'   : idx.hour,
        'weekday': idx.weekday,
        'month'  : idx.month,
    })
    tm['season'] = tm['month'].map(MONTH_TO_SEASON)
    return tm


if __name__ == '__main__':
    df_raw = pd.read_csv(GENESYS_PRICES_FILE)
    available = [c for c in COUNTRIES if c in df_raw.columns]

    country_pairs = list(itertools.combinations(available, 2))
    print('=' * 70)
    print('GENeSYS-MOD cross-country Pearson correlations')
    print(f'Countries     : {available}')
    print(f'Years         : {GENESYS_YEARS}')
    print(f'Scenarios     : {SCENARIOS}')
    print(f'Country-pairs : {len(country_pairs)}')
    print('=' * 70)

    rows = []
    for year in GENESYS_YEARS:
        tm = build_time_map(year)
        for scenario in SCENARIOS:
            sub = df_raw[(df_raw['year'] == year) & (df_raw['scenario'] == scenario)].copy()
            if sub.empty:
                print(f'  {year} / {scenario}: no data, skipping')
                continue
            sub = sub.merge(tm, on='Hour', how='left')

            print(f'  {year} / {scenario} ...', end=' ')
            n_before = len(rows)
            for c1, c2 in country_pairs:
                for dim in TIME_DIMENSIONS:
                    p1 = sub.groupby(dim)[c1].mean()
                    p2 = sub.groupby(dim)[c2].mean()
                    common = p1.index.intersection(p2.index)
                    if len(common) < 3:
                        continue
                    v1 = p1.loc[common].values
                    v2 = p2.loc[common].values
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
            print(f'{len(rows) - n_before} pairs')

    result = pd.DataFrame(rows)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_FILE, index=False)
    print(f'\nExported {len(result):,} rows -> {OUTPUT_FILE}')
