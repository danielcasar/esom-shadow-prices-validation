"""
compute_value_factors.py — solar and wind value factors quoted in Section 4.2.

Value factor = generation-weighted capture price / time-weighted average price,
computed per country for 2025 and reported as the median across countries.

  ENTSO-E     : observed hourly day-ahead prices weighted by observed hourly
                solar (resp. onshore + offshore wind) generation; hours with a
                missing price or generation value are dropped from the capture
                price; the average price is taken over all 2025 hours.
  GENeSYS-MOD : GoRES 2025 shadow prices weighted by the GoRES 2025 solar
                (PV) resp. wind production of the model. The production output
                covers 72 representative timeslices, which are matched to the
                corresponding hours of the price series; the average price is
                taken over all 8760 hours.

Inputs
------
data/ENTSOE_day_ahead_prices.csv, data/ENTSOE_vre_generation_2025.csv
data/GENeSYS_MOD_prices.csv,      data/GENeSYS_MOD_vre_production_2025.csv
(the two *_vre_* extracts are produced by prepare_vre_generation.py)

Outputs
-------
results/intermediate/value_factors_2025.csv
results/tables/values_compute_value_factors.csv
"""

import numpy as np
import pandas as pd

from config import (COUNTRIES, DATA_DIR, ENTSOE_PRICES_FILE, GENESYS_PRICES_FILE,
                    RESULTS_DIR)
from outputs import ValueLog

YEAR = 2025
SCENARIO = "GoRES"
SCENARIO_PRODUCTION = "Green_CO2_exo_globalLimit"   # GoRES in the production output
CARRIERS = ("solar", "wind")


def value_factor(prices: pd.Series, generation: pd.Series, average_price: float) -> float:
    d = pd.concat([prices, generation], axis=1, keys=["p", "g"]).dropna()
    if d["g"].sum() <= 0:
        return np.nan
    return (d["p"] * d["g"]).sum() / d["g"].sum() / average_price


def main():
    log = ValueLog("compute_value_factors")

    entsoe = pd.read_csv(ENTSOE_PRICES_FILE, index_col=0, parse_dates=True)
    entsoe = entsoe[entsoe.index.year == YEAR]
    gen = pd.read_csv(DATA_DIR / "ENTSOE_vre_generation_2025.csv", index_col=0, parse_dates=True)

    genesys = pd.read_csv(GENESYS_PRICES_FILE)
    genesys = genesys[(genesys["year"] == YEAR) & (genesys["scenario"] == SCENARIO)].set_index("Hour")
    prod = pd.read_csv(DATA_DIR / "GENeSYS_MOD_vre_production_2025.csv")
    prod = prod[prod["PathwayScenario"] == SCENARIO_PRODUCTION]

    rows = []
    for c in COUNTRIES:
        for carrier in CARRIERS:
            col = f"{c}_{carrier}"
            vf_e = (value_factor(entsoe[c], gen[col], entsoe[c].mean())
                    if col in gen.columns else np.nan)
            g_prod = (prod[(prod["Region"] == c) & (prod["carrier"] == carrier)]
                      .set_index("Timeslice")["production"])
            vf_g = value_factor(genesys[c], g_prod, genesys[c].mean()) if len(g_prod) else np.nan
            rows.append({"country": c, "carrier": carrier,
                         "entsoe_value_factor": vf_e, "genesys_value_factor": vf_g})
    vf = pd.DataFrame(rows)
    vf.to_csv(RESULTS_DIR / "value_factors_2025.csv", index=False)

    for carrier in CARRIERS:
        sub = vf[vf["carrier"] == carrier]
        e_med = sub["entsoe_value_factor"].median()
        g_med = sub["genesys_value_factor"].median()
        log.add("Section 4.2", f"ENTSO-E {carrier} value factor (median)", e_med)
        log.add("Section 4.2", f"GENeSYS-MOD {carrier} value factor (median)", g_med)
        log.add("Section 4.2", f"{carrier} capture-price overstatement (%)", 100 * (g_med / e_med - 1))
        print(f"{carrier:5s} value factor: ENTSO-E {e_med:.2f} "
              f"(n={sub['entsoe_value_factor'].notna().sum()}), "
              f"GENeSYS-MOD {g_med:.2f} (n={sub['genesys_value_factor'].notna().sum()})")
    log.save()


if __name__ == "__main__":
    main()
