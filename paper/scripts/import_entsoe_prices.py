"""
ENTSO-E Day-Ahead Prices — Import

Steps:
  1. Read zone mapping from data/country_mapping.csv
     (ENTSO-E zone codes ↔ country labels + metadata)
  2. Download all bidding zones from the ENTSO-E Transparency Platform
     (including non-primary zones such as NO_x, IT_x, flagged as is_primary=0)
  3. Save raw data with original zone codes -> data/ENTSOE_day_ahead_prices_raw.csv
  4. Rename primary zones (is_primary=1) and save analysis CSV
                                          -> data/ENTSOE_day_ahead_prices.csv

Configuration is entirely driven by data/country_mapping.csv:
  - is_primary=1  -> zone appears (renamed) in the analysis CSV
  - is_primary=0  -> zone only in the raw CSV (e.g. NO_1, IT_CNOR, SE_1 …)
  - pre_split_zone / split_date_utc  -> automatic predecessor-zone merging
"""

import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from entsoe import EntsoePandasClient

# =============================================================================
# SETTINGS
# =============================================================================

# Load API token from .env (two levels above this scripts/ directory)
load_dotenv(Path(__file__).parent.parent.parent / ".env")
API_KEY = os.environ.get("ENTSOE_API_TOKEN")
if not API_KEY:
    print("ERROR: ENTSOE_API_TOKEN not set.")
    print("  Copy .env.example -> .env and add your token.")
    sys.exit(1)

BASE         = Path(__file__).parent.parent.parent
MAPPING_FILE = BASE / "data" / "country_mapping.csv"
OUTPUT_RAW   = BASE / "data" / "ENTSOE_day_ahead_prices_raw.csv"
OUTPUT_FILE  = BASE / "data" / "ENTSOE_day_ahead_prices.csv"

START_TS = pd.Timestamp("20150101", tz="UTC")
END_TS   = pd.Timestamp("20260101", tz="UTC")

# =============================================================================
# LOAD MAPPING
# =============================================================================

print("="*70)
print("ENTSO-E Day-Ahead Prices Import")
print("="*70)
print(f"Mapping file: {MAPPING_FILE}")

mapping = pd.read_csv(MAPPING_FILE, dtype=str, keep_default_na=False)

required_cols = {"country_label", "entsoe_zone", "is_primary"}
if not required_cols.issubset(mapping.columns):
    raise ValueError(f"country_mapping.csv is missing columns: {required_cols - set(mapping.columns)}")

mapping["is_primary"] = mapping["is_primary"].astype(int)

n_total   = len(mapping)
n_primary = mapping["is_primary"].sum()
print(f"  Total zones: {n_total}  ({n_primary} primary -> analysis CSV)")
print()

display = mapping[["country_label", "entsoe_zone", "is_primary", "zone_description"]].copy()
display["P"] = display["is_primary"].map({1: "✓", 0: " "})
print(display[["P", "country_label", "entsoe_zone", "zone_description"]].to_string(index=False))
print()

# =============================================================================
# API CONNECTION
# =============================================================================

print("Connecting to ENTSO-E API...")
client = EntsoePandasClient(api_key=API_KEY)
print(f"Date range: {START_TS.date()} to {END_TS.date()}")
print()

# =============================================================================
# DOWNLOAD DATA  —  one row = one bidding zone
# =============================================================================

raw_data: dict[str, pd.Series] = {}

success_count = 0
error_count   = 0
error_log     = []

for _, row in mapping.iterrows():
    label     = row["country_label"]
    zone      = row["entsoe_zone"]
    is_prim   = row["is_primary"]
    pre_zone  = row.get("pre_split_zone", "")
    split_raw = row.get("split_date_utc", "")
    prim_tag  = "[PRIMARY]" if is_prim else "         "

    print(f"{'─'*70}")
    print(f"  {prim_tag}  {label:4s} / {zone:12s}  {row.get('zone_description', '')}")

    try:
        ts = client.query_day_ahead_prices(zone, start=START_TS, end=END_TS)

        # Merge predecessor zone if applicable (e.g. DE_AT_LU before Oct 2018)
        if pre_zone and split_raw:
            split_ts = pd.Timestamp(split_raw, tz="UTC")
            print(f"  Predecessor zone {pre_zone} (before {split_ts.date()}) ...")
            try:
                ts_old = client.query_day_ahead_prices(pre_zone, start=START_TS, end=split_ts)
                ts = ts.combine_first(ts_old)
                print(f"  OK: {pre_zone} merged")
            except Exception as e_split:
                print(f"  Note: {pre_zone} not available — {str(e_split)[:80]}")

        if isinstance(ts, pd.DataFrame):
            ts = ts.iloc[:, 0]

        ts = ts.resample("h").mean()

        n_null = ts.isnull().sum()
        if n_null > 0:
            ts = ts.interpolate().bfill().ffill()
            print(f"  {n_null} missing hours interpolated")

        raw_data[zone] = ts
        print(f"  OK: {len(ts):,} h  ({ts.index.min().date()} -> {ts.index.max().date()})")
        success_count += 1
        time.sleep(1)

    except Exception as e:
        print(f"  ERROR: {str(e)[:100]}")
        error_count += 1
        error_log.append((label, zone, str(e)[:80]))
        time.sleep(2)

# =============================================================================
# RAW CSV  —  all zones, column names = ENTSO-E zone codes
# =============================================================================

print(f"\n{'='*70}")
print("Saving raw CSV (all zones, original zone codes as columns) ...")

if not raw_data:
    print("No data downloaded — aborting.")
else:
    df_raw = pd.DataFrame(raw_data)
    df_raw.index.name = "timestamp"
    df_raw = df_raw.reindex(sorted(df_raw.columns), axis=1)
    df_raw.to_csv(OUTPUT_RAW)
    print(f"  -> {OUTPUT_RAW}")
    print(f"     {len(df_raw):,} rows | {len(df_raw.columns)} zones")
    print(f"     Columns: {', '.join(df_raw.columns)}")

    # =========================================================================
    # ANALYSIS CSV  —  primary zones only, column names = country labels
    # =========================================================================

    print()
    print("Building analysis CSV (primary zones only, country labels as columns) ...")

    primary_rows = mapping[mapping["is_primary"] == 1]

    # Safety check: each country_label may only have one primary zone
    dupes = primary_rows[primary_rows.duplicated("country_label", keep=False)]
    if not dupes.empty:
        raise ValueError(
            f"Multiple primary zones for the same country label in country_mapping.csv:\n{dupes}"
        )

    primary_rename = primary_rows.set_index("entsoe_zone")["country_label"].to_dict()

    available_primary = {z: lbl for z, lbl in primary_rename.items() if z in df_raw.columns}
    missing_primary   = [z for z in primary_rename if z not in df_raw.columns]

    if missing_primary:
        print(f"  Note: primary zones missing from raw CSV (download errors): {missing_primary}")

    df_analysis = df_raw[list(available_primary.keys())].rename(columns=available_primary)
    df_analysis = df_analysis.reindex(sorted(df_analysis.columns), axis=1)
    df_analysis.to_csv(OUTPUT_FILE)
    print(f"  -> {OUTPUT_FILE}")
    print(f"     {len(df_analysis):,} rows | {len(df_analysis.columns)} countries")
    print(f"     Columns: {', '.join(df_analysis.columns)}")

# =============================================================================
# SUMMARY
# =============================================================================

print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
print(f"  Zones downloaded successfully: {success_count} / {n_total}")
print(f"  Errors:                        {error_count}")

if error_log:
    print("\n  Error details:")
    for label, zone, err in error_log:
        print(f"    {label:4s} ({zone}): {err}")

print()
print(f"  Raw CSV      (ENTSO-E codes):  {OUTPUT_RAW}")
print(f"  Analysis CSV (country labels): {OUTPUT_FILE}")
print(f"  Mapping file:                  {MAPPING_FILE}")
print(f"{'='*70}")
