"""
compute_extended_years_pearson.py — GENeSYS-MOD vs. ENTSO-E Pearson rho for
all GENeSYS-MOD model years, including those beyond 2030 (2035–2060).

Supports the Section 3.4.2 footnote stating that the day-of-week alignment of
2030 does not persist in later model years. For 2018, 2025 and 2030 the
values are identical to genesys_vs_entsoe_year_pearson.csv, which uses the
same profiles; the main analysis only uses those three years.

GENeSYS-MOD group means are computed directly from data/GENeSYS_MOD_prices.csv
(Hour 1–8760 mapped to an hourly calendar starting January 1 of the model
year); ENTSO-E group means are taken from the Stage 2 output.

Inputs
------
data/GENeSYS_MOD_prices.csv
results/intermediate/stage2_ttest_groups_detail.csv

Output
------
results/intermediate/genesys_vs_entsoe_all_years_pearson.csv
  Columns: country, scenario, dimension, genesys_year, entsoe_year,
           pearson_r, p_value, n_groups
"""

import warnings

import pandas as pd
from scipy.stats import pearsonr

from config import COUNTRIES, GENESYS_PRICES_FILE, RESULTS_DIR

warnings.filterwarnings("ignore")

OUT_FILE = RESULTS_DIR / "genesys_vs_entsoe_all_years_pearson.csv"
DIMS = ["hour", "weekday", "month", "season"]
MIN_GROUPS = 3
MONTH_TO_SEASON = {12: 1, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2,
                   6: 3, 7: 3, 8: 3, 9: 4, 10: 4, 11: 4}


def build_time_map(year: int) -> pd.DataFrame:
    idx = pd.date_range(start=f"{year}-01-01", periods=8760, freq="h")
    return pd.DataFrame({
        "Hour":    range(1, 8761),
        "hour":    idx.hour,
        "weekday": idx.weekday,
        "month":   idx.month,
        "season":  idx.month.map(MONTH_TO_SEASON),
    })


def genesys_group_means(prices: pd.DataFrame, year: int) -> pd.DataFrame:
    sub = prices[prices["year"] == year].merge(build_time_map(year), on="Hour", how="left")
    frames = []
    for scenario, sc in sub.groupby("scenario"):
        for country in COUNTRIES:
            for dim in DIMS:
                gm = sc.groupby(dim)[country].mean().rename("genesys_mean").reset_index()
                gm = gm.rename(columns={dim: "group"})
                gm[["country", "scenario", "dimension"]] = country, scenario, dim
                frames.append(gm)
    return pd.concat(frames, ignore_index=True)


def main():
    prices = pd.read_csv(GENESYS_PRICES_FILE)
    detail = pd.read_csv(RESULTS_DIR / "stage2_ttest_groups_detail.csv")
    entsoe = (detail[detail["source"] == "ENTSOE"]
              .groupby(["country", "year", "dimension", "group"])["mean_group"].mean()
              .reset_index()
              .rename(columns={"mean_group": "entsoe_mean", "year": "entsoe_year"}))

    rows = []
    for g_year in sorted(prices["year"].unique()):
        gm = genesys_group_means(prices, g_year)
        for (country, scenario, dim), grp_g in gm.groupby(["country", "scenario", "dimension"]):
            e_sub = entsoe[(entsoe["country"] == country) & (entsoe["dimension"] == dim)]
            for e_year, grp_e in e_sub.groupby("entsoe_year"):
                merged = (grp_e[["group", "entsoe_mean"]]
                          .merge(grp_g[["group", "genesys_mean"]], on="group")
                          .sort_values("group").dropna())
                if len(merged) < MIN_GROUPS:
                    continue
                r, p = pearsonr(merged["entsoe_mean"].values, merged["genesys_mean"].values)
                rows.append({"country": country, "scenario": scenario, "dimension": dim,
                             "genesys_year": int(g_year), "entsoe_year": int(e_year),
                             "pearson_r": round(r, 6), "p_value": p,
                             "n_groups": len(merged)})
        print(f"  GENeSYS-MOD {g_year}: done")

    result = pd.DataFrame(rows)
    result.to_csv(OUT_FILE, index=False)
    print(f"Exported {len(result):,} rows -> {OUT_FILE}")


if __name__ == "__main__":
    main()
