"""
06_compression_factors.py — Compression factors xi (ENTSO-E 2025 range / GENeSYS-MOD 2025 range).

For each country and temporal dimension (Table C.5):
  1. deviation of each hourly 2025 price from the 2025 annual mean
  2. mean deviation per group (e.g. per hour of day)
  3. range = max - min of the group-mean deviations
xi = ENTSO-E range / GENeSYS-MOD range, where the GENeSYS-MOD range is the
median of the four scenario ranges.

Output
------
results/intermediate/compression_factors_2025.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import COUNTRIES, SCENARIOS

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE       = Path(__file__).parent.parent
ENTSOE_F   = BASE / "data" / "ENTSOE_day_ahead_prices.csv"
GENESYS_F  = BASE / "data" / "GENeSYS_MOD_prices.csv"
OUT_DIR    = BASE / "results" / "intermediate"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV    = OUT_DIR / "compression_factors_2025.csv"

DIMS = ["hour", "weekday", "month", "season"]

DIM_LABELS = {
    "hour":    "Hour-of-Day",
    "weekday": "Day-of-Week",
    "month":   "Month-of-Year",
    "season":  "Season",
}

SEASON_MAP = {12: "DJF", 1: "DJF", 2: "DJF",
              3:  "MAM", 4: "MAM", 5: "MAM",
              6:  "JJA", 7: "JJA", 8: "JJA",
              9:  "SON", 10: "SON", 11: "SON"}


# ── Build calendar for 2025 (8760 hours, non-leap year) ──────────────────────
def build_calendar_2025():
    """Return a DataFrame with one row per hour (Hour 1..8760) and group columns."""
    # Hour 1 = 2025-01-01 00:00 UTC
    timestamps = pd.date_range("2025-01-01", periods=8760, freq="h", tz="UTC")
    cal = pd.DataFrame({
        "Hour":    np.arange(1, 8761),
        "hour_of_day": timestamps.hour,
        "weekday":     timestamps.dayofweek,   # 0=Mon … 6=Sun
        "month":       timestamps.month,
        "season":      timestamps.month.map(SEASON_MAP),
    })
    return cal


CAL = build_calendar_2025()
GROUP_COL = {"hour": "hour_of_day", "weekday": "weekday",
             "month": "month", "season": "season"}


# ── Helper: range of group-mean deviations ────────────────────────────────────
def deviation_range(prices: np.ndarray, groups: np.ndarray) -> float:
    """
    Given a vector of hourly prices and corresponding group labels,
    return max(group_mean_deviation) - min(group_mean_deviation).
    """
    annual_mean = np.nanmean(prices)
    devs = prices - annual_mean
    df = pd.DataFrame({"dev": devs, "group": groups})
    gm = df.groupby("group")["dev"].mean()
    return float(gm.max() - gm.min())


# ── Load ENTSOE 2025 ──────────────────────────────────────────────────────────
print("Loading ENTSOE data...")
df_e = pd.read_csv(ENTSOE_F, parse_dates=["timestamp"])
df_e["timestamp"] = pd.to_datetime(df_e["timestamp"], utc=True)
df_e = df_e[df_e["timestamp"].dt.year == 2025].copy()
df_e = df_e.sort_values("timestamp").reset_index(drop=True)
assert len(df_e) == 8760, f"Expected 8760 ENTSOE 2025 rows, got {len(df_e)}"

# Attach calendar (already sorted chronologically)
for col in ["hour_of_day", "weekday", "month", "season"]:
    df_e[col] = CAL[col].values

print(f"  ENTSOE 2025: {len(df_e)} hourly rows, {len(COUNTRIES)} countries")


# ── Load GENeSYS 2025 ─────────────────────────────────────────────────────────
print("Loading GENeSYS-MOD data...")
df_g = pd.read_csv(GENESYS_F)
df_g = df_g[df_g["year"] == 2025].copy()
df_g = df_g.sort_values(["scenario", "Hour"]).reset_index(drop=True)

# Attach calendar per scenario
merged_parts = []
for sc in SCENARIOS:
    part = df_g[df_g["scenario"] == sc].sort_values("Hour").reset_index(drop=True)
    assert len(part) == 8760, f"Expected 8760 rows for {sc}, got {len(part)}"
    for col in ["hour_of_day", "weekday", "month", "season"]:
        part[col] = CAL[col].values
    merged_parts.append(part)
df_g = pd.concat(merged_parts, ignore_index=True)

print(f"  GENeSYS 2025: {len(df_g)} rows ({len(SCENARIOS)} scenarios × 8760 hours)")


# ── Compute compression factors ───────────────────────────────────────────────
print("\nComputing compression factors...")
records = []

for country in COUNTRIES:
    if country not in df_e.columns:
        print(f"  WARNING: {country} not in ENTSOE data, skipping")
        continue
    if country not in df_g.columns:
        print(f"  WARNING: {country} not in GENeSYS data, skipping")
        continue

    e_prices = df_e[country].values

    for dim in DIMS:
        gcol = GROUP_COL[dim]
        e_groups = df_e[gcol].values
        entsoe_range = deviation_range(e_prices, e_groups)

        # GENeSYS range per scenario, then median
        sc_ranges = []
        for sc in SCENARIOS:
            sc_df = df_g[df_g["scenario"] == sc]
            g_prices = sc_df[country].values
            g_groups = sc_df[gcol].values
            sc_ranges.append(deviation_range(g_prices, g_groups))

        genesys_range = float(np.median(sc_ranges))
        xi = entsoe_range / genesys_range if genesys_range > 0 else np.nan

        records.append({
            "country":        country,
            "dimension":      dim,
            "entsoe_range":   round(entsoe_range, 3),
            "genesys_range":  round(genesys_range, 3),
            "xi":             round(xi, 2),
        })

df_out = pd.DataFrame(records)
df_out.to_csv(OUT_CSV, index=False)
print(f"\nSaved: {OUT_CSV}")


# ── Pivot for display ─────────────────────────────────────────────────────────
pivot = df_out.pivot(index="country", columns="dimension", values="xi")
pivot = pivot[DIMS]   # enforce column order

print("\n=== Compression factors xi (ENTSOE 2025 / GENeSYS 2025 median) ===\n")
print(pivot.round(1).to_string())

medians = pivot.median()
print(f"\nMedian across countries: {medians.round(1).to_dict()}")
