"""
table_5_distribution_metrics.py — Table 5 and the values quoted in Section 3.1.

Table 5: distributional properties of hourly prices in the 2025 comparison year,
computed per country and reported as the median across the 22 countries.
  ENTSO-E     : observed 2025 hourly day-ahead prices of each country.
  GENeSYS-MOD : 2025 hourly shadow prices of each country, averaged across the
                four scenarios hour by hour (the same series as Figure C.2).
Skewness and excess kurtosis are the moment-based (biased) estimators of
Appendix B (scipy.stats.skew / scipy.stats.kurtosis with default settings).

Section 3.1 text values:
  - range of annual mean prices (Figure 4): min/max of ENTSO-E country-year
    means; interquartile range of GENeSYS-MOD country-scenario-year means
  - range of the median price duration curve (Figure 5)
  - ratio of the 2025 peak-to-trough ranges, ENTSO-E 2025 vs. GENeSYS-MOD
    2025, median across countries (Figure 6 text and the abstract; the
    per-country ratios are the compression factors of Table C.5)

Inputs
------
data/ENTSOE_day_ahead_prices.csv, data/GENeSYS_MOD_prices.csv
results/intermediate/compression_factors_2025.csv

Outputs
-------
results/tables/Table_5.csv
results/tables/values_table_5_distribution_metrics.csv
"""

import numpy as np
import pandas as pd
from scipy import stats

from config import (COUNTRIES, ENTSOE_PRICES_FILE, GENESYS_PRICES_FILE,
                    RESULTS_DIR)
from outputs import ValueLog, save_table
from plot_annual_mean_prices import annual_means_entsoe, annual_means_genesys
from plot_price_duration_curves import collect_entsoe_pdcs, collect_genesys_pdcs

YEAR = 2025
DIMS = ["hour", "weekday", "month", "season"]


def distribution_metrics(prices) -> dict:
    p = np.asarray(prices, dtype=float)
    p = p[~np.isnan(p)]
    mean = p.mean()
    return {
        "Mean (EUR/MWh)":                  mean,
        "Standard deviation (EUR/MWh)":    p.std(),
        "Skewness":                        stats.skew(p),
        "Excess kurtosis":                 stats.kurtosis(p),
        "5th percentile (EUR/MWh)":        np.percentile(p, 5),
        "95th percentile (EUR/MWh)":       np.percentile(p, 95),
        "Negative-price hours (%)":        100 * np.mean(p < 0),
        "Extreme-price hours (>3x mean, %)": 100 * np.mean(p > 3 * mean),
    }


def main():
    log = ValueLog("table_5_distribution_metrics")

    entsoe = pd.read_csv(ENTSOE_PRICES_FILE, index_col=0, parse_dates=True)
    genesys = pd.read_csv(GENESYS_PRICES_FILE)

    # ── Table 5 ──────────────────────────────────────────────────────────────
    e25 = entsoe[entsoe.index.year == YEAR]
    g25 = genesys[genesys["year"] == YEAR].groupby("Hour")[COUNTRIES].mean()

    e_metrics = pd.DataFrame({c: distribution_metrics(e25[c]) for c in COUNTRIES}).T
    g_metrics = pd.DataFrame({c: distribution_metrics(g25[c]) for c in COUNTRIES}).T
    table = pd.DataFrame({"ENTSO-E": e_metrics.median(), "GENeSYS-MOD": g_metrics.median()})
    save_table(table.round(2), "Table_5")
    print(table.round(2).to_string())
    for metric, row in table.iterrows():
        log.add("Table 5", f"ENTSO-E {metric}", row["ENTSO-E"])
        log.add("Table 5", f"GENeSYS-MOD {metric}", row["GENeSYS-MOD"])

    # ── Figure 4 text: annual mean prices ────────────────────────────────────
    am_e = annual_means_entsoe(ENTSOE_PRICES_FILE)["mean_price"]
    am_g = annual_means_genesys(GENESYS_PRICES_FILE)["mean_price"]
    log.add("Section 3.1", "ENTSO-E annual mean, minimum (EUR/MWh)", am_e.min())
    log.add("Section 3.1", "ENTSO-E annual mean, maximum (EUR/MWh)", am_e.max())
    log.add("Section 3.1", "GENeSYS-MOD annual mean, 25th percentile (EUR/MWh)", am_g.quantile(0.25))
    log.add("Section 3.1", "GENeSYS-MOD annual mean, 75th percentile (EUR/MWh)", am_g.quantile(0.75))
    print(f"\nAnnual means: ENTSO-E {am_e.min():.0f}-{am_e.max():.0f} EUR/MWh; "
          f"GENeSYS-MOD IQR {am_g.quantile(0.25):.0f}-{am_g.quantile(0.75):.0f} EUR/MWh")

    # ── Figure 5 text: range of the median price duration curve ─────────────
    for label, pdcs in (("ENTSO-E", collect_entsoe_pdcs()), ("GENeSYS-MOD", collect_genesys_pdcs())):
        median_curve = np.median(pdcs, axis=0)
        log.add("Section 3.1", f"{label} median duration curve, minimum (EUR/MWh)", median_curve.min())
        log.add("Section 3.1", f"{label} median duration curve, maximum (EUR/MWh)", median_curve.max())
        print(f"{label} median duration curve: {median_curve.min():.0f} to {median_curve.max():.0f} EUR/MWh")

    # ── Figure 6 text and abstract: 2025 peak-to-trough ratio ───────────────
    cf = pd.read_csv(RESULTS_DIR / "compression_factors_2025.csv")
    for dim in DIMS:
        ratio = cf.loc[cf["dimension"] == dim, "xi"].median()
        for exhibit in ("Section 3.1", "Abstract"):
            log.add(exhibit, f"{dim} 2025 peak-to-trough ratio (ENTSO-E/GENeSYS-MOD)", ratio)
        print(f"2025 peak-to-trough ratio {dim:8s}: {ratio:.1f}")

    log.save()


if __name__ == "__main__":
    main()
