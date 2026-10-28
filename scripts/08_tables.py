"""
08_tables.py — All tables of the paper, the Figure 1 data, and the numbers quoted in the text.

Sections (in paper order):
  Figure 1     coordinates of the France price patterns (pooled medians)
  Table 4      within-cluster Pearson rho; footnote on shared price nodes
  Table 5      distributional properties (2025); Section 3.1 ranges; abstract
  Tables 6, 7, C.3   Stage 1 and Stage 2 summaries, multiple-testing check
  Table 8, C.4 benchmark values, bootstrap CI widths, sub-period benchmark,
               Pearson-Spearman MAE, model years after 2030
  Tables 9, 11, C.5, C.6   daily spreads and corrected spreads

Inputs
------
data/ENTSOE_day_ahead_prices.csv, data/GENeSYS_MOD_prices.csv
results/intermediate/*.csv (written by scripts 01-07)

Outputs
-------
results/tables/Table_*.csv, results/tables/bootstrap_ci_by_lag.csv
results/figures/Figure_1_data.csv
results/intermediate/corrected_spreads_2030.csv
results/tables/values_tables.csv   every number quoted in the text, labelled
                                   with its location in the paper
"""

import numpy as np
import pandas as pd
from scipy import stats

from config import (CLUSTERS, COUNTRIES, ENTSOE_PRICES_FILE, ENTSOE_YEARS,
                    GENESYS_PRICES_FILE, GENESYS_YEARS, PLOTS_DIR, RESULTS_DIR,
                    SCENARIOS)
from helpers import ValueLog, save_table
from figure_04_annual_prices import annual_means_entsoe, annual_means_genesys
from figure_05_price_duration_curves import collect_entsoe_pdcs, collect_genesys_pdcs

ALPHA = 0.05
DIMS = ["hour", "weekday", "month", "season"]
DIM_LABELS = {"hour": "Hour-of-Day", "weekday": "Day-of-Week",
              "month": "Month-of-Year", "season": "Season"}
SOURCES = {"ENTSOE": "ENTSO-E", "GENeSYS-MOD": "GENeSYS-MOD"}
COUNTRY_TO_CLUSTER = {c: name for name, ms in CLUSTERS.items() for c in ms}


# ═══════════════════════════════════════════════════════════════════════════
# Figure 1 — France price patterns
# ═══════════════════════════════════════════════════════════════════════════
# Median of all hourly prices in each hour-of-day, day-of-week and
# month-of-year group, pooled over 2018–2025 (the figure is drawn in LaTeX).

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def figure_1(entsoe: pd.DataFrame, log: ValueLog) -> None:
    prices = entsoe["FR"].dropna()
    prices = prices[prices.index.year.isin(ENTSOE_YEARS)]
    groupings = {
        "hour":    (prices.index.hour, list(range(24))),
        "weekday": (prices.index.weekday, WEEKDAYS),
        "month":   (prices.index.month, MONTHS),
    }
    rows = []
    for dim, (keys, labels) in groupings.items():
        medians = prices.groupby(keys).median()
        for (group, value), label in zip(medians.items(), labels):
            rows.append({"dimension": dim, "group": label, "median_price": round(value, 1)})
            log.add("Figure 1", f"{dim} {label}", value)
    overall = prices.median()
    rows.append({"dimension": "overall", "group": "all hours", "median_price": round(overall, 1)})
    log.add("Figure 1", "overall median", overall)

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(PLOTS_DIR / "Figure_1_data.csv", index=False)


# ═══════════════════════════════════════════════════════════════════════════
# Table 4 — country clusters (Section 2.2.3)
# ═══════════════════════════════════════════════════════════════════════════
# Within-cluster mean Pearson rho, pooled over dimensions, years (and
# scenarios); all-country mean; share of model hours with identical prices.

MULTI_COUNTRY = ["Iberian", "Baltic", "South-East", "Core-East", "Core-West"]


def _mean_rho(df: pd.DataFrame, members: list) -> float:
    sub = df[df["country1"].isin(members) & df["country2"].isin(members)
             & (df["country1"] != df["country2"])]
    return sub["rho"].mean()


def table_4(genesys_prices: pd.DataFrame, log: ValueLog) -> None:
    entsoe = pd.read_csv(RESULTS_DIR / "entsoe_cross_country_pearson.csv")
    genesys = pd.read_csv(RESULTS_DIR / "genesys_cross_country_pearson.csv")
    entsoe = entsoe[entsoe["country1"].isin(COUNTRIES) & entsoe["country2"].isin(COUNTRIES)]
    genesys = genesys[genesys["country1"].isin(COUNTRIES) & genesys["country2"].isin(COUNTRIES)]

    rows = []
    for cluster in MULTI_COUNTRY:
        members = CLUSTERS[cluster]
        e, g = _mean_rho(entsoe, members), _mean_rho(genesys, members)
        rows.append({"Cluster": cluster, "Countries": ", ".join(members),
                     "n": len(members), "ENTSO-E rho": round(e, 3),
                     "GENeSYS-MOD rho": round(g, 3)})
        log.add("Table 4", f"{cluster} ENTSO-E rho", e)
        log.add("Table 4", f"{cluster} GENeSYS-MOD rho", g)
    singletons = [c for c in CLUSTERS if c not in MULTI_COUNTRY]
    rows.append({"Cluster": "Singletons", "Countries": ", ".join(singletons), "n": 1,
                 "ENTSO-E rho": None, "GENeSYS-MOD rho": None})
    save_table(pd.DataFrame(rows), "Table_4", index=False)

    log.add("Table 4", "all-country ENTSO-E rho",
            entsoe.loc[entsoe["country1"] != entsoe["country2"], "rho"].mean())
    log.add("Table 4", "all-country GENeSYS-MOD rho",
            genesys.loc[genesys["country1"] != genesys["country2"], "rho"].mean())

    prices = genesys_prices[genesys_prices["year"].isin(GENESYS_YEARS)]
    log.add("Section 2.2.3 footnote", "HR/HU/SI identical price (% of hours)",
            ((prices["HR"] == prices["HU"]) & (prices["HU"] == prices["SI"])).mean() * 100)
    log.add("Section 2.2.3 footnote", "LT/LV identical price (% of hours)",
            (prices["LT"] == prices["LV"]).mean() * 100)


# ═══════════════════════════════════════════════════════════════════════════
# Table 5 — distributional properties (Section 3.1, abstract)
# ═══════════════════════════════════════════════════════════════════════════
# 2025 hourly prices per country, median across the 22 countries;
# GENeSYS-MOD prices averaged across the four scenarios hour by hour.
# Skewness and excess kurtosis are the moment estimators of Appendix B.

YEAR = 2025


def _distribution_metrics(prices) -> dict:
    p = np.asarray(prices, dtype=float)
    p = p[~np.isnan(p)]
    mean = p.mean()
    return {
        "Mean (EUR/MWh)":                    mean,
        "Standard deviation (EUR/MWh)":      p.std(),
        "Skewness":                          stats.skew(p),
        "Excess kurtosis":                   stats.kurtosis(p),
        "5th percentile (EUR/MWh)":          np.percentile(p, 5),
        "95th percentile (EUR/MWh)":         np.percentile(p, 95),
        "Negative-price hours (%)":          100 * np.mean(p < 0),
        "Extreme-price hours (>3x mean, %)": 100 * np.mean(p > 3 * mean),
    }


def table_5(entsoe: pd.DataFrame, genesys: pd.DataFrame, log: ValueLog) -> None:
    e25 = entsoe[entsoe.index.year == YEAR]
    g25 = genesys[genesys["year"] == YEAR].groupby("Hour")[COUNTRIES].mean()
    e_metrics = pd.DataFrame({c: _distribution_metrics(e25[c]) for c in COUNTRIES}).T
    g_metrics = pd.DataFrame({c: _distribution_metrics(g25[c]) for c in COUNTRIES}).T
    table = pd.DataFrame({"ENTSO-E": e_metrics.median(), "GENeSYS-MOD": g_metrics.median()})
    save_table(table.round(2), "Table_5")
    for metric, row in table.iterrows():
        log.add("Table 5", f"ENTSO-E {metric}", row["ENTSO-E"])
        log.add("Table 5", f"GENeSYS-MOD {metric}", row["GENeSYS-MOD"])

    # Section 3.1, text on Figure 4: range of annual mean prices
    am_e = annual_means_entsoe(ENTSOE_PRICES_FILE)["mean_price"]
    am_g = annual_means_genesys(GENESYS_PRICES_FILE)["mean_price"]
    log.add("Section 3.1", "ENTSO-E annual mean, minimum (EUR/MWh)", am_e.min())
    log.add("Section 3.1", "ENTSO-E annual mean, maximum (EUR/MWh)", am_e.max())
    log.add("Section 3.1", "GENeSYS-MOD annual mean, 25th percentile (EUR/MWh)", am_g.quantile(0.25))
    log.add("Section 3.1", "GENeSYS-MOD annual mean, 75th percentile (EUR/MWh)", am_g.quantile(0.75))

    # Section 3.1, text on Figure 5: range of the median price duration curve
    for label, pdcs in (("ENTSO-E", collect_entsoe_pdcs()), ("GENeSYS-MOD", collect_genesys_pdcs())):
        median_curve = np.median(pdcs, axis=0)
        log.add("Section 3.1", f"{label} median duration curve, minimum (EUR/MWh)", median_curve.min())
        log.add("Section 3.1", f"{label} median duration curve, maximum (EUR/MWh)", median_curve.max())

    # Section 3.1 (Figure 6) and abstract: median 2025 compression factor
    cf = pd.read_csv(RESULTS_DIR / "compression_factors_2025.csv")
    for dim in DIMS:
        ratio = cf.loc[cf["dimension"] == dim, "xi"].median()
        for exhibit in ("Section 3.1", "Abstract"):
            log.add(exhibit, f"{dim} 2025 peak-to-trough ratio (ENTSO-E/GENeSYS-MOD)", ratio)


# ═══════════════════════════════════════════════════════════════════════════
# Tables 6, 7, C.3 — Stage 1 and Stage 2 (Sections 3.2, 3.3)
# ═══════════════════════════════════════════════════════════════════════════

def table_6(log: ValueLog) -> None:
    """Significant Kruskal-Wallis tests and mean epsilon-squared per dimension."""
    kw = pd.read_csv(RESULTS_DIR / "stage1_kw_pooled.csv")
    rows, eps = [], {}
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
    save_table(pd.DataFrame(rows), "Table_6", index=False)

    ns = kw[(kw["source"] == "GENeSYS-MOD") & (kw["dimension"] == "weekday") & (kw["p_value"] >= ALPHA)]
    print("Non-significant GENeSYS-MOD day-of-week combinations (Section 3.2 footnote):")
    for country, grp in ns.groupby("country"):
        print(f"  {country}: {', '.join(sorted(grp['scenario']))}")

    log.add("Section 3.2", "day-of-week effect-size ratio (ENTSO-E/GENeSYS-MOD)",
            eps[("ENTSOE", "weekday")] / eps[("GENeSYS-MOD", "weekday")])
    log.add("Section 3.2", "month-of-year effect-size ratio (GENeSYS-MOD/ENTSO-E)",
            eps[("GENeSYS-MOD", "month")] / eps[("ENTSOE", "month")])
    log.add("Section 3.2", "season effect-size ratio (GENeSYS-MOD/ENTSO-E)",
            eps[("GENeSYS-MOD", "season")] / eps[("ENTSOE", "season")])


def _unit_profiles(sub: pd.DataFrame, unit: list) -> pd.DataFrame:
    """Group-mean deviation profile per unit (rows) and group (columns)."""
    return sub.groupby(unit + ["group"])["deviation"].mean().unstack()


def table_7(detail: pd.DataFrame, log: ValueLog) -> None:
    """
    % sig.  share of group t-tests with p < 0.05
    Range   per-unit deviation profile (unit = country for ENTSO-E, country x
            scenario for GENeSYS-MOD, averaged over years); bounds = mean over
            units of the profile minimum / maximum (EUR/MWh)
    |d%|    mean absolute relative deviation
    Ratio   mean over country x scenario of ENTSO-E range / GENeSYS-MOD range
    """
    rows = []
    for dim in DIMS:
        sub = detail[detail["dimension"] == dim]
        e = sub[sub["source"] == "ENTSOE"]
        g = sub[sub["source"] == "GENeSYS-MOD"]
        e_prof = _unit_profiles(e, ["country"])
        g_prof = _unit_profiles(g, ["country", "scenario"])
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
    save_table(pd.DataFrame(rows), "Table_7", index=False)


def _benjamini_hochberg(p_values: np.ndarray, alpha: float = ALPHA) -> np.ndarray:
    """Boolean array: True where the hypothesis is rejected under BH-FDR."""
    m = len(p_values)
    order = np.argsort(p_values)
    below = p_values[order] <= (np.arange(1, m + 1) / m) * alpha
    rejected = np.zeros(m, dtype=bool)
    if below.any():
        rejected[order[:np.where(below)[0].max() + 1]] = True
    return rejected


def table_c3(detail: pd.DataFrame, log: ValueLog) -> None:
    """Significance rates under no correction, Bonferroni and BH-FDR, applied
    within each source x scenario x country x year x dimension family."""
    keys = ["source", "scenario", "country", "year", "dimension"]
    rates = []
    for key, grp in detail.groupby(keys):
        p = grp["p_value"].values
        k = len(p)
        rates.append({**dict(zip(keys, key)),
                      "Uncorr.": np.mean(p < ALPHA),
                      "Bonf.":   np.mean(p < ALPHA / k),
                      "BH-FDR":  np.mean(_benjamini_hochberg(p))})
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
    save_table(pd.DataFrame(rows), "Table_C3", index=False)


# ═══════════════════════════════════════════════════════════════════════════
# Table 8, Table C.4 — benchmark (Sections 3.4.1–3.4.3)
# ═══════════════════════════════════════════════════════════════════════════

N_BOOT = 10_000
CRISIS_YEAR = 2022
PERIODS = {
    "Pre-crisis (2018-2020)":  [2018, 2019, 2020],
    "Crisis (2021-2023)":      [2021, 2022, 2023],
    "Post-crisis (2024-2025)": [2024, 2025],
    "Full period (2018-2025)": list(range(2018, 2026)),
}


def table_8(cy: pd.DataFrame, log: ValueLog) -> None:
    """Values in Table 8: cross-year ENTSO-E rho by dimension."""
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
    """Section 3.4.1: 95% bootstrap CI of the median cross-year rho per
    dimension and lag, resampling the 22 country medians (seed 42)."""
    rng = np.random.default_rng(42)
    records = []
    for dim in DIMS:
        for lag in sorted(cy["lag"].unique()):
            vals = cy[(cy["dimension"] == dim) & (cy["lag"] == lag)].groupby("country")["rho"].median().values
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


def table_c4(cy: pd.DataFrame, log: ValueLog) -> None:
    """Mean cross-year rho over the year pairs within each sub-period."""
    rows = []
    for dim, label in (("month", "Month-of-year"), ("season", "Season")):
        row = {"Dimension": label}
        for period, years in PERIODS.items():
            v = cy[(cy["dimension"] == dim) & cy["year1"].isin(years) & cy["year2"].isin(years)]["rho"].mean()
            row[period] = round(v, 2)
            log.add("Table C.4", f"{dim} {period}", v)
        rows.append(row)
    save_table(pd.DataFrame(rows), "Table_C4", index=False)


def text_section_3_4(log: ValueLog) -> None:
    """Section 3.4.2 footnote (day-of-week rho by model year, incl. after 2030)
    and Section 3.4.3 (mean absolute Pearson-Spearman difference)."""
    ext = pd.read_csv(RESULTS_DIR / "genesys_vs_entsoe_all_years_pearson.csv")
    for year, rho in ext[ext["dimension"] == "weekday"].groupby("genesys_year")["pearson_r"].mean().items():
        log.add("Section 3.4.2 footnote", f"weekday mean rho {year}", rho)
    s3 = pd.read_csv(RESULTS_DIR / "stage3_pearson_correlations.csv")
    for dim, v in (s3["pearson_r"] - s3["spearman_r"]).abs().groupby(s3["dimension"]).mean().items():
        log.add("Section 3.4.3", f"{dim} Pearson-Spearman MAE", v)


# ═══════════════════════════════════════════════════════════════════════════
# Tables 9, 11, C.5, C.6 — spreads (Sections 4.1–4.3)
# ═══════════════════════════════════════════════════════════════════════════
# Daily spread = max - min of the hourly prices within a calendar day,
# averaged over all days of the year.

TABLE_9_COUNTRIES = ["DE", "FR", "AT", "CH", "PT"]


def _daily_spread_entsoe(entsoe: pd.DataFrame, year: int) -> pd.Series:
    sub = entsoe[entsoe.index.year == year][COUNTRIES]
    return sub.groupby(sub.index.date).agg(lambda x: x.max() - x.min()).mean()


def _daily_spread_genesys(genesys: pd.DataFrame, year: int) -> pd.DataFrame:
    sub = genesys[genesys["year"] == year].copy()
    sub["day"] = (sub["Hour"] - 1) // 24
    return pd.DataFrame({
        scenario: grp.groupby("day")[COUNTRIES].agg(lambda x: x.max() - x.min()).mean()
        for scenario, grp in sub.groupby("scenario")
    }).T


def table_9(entsoe: pd.DataFrame, genesys: pd.DataFrame, log: ValueLog) -> None:
    """Table 9 (model and ENTSO-E columns; literature ranges are from the
    cited studies) and the 2025 daily spreads quoted in Section 4.2."""
    e25 = _daily_spread_entsoe(entsoe, 2025)
    g25 = _daily_spread_genesys(genesys, 2025)
    e_mean, g_mean = e25.mean(), g25.mean(axis=0).mean()
    log.add("Section 4.2", "ENTSO-E 2025 mean daily spread (EUR/MWh)", e_mean)
    log.add("Section 4.2", "GENeSYS-MOD 2025 mean daily spread (EUR/MWh)", g_mean)
    log.add("Section 4.2", "daily spread reduction (%)", 100 * (1 - g_mean / e_mean))

    g30 = _daily_spread_genesys(genesys, 2030)
    rows = []
    for c in TABLE_9_COUNTRIES:
        lo, hi = g30[c].min(), g30[c].max()
        rows.append({"Country": c, "GENeSYS-MOD 2030 low": round(lo, 1),
                     "GENeSYS-MOD 2030 high": round(hi, 1), "ENTSO-E 2025": round(e25[c], 1)})
        log.add("Table 9", f"{c} GENeSYS-MOD 2030 daily spread, lowest scenario", lo)
        log.add("Table 9", f"{c} GENeSYS-MOD 2030 daily spread, highest scenario", hi)
        log.add("Table 9", f"{c} ENTSO-E 2025 daily spread", e25[c])
    save_table(pd.DataFrame(rows), "Table_9", index=False)


def tables_compression(log: ValueLog) -> None:
    """Table C.5 (compression factors xi) and Tables 11 / C.6: GENeSYS-MOD
    2030 group-deviation range (median over scenarios) times xi per country,
    against the ENTSO-E 2025 range; medians over all countries / clusters."""
    cf = pd.read_csv(RESULTS_DIR / "compression_factors_2025.csv")
    xi = cf.pivot(index="country", columns="dimension", values="xi")[DIMS]
    save_table(xi.rename(columns=DIM_LABELS).round(1), "Table_C5")
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
    spreads = model_range.merge(cf[["country", "dimension", "xi", "entsoe_range"]],
                                on=["country", "dimension"], how="left")
    spreads = spreads.rename(columns={"entsoe_range": "entsoe_2025_range"})
    spreads["corrected_range_2030"] = spreads["model_range_2030"] * spreads["xi"]
    spreads["cluster"] = spreads["country"].map(COUNTRY_TO_CLUSTER)
    cols = ["model_range_2030", "xi", "corrected_range_2030", "entsoe_2025_range"]
    spreads[["country", "cluster", "dimension"] + cols].to_csv(
        RESULTS_DIR / "corrected_spreads_2030.csv", index=False)

    med = spreads.groupby("dimension")[cols].median()
    order = ["season", "month", "hour", "weekday"]
    table_11 = med.loc[order].rename(index=DIM_LABELS)
    table_11.columns = ["GENeSYS 2030", "xi", "Corrected", "ENTSO-E 2025"]
    save_table(table_11.round(1), "Table_11")
    for dim in order:
        for col, label in zip(cols, table_11.columns):
            log.add("Table 11", f"{dim} {label}", med.loc[dim, col])

    cl = spreads.groupby(["cluster", "dimension"])[["corrected_range_2030", "entsoe_2025_range"]].median()
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


# ═══════════════════════════════════════════════════════════════════════════

def main():
    log = ValueLog("tables")
    entsoe = pd.read_csv(ENTSOE_PRICES_FILE, index_col=0, parse_dates=True)
    genesys = pd.read_csv(GENESYS_PRICES_FILE)
    detail = pd.read_csv(RESULTS_DIR / "stage2_ttest_groups_detail.csv")
    cy = pd.read_csv(RESULTS_DIR / "entsoe_cross_year_pearson.csv")
    cy["lag"] = (cy["year2"] - cy["year1"]).abs()

    figure_1(entsoe, log)
    table_4(genesys, log)
    table_5(entsoe, genesys, log)
    table_6(log)
    table_7(detail, log)
    table_c3(detail, log)
    table_8(cy, log)
    bootstrap_ci_by_lag(cy, log)
    table_c4(cy, log)
    text_section_3_4(log)
    table_9(entsoe, genesys, log)
    tables_compression(log)
    log.save()


if __name__ == "__main__":
    main()
