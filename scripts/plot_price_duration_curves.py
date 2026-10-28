"""
plot_price_duration_curve.py

Paper figure: Price duration curves — ENTSO-E vs. GENeSYS-MOD.
  - For each source: min/max band, IQR band, median line.
  - ENTSO-E series:  country × year  (20 countries × 8 years)
  - GENeSYS series:  country × scenario × year  (20 × 4 × 3)

Output: results/figures/Figure_5.pdf
"""

import warnings
warnings.filterwarnings("ignore")

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.path.insert(0, str(Path(__file__).parent))
from config import COUNTRIES, SCENARIOS, ENTSOE_YEARS, GENESYS_YEARS

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE         = Path(__file__).parent.parent
ENTSOE_FILE  = BASE / "data" / "ENTSOE_day_ahead_prices.csv"
GENESYS_FILE = BASE / "data" / "GENeSYS_MOD_prices.csv"
OUT_DIR      = BASE / "results" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
N_POINTS       = 500
PERCENTILE_GRID = np.linspace(0, 100, N_POINTS)
COLOR_E        = "#2166ac"   # blue  – ENTSO-E
COLOR_G        = "#d6604d"   # red   – GENeSYS-MOD
MIN_HOURS      = 100


# ── PDC helpers ────────────────────────────────────────────────────────────────

def compute_pdc(prices):
    """Interpolate a sorted-descending price series onto the common grid."""
    prices = np.asarray(prices, dtype=float)
    prices = prices[~np.isnan(prices)]
    if len(prices) < MIN_HOURS:
        return None
    sorted_p = np.sort(prices)[::-1]
    raw_pct  = np.linspace(0, 100, len(sorted_p))
    return np.interp(PERCENTILE_GRID, raw_pct, sorted_p)


def collect_entsoe_pdcs():
    print("Loading ENTSO-E data …")
    df = pd.read_csv(ENTSOE_FILE, index_col=0, parse_dates=True)
    cols = [c for c in COUNTRIES if c in df.columns]
    df = df[cols]
    pdcs = []
    for country in cols:
        for year in ENTSOE_YEARS:
            pdc = compute_pdc(df.loc[df.index.year == year, country].values)
            if pdc is not None:
                pdcs.append(pdc)
    print(f"  {len(pdcs)} ENTSO-E series (country × year)")
    return np.array(pdcs)


def collect_genesys_pdcs():
    print("Loading GENeSYS-MOD data …")
    df = pd.read_csv(GENESYS_FILE)
    pdcs = []
    for scenario in SCENARIOS:
        s = df[df["scenario"] == scenario]
        for year in GENESYS_YEARS:
            sy = s[s["year"] == year]
            if sy.empty:
                continue
            for country in COUNTRIES:
                if country not in sy.columns:
                    continue
                pdc = compute_pdc(sy[country].values)
                if pdc is not None:
                    pdcs.append(pdc)
    print(f"  {len(pdcs)} GENeSYS-MOD series (country × scenario × year)")
    return np.array(pdcs)


# ── Plot ───────────────────────────────────────────────────────────────────────

def make_pdc_figure(entsoe_pdcs, genesys_pdcs):
    matplotlib.rcParams.update({
        "font.family":     "sans-serif",
        "font.sans-serif": ["Arial"],
        "font.size":       9,
        "axes.labelsize":  9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.linewidth":  0.8,
    })

    x = PERCENTILE_GRID

    def stats(arr):
        return (np.percentile(arr, 25, axis=0),
                np.median(arr, axis=0),
                np.percentile(arr, 75, axis=0))

    e_p25, e_med, e_p75 = stats(entsoe_pdcs)
    g_p25, g_med, g_p75 = stats(genesys_pdcs)

    fig, ax = plt.subplots(figsize=(4.5, 2.5))

    # ENTSO-E
    ax.fill_between(x, e_p25, e_p75, color=COLOR_E, alpha=0.30, zorder=2)
    ax.plot(x, e_med, color=COLOR_E, linewidth=2.0, zorder=5)

    # GENeSYS-MOD
    ax.fill_between(x, g_p25, g_p75, color=COLOR_G, alpha=0.30, zorder=2)
    ax.plot(x, g_med, color=COLOR_G, linewidth=2.0, zorder=5)

    # Zero line
    ax.axhline(0, color="black", linewidth=0.7, linestyle=":", zorder=3)

    # Axes
    ax.set_xlabel("Share of hours (%)")
    ax.set_ylabel("Price (€/MWh)")
    ax.set_xlim(0, 100)
    ax.set_ylim(-100, 500)
    ax.grid(True, alpha=0.25, linestyle="--", linewidth=0.5)

    # Legend — two source entries; visual elements described in caption
    legend_handles = [
        mpatches.Patch(facecolor=COLOR_E, alpha=0.7, label="ENTSO-E"),
        mpatches.Patch(facecolor=COLOR_G, alpha=0.7, label="GENeSYS-MOD"),
    ]
    ax.legend(handles=legend_handles, fontsize=9, framealpha=0.85)

    plt.tight_layout()
    out_path = OUT_DIR / "Figure_5.pdf"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    matplotlib.rcParams.update(matplotlib.rcParamsDefault)
    print(f"Saved: {out_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    entsoe_pdcs  = collect_entsoe_pdcs()
    genesys_pdcs = collect_genesys_pdcs()
    print("Generating figure …")
    make_pdc_figure(entsoe_pdcs, genesys_pdcs)
    print("Done.")
