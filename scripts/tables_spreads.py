"""
tables_spreads.py — Tables 9, 11, C.5 and C.6 and the daily spreads quoted in
Section 4.2.

Daily spread = max - min of the hourly prices within each calendar day,
averaged over all days of the year.

Section 4.2: mean daily spread in 2025, averaged across the 22 countries;
  ENTSO-E from observed prices, GENeSYS-MOD computed per scenario and then
  averaged across the four scenarios.
Table 9 (numeric columns): GENeSYS-MOD 2030 mean daily spread, min–max across
  the four scenarios; ENTSO-E 2025 mean daily spread. (The literature ranges in
  Table 9 are taken from the cited studies, not computed here.)
Table C.5: compression factors xi_{dim,c} (results/intermediate/
  compression_factors_2025.csv, produced by compute_compression_factors.py).
Table 11 / Table C.6: GENeSYS-MOD 2030 range of group-mean deviations (max -
  min per country × scenario, median across scenarios), multiplied by xi_{dim,c}
  per country, compared with the ENTSO-E 2025 range; medians across all
  countries (Table 11) and within clusters (Table C.6).

Inputs
------
data/ENTSOE_day_ahead_prices.csv, data/GENeSYS_MOD_prices.csv
results/intermediate/compression_factors_2025.csv
results/intermediate/stage2_ttest_groups_detail.csv

Outputs
-------
results/tables/Table_9.csv, Table_11.csv, Table_C5.csv, Table_C6.csv
results/intermediate/corrected_spreads_2030.csv
results/tables/values_tables_spreads.csv
"""

import pandas as pd

from config import (CLUSTERS, COUNTRIES, ENTSOE_PRICES_FILE, GENESYS_PRICES_FILE,
                    RESULTS_DIR, SCENARIOS)
from outputs import ValueLog, save_table

DIMS = ["hour", "weekday", "month", "season"]
DIM_LABELS = {"hour": "Hour-of-Day", "weekday": "Day-of-Week",
              "month": "Month-of-Year", "season": "Season"}
TABLE_9_COUNTRIES = ["DE", "FR", "AT", "CH", "PT"]
COUNTRY_TO_CLUSTER = {c: name for name, ms in CLUSTERS.items() for c in ms}


def daily_spread_entsoe(entsoe: pd.DataFrame, year: int) -> pd.Series:
    """Mean daily spread per country (calendar days in UTC, as in the data)."""
    sub = entsoe[entsoe.index.year == year][COUNTRIES]
    return sub.groupby(sub.index.date).agg(lambda x: x.max() - x.min()).mean()


def daily_spread_genesys(genesys: pd.DataFrame, year: int) -> pd.DataFrame:
    """Mean daily spread per scenario (rows) and country (columns)."""
    sub = genesys[genesys["year"] == year].copy()
    sub["day"] = (sub["Hour"] - 1) // 24
    return pd.DataFrame({
        scenario: grp.groupby("day")[COUNTRIES].agg(lambda x: x.max() - x.min()).mean()
        for scenario, grp in sub.groupby("scenario")
    }).T


def spreads(log: ValueLog) -> None:
    entsoe = pd.read_csv(ENTSOE_PRICES_FILE, index_col=0, parse_dates=True)
    genesys = pd.read_csv(GENESYS_PRICES_FILE)

    e25 = daily_spread_entsoe(entsoe, 2025)
    g25 = daily_spread_genesys(genesys, 2025)
    e_mean, g_mean = e25.mean(), g25.mean(axis=0).mean()
    log.add("Section 4.2", "ENTSO-E 2025 mean daily spread (EUR/MWh)", e_mean)
    log.add("Section 4.2", "GENeSYS-MOD 2025 mean daily spread (EUR/MWh)", g_mean)
    log.add("Section 4.2", "daily spread reduction (%)", 100 * (1 - g_mean / e_mean))
    print(f"Mean daily spread 2025: ENTSO-E {e_mean:.1f}, GENeSYS-MOD {g_mean:.1f} EUR/MWh "
          f"({100 * (1 - g_mean / e_mean):.0f}% lower)")

    g30 = daily_spread_genesys(genesys, 2030)
    rows = []
    for c in TABLE_9_COUNTRIES:
        lo, hi = g30[c].min(), g30[c].max()
        rows.append({"Country": c, "GENeSYS-MOD 2030 low": round(lo, 1),
                     "GENeSYS-MOD 2030 high": round(hi, 1), "ENTSO-E 2025": round(e25[c], 1)})
        log.add("Table 9", f"{c} GENeSYS-MOD 2030 daily spread, lowest scenario", lo)
        log.add("Table 9", f"{c} GENeSYS-MOD 2030 daily spread, highest scenario", hi)
        log.add("Table 9", f"{c} ENTSO-E 2025 daily spread", e25[c])
    table = pd.DataFrame(rows)
    save_table(table, "Table_9", index=False)
    print(table.to_string(index=False))


def compression_tables(log: ValueLog) -> None:
    cf = pd.read_csv(RESULTS_DIR / "compression_factors_2025.csv")
    xi = cf.pivot(index="country", columns="dimension", values="xi")[DIMS]
    table_c5 = xi.rename(columns=DIM_LABELS)
    save_table(table_c5.round(1), "Table_C5")
    for country, row in xi.iterrows():
        for dim in DIMS:
            log.add("Table C.5", f"{country} {dim} xi", row[dim])

    detail = pd.read_csv(RESULTS_DIR / "stage2_ttest_groups_detail.csv")
    g2030 = detail[(detail["source"] != "ENTSOE") & (detail["year"] == 2030)
                   & detail["scenario"].isin(SCENARIOS)]
    model_range = (g2030.groupby(["country", "dimension", "scenario"])["deviation"]
                   .agg(lambda x: x.max() - x.min())
                   .groupby(["country", "dimension"]).median()
                   .rename("model_range_2030").reset_index())
    spreads_df = model_range.merge(cf[["country", "dimension", "xi", "entsoe_range"]],
                                   on=["country", "dimension"], how="left")
    spreads_df = spreads_df.rename(columns={"entsoe_range": "entsoe_2025_range"})
    spreads_df["corrected_range_2030"] = spreads_df["model_range_2030"] * spreads_df["xi"]
    spreads_df["cluster"] = spreads_df["country"].map(COUNTRY_TO_CLUSTER)
    cols = ["model_range_2030", "xi", "corrected_range_2030", "entsoe_2025_range"]
    spreads_df[["country", "cluster", "dimension"] + cols].to_csv(
        RESULTS_DIR / "corrected_spreads_2030.csv", index=False)

    # Table 11 — Season, Month-of-Year, Hour-of-Day, Day-of-Week as in the paper
    med = spreads_df.groupby("dimension")[cols].median()
    order = ["season", "month", "hour", "weekday"]
    table_11 = med.loc[order].rename(index=DIM_LABELS)
    table_11.columns = ["GENeSYS 2030", "xi", "Corrected", "ENTSO-E 2025"]
    save_table(table_11.round(1), "Table_11")
    print("\n" + table_11.round(1).to_string())
    for dim in order:
        for col, label in zip(cols, table_11.columns):
            log.add("Table 11", f"{dim} {label}", med.loc[dim, col])

    # Table C.6 — cluster medians of corrected and ENTSO-E 2025 spreads
    cl = spreads_df.groupby(["cluster", "dimension"])[["corrected_range_2030",
                                                       "entsoe_2025_range"]].median()
    rows = []
    for cluster in CLUSTERS:
        row = {"Cluster": cluster}
        for dim in DIMS:
            corr, ent = cl.loc[(cluster, dim)]
            row[f"{DIM_LABELS[dim]} Corr."] = round(corr, 1)
            row[f"{DIM_LABELS[dim]} E-2025"] = round(ent, 1)
            log.add("Table C.6", f"{cluster} {dim} corrected", corr)
            log.add("Table C.6", f"{cluster} {dim} ENTSO-E 2025", ent)
        rows.append(row)
    save_table(pd.DataFrame(rows), "Table_C6", index=False)


def main():
    log = ValueLog("tables_spreads")
    spreads(log)
    compression_tables(log)
    log.save()


if __name__ == "__main__":
    main()
