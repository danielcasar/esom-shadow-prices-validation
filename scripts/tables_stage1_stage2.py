"""
tables_stage1_stage2.py — Tables 6, 7 and C.3 and the values quoted in
Sections 3.2–3.3.

Table 6 (Stage 1): number of significant Kruskal–Wallis tests (p < 0.05) and
  mean epsilon-squared per dimension; ENTSO-E one test per country (2018–2025
  pooled), GENeSYS-MOD one test per country × scenario (2018/2025/2030 pooled).
  Also lists the non-significant GENeSYS-MOD day-of-week combinations
  (Section 3.2 footnote) and the effect-size ratios quoted in the text.

Table 7 (Stage 2), per source and dimension:
  % sig.      share of group-level t-tests with p < 0.05 (all countries,
              years, and scenarios)
  Range       per-unit group-mean deviation profile (unit = country for
              ENTSO-E, country × scenario for GENeSYS-MOD; deviations averaged
              over the unit's years); lower/upper bound = mean across units
              of the profile minimum/maximum (EUR/MWh)
  |Δ%|        mean absolute relative deviation across all group tests
  Range ratio mean across country × scenario of
              ENTSO-E country range / GENeSYS-MOD country-scenario range

Table C.3: group-level significance rates (%) under no correction, Bonferroni
  (alpha/k) and Benjamini–Hochberg FDR, applied within each source × scenario ×
  country × year × dimension family of k group tests, then averaged.

Inputs
------
results/intermediate/stage1_kw_pooled.csv
results/intermediate/stage2_ttest_groups_detail.csv

Outputs
-------
results/tables/Table_6.csv, Table_7.csv, Table_C3.csv
results/tables/values_tables_stage1_stage2.csv
"""

import numpy as np
import pandas as pd

from config import RESULTS_DIR
from outputs import ValueLog, save_table

ALPHA = 0.05
DIMS = ["hour", "weekday", "month", "season"]
DIM_LABELS = {"hour": "Hour-of-Day", "weekday": "Day-of-Week",
              "month": "Month-of-Year", "season": "Season"}
SOURCES = {"ENTSOE": "ENTSO-E", "GENeSYS-MOD": "GENeSYS-MOD"}


def table_6(log: ValueLog) -> None:
    kw = pd.read_csv(RESULTS_DIR / "stage1_kw_pooled.csv")
    rows = []
    eps = {}
    for dim in DIMS:
        row = {"Dimension": DIM_LABELS[dim]}
        for src, label in SOURCES.items():
            sub = kw[(kw["source"] == src) & (kw["dimension"] == dim)]
            n_sig = int((sub["p_value"] < ALPHA).sum())
            eps[(src, dim)] = sub["effect_size"].mean()
            row[f"{label} Sig."] = f"{n_sig}/{len(sub)}"
            row[f"{label} mean eps2"] = round(eps[(src, dim)], 3)
            log.add("Table 6", f"{label} {dim} significant tests", n_sig)
            log.add("Table 6", f"{label} {dim} number of tests", len(sub))
            log.add("Table 6", f"{label} {dim} mean epsilon-squared", eps[(src, dim)])
        rows.append(row)
    table = pd.DataFrame(rows)
    save_table(table, "Table_6", index=False)
    print(table.to_string(index=False))

    ns = kw[(kw["source"] == "GENeSYS-MOD") & (kw["dimension"] == "weekday")
            & (kw["p_value"] >= ALPHA)]
    print("\nNon-significant GENeSYS-MOD day-of-week combinations (Section 3.2 footnote):")
    for country, grp in ns.groupby("country"):
        print(f"  {country}: {', '.join(sorted(grp['scenario']))}")

    ratios = {
        "day-of-week effect-size ratio (ENTSO-E/GENeSYS-MOD)":
            eps[("ENTSOE", "weekday")] / eps[("GENeSYS-MOD", "weekday")],
        "month-of-year effect-size ratio (GENeSYS-MOD/ENTSO-E)":
            eps[("GENeSYS-MOD", "month")] / eps[("ENTSOE", "month")],
        "season effect-size ratio (GENeSYS-MOD/ENTSO-E)":
            eps[("GENeSYS-MOD", "season")] / eps[("ENTSOE", "season")],
    }
    for item, value in ratios.items():
        log.add("Section 3.2", item, value)
        print(f"  {item}: {value:.1f}")


def unit_profiles(sub: pd.DataFrame, unit: list) -> pd.DataFrame:
    """Group-mean deviation profile per unit (rows) and group (columns)."""
    return sub.groupby(unit + ["group"])["deviation"].mean().unstack()


def table_7(detail: pd.DataFrame, log: ValueLog) -> None:
    rows = []
    for dim in DIMS:
        sub = detail[detail["dimension"] == dim]
        e = sub[sub["source"] == "ENTSOE"]
        g = sub[sub["source"] == "GENeSYS-MOD"]
        e_prof = unit_profiles(e, ["country"])
        g_prof = unit_profiles(g, ["country", "scenario"])

        row = {"Dimension": DIM_LABELS[dim]}
        for label, src, prof in (("ENTSO-E", e, e_prof), ("GENeSYS-MOD", g, g_prof)):
            pct_sig = 100 * src["significant"].mean()
            lo, hi = prof.min(axis=1).mean(), prof.max(axis=1).mean()
            abs_pct = src["deviation_pct"].abs().mean()
            row[f"{label} % sig."] = round(pct_sig, 1)
            row[f"{label} range low"] = round(lo, 1)
            row[f"{label} range high"] = round(hi, 1)
            row[f"{label} mean |delta %|"] = round(abs_pct, 1)
            log.add("Table 7", f"{label} {dim} % significant", pct_sig)
            log.add("Table 7", f"{label} {dim} range low (EUR/MWh)", lo)
            log.add("Table 7", f"{label} {dim} range high (EUR/MWh)", hi)
            log.add("Table 7", f"{label} {dim} mean |delta %|", abs_pct)

        e_range = e_prof.max(axis=1) - e_prof.min(axis=1)
        g_range = g_prof.max(axis=1) - g_prof.min(axis=1)
        countries = g_range.index.get_level_values("country")
        ratio = (e_range.reindex(countries).values / g_range.values).mean()
        row["Range ratio (E/M)"] = round(ratio, 1)
        log.add("Table 7", f"{dim} range ratio (E/M)", ratio)
        rows.append(row)

    table = pd.DataFrame(rows)
    save_table(table, "Table_7", index=False)
    print("\n" + table.to_string(index=False))


def benjamini_hochberg(p_values: np.ndarray, alpha: float = ALPHA) -> np.ndarray:
    """Boolean array: True where the hypothesis is rejected under BH-FDR."""
    m = len(p_values)
    order = np.argsort(p_values)
    below = p_values[order] <= (np.arange(1, m + 1) / m) * alpha
    rejected = np.zeros(m, dtype=bool)
    if below.any():
        rejected[order[:np.where(below)[0].max() + 1]] = True
    return rejected


def table_c3(detail: pd.DataFrame, log: ValueLog) -> None:
    keys = ["source", "scenario", "country", "year", "dimension"]
    rates = []
    for key, grp in detail.groupby(keys):
        p = grp["p_value"].values
        k = len(p)
        rates.append({**dict(zip(keys, key)),
                      "Uncorr.": np.mean(p < ALPHA),
                      "Bonf.":   np.mean(p < ALPHA / k),
                      "BH-FDR":  np.mean(benjamini_hochberg(p))})
    rates = pd.DataFrame(rates)
    methods = ["Uncorr.", "Bonf.", "BH-FDR"]

    by_dim = rates.groupby(["dimension", "source"])[methods].mean().mul(100).unstack("source")
    overall = rates.groupby("source")[methods].mean().mul(100)

    rows = []
    for dim in DIMS + ["overall"]:
        row = {"Dimension": DIM_LABELS.get(dim, "Overall")}
        for src, label in SOURCES.items():
            for m in methods:
                v = overall.loc[src, m] if dim == "overall" else by_dim.loc[dim, (m, src)]
                row[f"{label} {m}"] = round(v, 1)
                log.add("Table C.3", f"{label} {dim} {m}", v)
        rows.append(row)
    table = pd.DataFrame(rows)
    save_table(table, "Table_C3", index=False)
    print("\n" + table.to_string(index=False))


def main():
    log = ValueLog("tables_stage1_stage2")
    table_6(log)
    detail = pd.read_csv(RESULTS_DIR / "stage2_ttest_groups_detail.csv")
    table_7(detail, log)
    table_c3(detail, log)
    log.save()


if __name__ == "__main__":
    main()
