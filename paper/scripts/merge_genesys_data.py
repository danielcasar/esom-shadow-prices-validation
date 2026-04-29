"""
merge_genesys_data.py — Merge raw GENeSYS-MOD output files into a single CSV.

Reads all Output_marginals_*.csv files from the model output folder and
combines them into data/GENeSYS_MOD_prices.csv.

This script was run once to produce the input data and is provided for
reproducibility. Adjust INPUT_FOLDER to point to your GENeSYS-MOD output
directory before running.

Output columns: year, scenario, Hour (1–8760), one column per country (€/MWh).
"""

import os
from glob import glob

import pandas as pd

# =============================================================================
# SETTINGS
# =============================================================================

# Path to the folder containing Output_marginals_*.csv files from GENeSYS-MOD
INPUT_FOLDER = r"C:\Users\eeg\OneDrive - TU Wien\Publications\On Leveraging Shadow Prices from Energy System Models to Forecast Indicative Electricity Market Trends\GENeSYS-MOD\output"

# Output path for the merged CSV
OUTPUT_FILE = r"C:\Users\eeg\OneDrive - TU Wien\Publications\On Leveraging Shadow Prices from Energy System Models to Forecast Indicative Electricity Market Trends\Code\data\GENeSYS_MOD_prices_new.csv"

# Price column name in the old file format (€/MWh = €/kWh × 1000)
PRICE_COLUMN   = "Dual_price [€/kWh]"
CONVERT_TO_MWH = True

# =============================================================================
# MAIN
# =============================================================================

print("="*80)
print("GENeSYS-MOD — merge raw output files")
print("="*80)

csv_files = glob(os.path.join(INPUT_FOLDER, "Output_marginals_*.csv"))
print(f"\nFiles found: {len(csv_files)}")

all_data      = []
skipped_files = []

for filepath in sorted(csv_files):
    filename = os.path.basename(filepath)
    print(f"  Loading: {filename}", end="")

    year     = None
    scenario = None

    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig', low_memory=False)

        if 'Dim1' in df.columns and 'Dim2' in df.columns and 'Val' in df.columns:
            # New format: Dim1="dispatch_{scenario}_{year}", Dim2=Region, Dim3=Hour, Val=price
            df['year']     = df['Dim1'].str.extract(r'_(\d{4})$').astype(int)
            df['scenario'] = df['Dim1'].str.extract(r'^dispatch_(.+)_\d{4}$')

            df = df.rename(columns={'Dim2': 'Region', 'Dim3': 'Hour', 'Val': 'price'})
            df = df.drop(columns=['Dim1'], errors='ignore')
            df['Hour']  = pd.to_numeric(df['Hour'],  errors='coerce')
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            df = df.dropna(subset=['Hour', 'price', 'year', 'scenario'])
            df['Hour'] = df['Hour'].astype(int)

            year     = df['year'].iloc[0]
            scenario = df['scenario'].iloc[0]
            print(f" (year: {year}, scenario: {scenario})", end="")

        elif 'Region' in df.columns and 'Hour' in df.columns:
            # Old format: Region, Hour, Dual_price [€/kWh]
            # Extract year and scenario from filename (e.g. Output_marginals_2025_scenario_Green.csv)
            try:
                parts    = filename.replace(".csv", "").split("_")
                year     = int(parts[2])
                scenario = parts[4]
                print(f" (year: {year}, scenario: {scenario})", end="")
            except (IndexError, ValueError):
                print(f" — SKIPPED (cannot extract year/scenario from filename)")
                skipped_files.append(filename)
                continue

            if PRICE_COLUMN in df.columns:
                df['price'] = df[PRICE_COLUMN]
            else:
                print(f" — SKIPPED (price column missing)")
                skipped_files.append(filename)
                continue

        elif 'Row Labels' in df.columns:
            print(f" — SKIPPED (broken pivot format)")
            skipped_files.append(filename)
            continue

        else:
            print(f" — SKIPPED (unknown format: {list(df.columns)[:5]})")
            skipped_files.append(filename)
            continue

        if len(df) < 1000:
            print(f" — SKIPPED (only {len(df)} rows)")
            skipped_files.append(filename)
            continue

        if 'year' in df.columns and 'scenario' in df.columns:
            # New format: year and scenario are already columns
            df_pivot = df.pivot_table(
                index=['year', 'scenario', 'Hour'],
                columns='Region',
                values='price',
                aggfunc='first'
            ).reset_index()

            unique_combos  = df_pivot[['year', 'scenario']].drop_duplicates()
            expanded_data  = []
            for _, row in unique_combos.iterrows():
                y, s       = row['year'], row['scenario']
                df_subset  = df_pivot[(df_pivot['year'] == y) & (df_pivot['scenario'] == s)]
                all_hours  = pd.DataFrame({'Hour': range(1, 8761)})
                all_hours['year']     = y
                all_hours['scenario'] = s
                df_expanded = all_hours.merge(df_subset, on=['year', 'scenario', 'Hour'], how='left')
                expanded_data.append(df_expanded)

            df_pivot = pd.concat(expanded_data, ignore_index=True)

        else:
            # Old format: pivot on Hour, then attach year/scenario
            df_pivot = df.pivot(index='Hour', columns='Region', values='price')
            df_pivot['year']     = year
            df_pivot['scenario'] = scenario
            df_pivot = df_pivot.reset_index()

            all_hours  = pd.DataFrame({'Hour': range(1, 8761)})
            df_pivot   = all_hours.merge(df_pivot, on='Hour', how='left')
            df_pivot['year']     = year
            df_pivot['scenario'] = scenario

        # Fill missing hours with 0
        country_cols_temp = [c for c in df_pivot.columns if c not in ['year', 'scenario', 'Hour']]
        missing_count     = df_pivot[country_cols_temp].isna().sum().sum()
        df_pivot[country_cols_temp] = df_pivot[country_cols_temp].fillna(0)

        all_data.append(df_pivot)
        print(f" — OK ({len(df_pivot)} hours, {len(df_pivot.columns)-3} countries, "
              f"{missing_count} missing values filled with 0)")

    except Exception as e:
        print(f" — ERROR: {str(e)[:50]}")
        skipped_files.append(filename)
        continue

# =============================================================================
# COMBINE AND SAVE
# =============================================================================

print(f"\n{'='*80}")
print(f"Combining {len(all_data)} files ...")

if not all_data:
    print("ERROR: No data to combine.")
    exit(1)

df_combined  = pd.concat(all_data, ignore_index=True)
country_cols = sorted([c for c in df_combined.columns if c not in ['year', 'scenario', 'Hour']])
col_order    = ['year', 'scenario', 'Hour'] + country_cols
df_combined  = df_combined[col_order]
df_combined  = df_combined.sort_values(['year', 'scenario', 'Hour']).reset_index(drop=True)

df_combined.to_csv(OUTPUT_FILE, index=False)

print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
print(f"Rows:          {len(df_combined)}")
print(f"Years:         {sorted(df_combined['year'].unique())}")
print(f"Scenarios:     {sorted(df_combined['scenario'].unique())}")
print(f"Countries ({len(country_cols)}): {country_cols}")

if skipped_files:
    print(f"\nSkipped files ({len(skipped_files)}):")
    for f in skipped_files:
        print(f"  - {f}")

zero_counts  = {col: (df_combined[col] == 0).sum() for col in country_cols}
total_zeros  = sum(zero_counts.values())
total_values = len(df_combined) * len(country_cols)

print(f"\nZero values (missing hours filled with 0):")
print(f"  Total: {total_zeros} of {total_values} ({100*total_zeros/total_values:.2f}%)")
print(f"  Top 5 countries by zero count:")
for country, count in sorted(zero_counts.items(), key=lambda x: -x[1])[:5]:
    print(f"    {country}: {count}")

print(f"\nOutput: {OUTPUT_FILE}")
print(f"{'='*80}")
