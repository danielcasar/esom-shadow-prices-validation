"""
tables_benchmark.py — Table 8 values, Table C.4, and the values quoted in
Sections 3.4.1–3.4.3.

Table 8 / Section 3.4.1 (ENTSO-E cross-year Pearson rho, 22 countries):
  - hour-of-day: median rho of adjacent year pairs (lag 1) and mean rho of the
    2018 vs. 2025 pair
  - day-of-week: smallest per-lag median rho across lags 1–7
  - month-of-year and season: mean rho over all year pairs, and over the year
    pairs not involving 2022
  - maximum width of the 95% bootstrap CI of the median cross-year rho: for
    each dimension and lag, the per-country median rho is resampled across the
    22 countries (10,000 draws, numpy seed 42), and the largest CI width over
    lags is reported

Table C.4: mean cross-year rho over the year pairs falling within the
  pre-crisis (2018–2020), crisis (2021–2023), post-crisis (2024–2025) and full
  (2018–2025) periods, for month-of-year and season.

Section 3.4.2 footnote: mean day-of-week model–market rho per GENeSYS-MOD
  year (all countries, scenarios, ENTSO-E years), including 2035–2060.

Section 3.4.3: mean absolute difference between Pearson and Spearman
  model–market correlations per dimension (Figure C.10).

Inputs
------
results/intermediate/entsoe_cross_year_pearson.csv
results/intermediate/genesys_vs_entsoe_all_years_pearson.csv
results/intermediate/stage3_pearson_correlations.csv

Outputs
-------
results/tables/Table_C4.csv
results/tables/bootstrap_ci_by_lag.csv
results/tables/values_tables_benchmark.csv
"""

import numpy as np
import pandas as pd

from config import RESULTS_DIR
from outputs import ValueLog, save_table

DIMS = ["hour", "weekday", "month", "season"]
N_BOOT = 10_000
CRISIS_YEAR = 2022
PERIODS = {
    "Pre-crisis (2018-2020)":  [2018, 2019, 2020],
    "Crisis (2021-2023)":      [2021, 2022, 2023],
    "Post-crisis (2024-2025)": [2024, 2025],
    "Full period (2018-2025)": list(range(2018, 2026)),
}


def benchmark_values(cy: pd.DataFrame, log: ValueLog) -> None:
    hod = cy[cy["dimension"] == "hour"]
    log.add("Table 8", "hour adjacent-year median rho", hod.loc[hod["lag"] == 1, "rho"].median())
    log.add("Table 8", "hour 2018 vs 2025 mean rho",
            hod.loc[(hod["year1"] == 2018) & (hod["year2"] == 2025), "rho"].mean())
    dow = cy[cy["dimension"] == "weekday"]
    log.add("Table 8", "weekday minimum per-lag median rho", dow.groupby("lag")["rho"].median().min())
    for dim in ("month", "season"):
        sub = cy[cy["dimension"] == dim]
        no_crisis = sub[(sub["year1"] != CRISIS_YEAR) & (sub["year2"] != CRISIS_YEAR)]
        log.add("Table 8", f"{dim} mean rho", sub["rho"].mean())
        log.add("Table 8", f"{dim} mean rho excluding 2022", no_crisis["rho"].mean())


def bootstrap_ci_by_lag(cy: pd.DataFrame, log: ValueLog) -> None:
    rng = np.random.default_rng(42)
    records = []
    for dim in DIMS:
        for lag in sorted(cy["lag"].unique()):
            sub = cy[(cy["dimension"] == dim) & (cy["lag"] == lag)]
            vals = sub.groupby("country")["rho"].median().values
            if len(vals) < 2:
                continue
            boot = np.array([np.median(rng.choice(vals, size=len(vals), replace=True))
                             for _ in range(N_BOOT)])
            lo, hi = np.percentile(boot, 2.5), np.percentile(boot, 97.5)
            records.append({"dimension": dim, "lag": lag, "n_countries": len(vals),
                            "median_rho": np.median(vals), "ci_lo": lo, "ci_hi": hi,
                            "ci_width": hi - lo})
    boot_df = pd.DataFrame(records)
    save_table(boot_df.round(4), "bootstrap_ci_by_lag", index=False)
    for dim, width in boot_df.groupby("dimension")["ci_width"].max().items():
        log.add("Section 3.4.1", f"{dim} maximum bootstrap CI width", width)
        print(f"  max CI width {dim:8s}: {width:.2f}")


def table_c4(cy: pd.DataFrame, log: ValueLog) -> None:
    rows = []
    for dim, label in (("month", "Month-of-year"), ("season", "Season")):
        row = {"Dimension": label}
        for period, years in PERIODS.items():
            sub = cy[(cy["dimension"] == dim) & cy["year1"].isin(years) & cy["year2"].isin(years)]
            row[period] = round(sub["rho"].mean(), 2)
            log.add("Table C.4", f"{dim} {period}", sub["rho"].mean())
        rows.append(row)
    table = pd.DataFrame(rows)
    save_table(table, "Table_C4", index=False)
    print(table.to_string(index=False))


def extended_years(log: ValueLog) -> None:
    ext = pd.read_csv(RESULTS_DIR / "genesys_vs_entsoe_all_years_pearson.csv")
    dow = ext[ext["dimension"] == "weekday"].groupby("genesys_year")["pearson_r"].mean()
    print("\nMean day-of-week model-market rho by GENeSYS-MOD year:")
    for year, rho in dow.items():
        log.add("Section 3.4.2 footnote", f"weekday mean rho {year}", rho)
        print(f"  {year}: {rho:.2f}")


def spearman_mae(log: ValueLog) -> None:
    s3 = pd.read_csv(RESULTS_DIR / "stage3_pearson_correlations.csv")
    mae = (s3["pearson_r"] - s3["spearman_r"]).abs().groupby(s3["dimension"]).mean()
    print("\nMean absolute Pearson-Spearman difference:")
    for dim, v in mae.items():
        log.add("Section 3.4.3", f"{dim} Pearson-Spearman MAE", v)
        print(f"  {dim:8s}: {v:.3f}")


def main():
    log = ValueLog("tables_benchmark")
    cy = pd.read_csv(RESULTS_DIR / "entsoe_cross_year_pearson.csv")
    cy["lag"] = (cy["year2"] - cy["year1"]).abs()

    benchmark_values(cy, log)
    bootstrap_ci_by_lag(cy, log)
    table_c4(cy, log)
    extended_years(log)
    spearman_mae(log)
    log.save()


if __name__ == "__main__":
    main()
