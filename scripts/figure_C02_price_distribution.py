"""
figure_C02_price_distribution.py — Figure C.2: pooled hourly price distributions, 2025.

Pooled hourly price distributions for the 2025 comparison year across the 22
countries: ENTSO-E observed prices and GENeSYS-MOD shadow prices (averaged
across the four scenarios hour by hour, as in Table 5). Values outside the
plotted range [-50, 560] EUR/MWh are clipped into the edge bins.

Inputs : data/ENTSOE_day_ahead_prices.csv, data/GENeSYS_MOD_prices.csv
Output : results/figures/Figure_C2.pdf
         results/tables/values_figure_C02.csv
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import COUNTRIES, ENTSOE_PRICES_FILE, GENESYS_PRICES_FILE, PLOTS_DIR
from helpers import ValueLog

YEAR = 2025
LO, HI = -50, 560
ENTSOE_COLOR = "#1a6faf"
GENESYS_COLOR = "#b2182b"


def main():
    log = ValueLog("figure_C02")
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial"],
        "font.size": 9, "axes.labelsize": 9, "xtick.labelsize": 9,
        "ytick.labelsize": 9, "legend.fontsize": 9, "axes.linewidth": 0.6,
    })

    entsoe = pd.read_csv(ENTSOE_PRICES_FILE, index_col=0, parse_dates=True)
    entsoe = entsoe[entsoe.index.year == YEAR]
    e_vals = np.concatenate([entsoe[c].dropna().values for c in COUNTRIES])

    genesys = pd.read_csv(GENESYS_PRICES_FILE)
    genesys = genesys[genesys["year"] == YEAR].groupby("Hour")[COUNTRIES].mean()
    g_vals = np.concatenate([genesys[c].values for c in COUNTRIES])

    bins = np.linspace(LO, HI, 91)
    fig, ax = plt.subplots(figsize=(6.67, 4.4))
    ax.hist(np.clip(e_vals, LO, HI), bins=bins, density=True, color=ENTSOE_COLOR,
            alpha=0.55, label="ENTSO-E (observed)")
    ax.hist(np.clip(g_vals, LO, HI), bins=bins, density=True, color=GENESYS_COLOR,
            alpha=0.55, label="GENeSYS-MOD (shadow prices)")
    ax.axvline(0, color="grey", lw=0.6, ls="--")
    ax.set_xlabel("Hourly price (€/MWh)")
    ax.set_ylabel("Density")
    ax.set_xlim(LO, HI)
    ax.legend(frameon=False, loc="upper right")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    out = PLOTS_DIR / "Figure_C2.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")

    outside = 100 * np.mean((e_vals < LO) | (e_vals > HI))
    log.add("Figure C.2", "ENTSO-E hours outside plotted range (%)", outside)
    print(f"ENTSO-E hours outside [{LO}, {HI}]: {outside:.2f}%")
    log.save()


if __name__ == "__main__":
    main()
