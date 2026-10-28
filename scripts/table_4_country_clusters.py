"""
table_4_country_clusters.py — Table 4 and its footnote (Section 2.2.3).

Table 4: within-cluster mean Pearson rho for ENTSO-E and GENeSYS-MOD, pooled
over all four temporal dimensions and all years (and, for GENeSYS-MOD, all
scenarios), plus the all-country mean over every country pair.

Footnote: share of GENeSYS-MOD hours (2018, 2025, 2030; all scenarios) in which
several countries share an identical shadow price (HR/HU/SI and LT/LV).

Inputs
------
results/intermediate/entsoe_cross_country_pearson.csv
results/intermediate/genesys_cross_country_pearson.csv
data/GENeSYS_MOD_prices.csv

Outputs
-------
results/tables/Table_4.csv
results/tables/values_table_4_country_clusters.csv
"""

import pandas as pd

from config import (CLUSTERS, COUNTRIES, GENESYS_YEARS, GENESYS_PRICES_FILE,
                    RESULTS_DIR)
from outputs import ValueLog, save_table

MULTI_COUNTRY = ["Iberian", "Baltic", "South-East", "Core-East", "Core-West"]


def mean_rho(df: pd.DataFrame, members: list) -> float:
    sub = df[df["country1"].isin(members) & df["country2"].isin(members)
             & (df["country1"] != df["country2"])]
    return sub["rho"].mean()


def main():
    log = ValueLog("table_4_country_clusters")

    entsoe = pd.read_csv(RESULTS_DIR / "entsoe_cross_country_pearson.csv")
    genesys = pd.read_csv(RESULTS_DIR / "genesys_cross_country_pearson.csv")
    entsoe = entsoe[entsoe["country1"].isin(COUNTRIES) & entsoe["country2"].isin(COUNTRIES)]
    genesys = genesys[genesys["country1"].isin(COUNTRIES) & genesys["country2"].isin(COUNTRIES)]

    rows = []
    for cluster in MULTI_COUNTRY:
        members = CLUSTERS[cluster]
        e, g = mean_rho(entsoe, members), mean_rho(genesys, members)
        rows.append({"Cluster": cluster, "Countries": ", ".join(members),
                     "n": len(members), "ENTSO-E rho": round(e, 3),
                     "GENeSYS-MOD rho": round(g, 3)})
        log.add("Table 4", f"{cluster} ENTSO-E rho", e)
        log.add("Table 4", f"{cluster} GENeSYS-MOD rho", g)

    singletons = [c for c in CLUSTERS if c not in MULTI_COUNTRY]
    rows.append({"Cluster": "Singletons", "Countries": ", ".join(singletons), "n": 1,
                 "ENTSO-E rho": None, "GENeSYS-MOD rho": None})

    e_all = entsoe.loc[entsoe["country1"] != entsoe["country2"], "rho"].mean()
    g_all = genesys.loc[genesys["country1"] != genesys["country2"], "rho"].mean()
    log.add("Table 4", "all-country ENTSO-E rho", e_all)
    log.add("Table 4", "all-country GENeSYS-MOD rho", g_all)

    table = pd.DataFrame(rows)
    save_table(table, "Table_4", index=False)
    print(table.to_string(index=False))
    print(f"All-country mean rho: ENTSO-E {e_all:.3f}, GENeSYS-MOD {g_all:.3f}")

    # ── Footnote: shared GENeSYS-MOD price nodes ─────────────────────────────
    prices = pd.read_csv(GENESYS_PRICES_FILE)
    prices = prices[prices["year"].isin(GENESYS_YEARS)]
    hr_hu_si = ((prices["HR"] == prices["HU"]) & (prices["HU"] == prices["SI"])).mean() * 100
    lt_lv = (prices["LT"] == prices["LV"]).mean() * 100
    log.add("Section 2.2.3 footnote", "HR/HU/SI identical price (% of hours)", hr_hu_si)
    log.add("Section 2.2.3 footnote", "LT/LV identical price (% of hours)", lt_lv)
    print(f"Identical GENeSYS-MOD prices: HR/HU/SI {hr_hu_si:.1f}% of hours, "
          f"LT/LV {lt_lv:.1f}% of hours")

    log.save()


if __name__ == "__main__":
    main()
