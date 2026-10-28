"""
figure_07_compression.py — Figure 7: compression ratio by model year and country cluster.

Compression ratio = ENTSO-E range / GENeSYS-MOD range, where a range is the
max - min of group-mean deviations from the annual mean.
  Left panel (by model year): ranges per country and year; GENeSYS-MOD median
      over scenarios and then over countries, ENTSO-E median over countries
      for the same year (ENTSO-E 2025 for model year 2030).
  Right panel (by cluster): per country and scenario, ratio of the ranges
      pooled over all years (deviation_summary.csv); median within cluster.

Input:  results/intermediate/stage2_ttest_groups_detail.csv
        results/intermediate/deviation_summary.csv
Output: results/figures/Figure_7.pdf
"""

import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import SCENARIOS, GENESYS_YEARS
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# ── Paths ────────────────────────────────────────────────────────────────────
BASE     = Path(__file__).parent.parent
DET_FILE = BASE / "results" / "intermediate" / "stage2_ttest_groups_detail.csv"
DEV_FILE = BASE / "results" / "intermediate" / "deviation_summary.csv"
OUT      = BASE / "results" / "figures" / "Figure_7.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────

DIMS = ["hour", "weekday", "month", "season"]
DIM_LABELS = {
    "hour":    "Hour-of-Day",
    "weekday": "Day-of-Week",
    "month":   "Month-of-Year",
    "season":  "Season",
}

CLUSTERS = {
    "Iberian":    ["ES", "PT"],
    "Baltic":     ["EE", "LT", "LV"],
    "South-East": ["BG", "HR", "HU", "SI"],
    "Core-East":  ["AT", "CZ", "DE", "SK"],
    "Core-West":  ["BE", "CH", "FR", "NL"],
    "FI": ["FI"], "GR": ["GR"], "RO": ["RO"], "IE": ["IE"], "PL": ["PL"],
}
CLUSTER_ORDER = [
    "Iberian", "Baltic", "South-East", "Core-East", "Core-West",
    "FI", "GR", "RO", "IE", "PL",
]
CTC = {c: name for name, ms in CLUSTERS.items() for c in ms}

DIM_COLORS = {
    "hour":    "#1f77b4",
    "weekday": "#ff7f0e",
    "month":   "#2ca02c",
    "season":  "#d62728",
}
DIM_MARKERS = {
    "hour":    "o",
    "weekday": "s",
    "month":   "^",
    "season":  "D",
}


def main():
    matplotlib.rcParams.update({
        "font.family":     "sans-serif",
        "font.sans-serif": ["Arial"],
        "font.size":       9,
        "axes.labelsize":  9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.linewidth":  0.8,
    })

    # ── Load data ─────────────────────────────────────────────────────────────
    det = pd.read_csv(DET_FILE)
    dev = pd.read_csv(DEV_FILE)

    dev = dev[dev["model_scenario"].isin(SCENARIOS)].copy()

    # ── Plot 1 data: compression by GENeSYS year ──────────────────────────────
    # GENeSYS range per (year, dimension, country) = max−min of group deviations,
    # then median across scenarios and countries.
    genesys = det[
        (det["source"] != "ENTSOE") & det["scenario"].isin(SCENARIOS)
    ].copy()

    g_ranges = (
        genesys.groupby(["year", "dimension", "country", "scenario"])["deviation"]
        .agg(lambda x: x.max() - x.min())
        .reset_index(name="g_range")
    )
    # Median across scenarios first, then across countries
    g_by_year = (
        g_ranges.groupby(["year", "dimension", "country"])["g_range"]
        .median()
        .reset_index()
        .groupby(["year", "dimension"])["g_range"]
        .median()
    )

    # ENTSO-E range per (year, dimension, country) = max−min of group deviations,
    # then median across countries.  For 2030 (no ENTSO-E), use 2025 as reference.
    entsoe = det[det["source"] == "ENTSOE"].copy()
    e_ranges = (
        entsoe.groupby(["year", "dimension", "country"])["deviation"]
        .agg(lambda x: x.max() - x.min())
        .reset_index(name="e_range")
    )
    e_by_year = (
        e_ranges.groupby(["year", "dimension"])["e_range"]
        .median()
    )
    # Map each GENeSYS year to the ENTSO-E reference year
    ENTSOE_REF_YEAR = {2018: 2018, 2025: 2025, 2030: 2025}

    # compression per (year, dim) = entsoe_year_range / genesys_range
    year_comp = {}
    for dim in DIMS:
        year_comp[dim] = []
        for yr in GENESYS_YEARS:
            eyr = ENTSOE_REF_YEAR[yr]
            if (yr, dim) in g_by_year.index and (eyr, dim) in e_by_year.index:
                g_rng = g_by_year.loc[(yr, dim)]
                e_rng = e_by_year.loc[(eyr, dim)]
                year_comp[dim].append(e_rng / g_rng if g_rng > 0 else np.nan)
            else:
                year_comp[dim].append(np.nan)

    # ── Plot 2 data: compression by cluster ───────────────────────────────────
    dev["cluster"] = dev["country"].map(CTC)
    dev["compression"] = dev["entsoe_range"] / dev["model_range"]
    dev_cl = dev[dev["cluster"].notna()]

    clust_comp = (
        dev_cl.groupby(["cluster", "dimension"])["compression"]
        .median()
        .unstack()
    )

    # ── Figure ────────────────────────────────────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.67, 3.2),
                                    gridspec_kw={"wspace": 0.45})

    # ── Left panel: by year ───────────────────────────────────────────────────
    xs_yr = np.arange(len(GENESYS_YEARS))
    for dim in DIMS:
        vals = year_comp[dim]
        ax1.plot(xs_yr, vals,
                 color=DIM_COLORS[dim], marker=DIM_MARKERS[dim],
                 markersize=5, linewidth=1.5, label=DIM_LABELS[dim])

    ax1.axhline(1, color="#aaaaaa", linewidth=0.8, linestyle="--", zorder=0)
    ax1.set_xticks(xs_yr)
    ax1.set_xticklabels([str(y) for y in GENESYS_YEARS])
    ax1.set_ylabel(r"Compression ratio $\xi$", fontsize=9)
    ax1.set_xlabel("GENeSYS-MOD modelling year", fontsize=9)
    ax1.set_ylim(bottom=0)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.grid(axis="y", color="#eeeeee", linewidth=0.6, zorder=0)
    ax1.tick_params(axis="both", labelsize=9)

    # ── Right panel: by cluster ───────────────────────────────────────────────
    xs_cl = np.arange(len(CLUSTER_ORDER))
    sep   = 4.5  # separator between multi-country and singleton clusters

    for dim in DIMS:
        vals = [clust_comp.loc[cl, dim] if cl in clust_comp.index else np.nan
                for cl in CLUSTER_ORDER]
        ax2.plot(xs_cl, vals,
                 color=DIM_COLORS[dim], marker=DIM_MARKERS[dim],
                 markersize=5, linewidth=1.5, label=DIM_LABELS[dim])

    ax2.axhline(1, color="#aaaaaa", linewidth=0.8, linestyle="--", zorder=0)
    ax2.axvline(sep, color="#aaaaaa", linewidth=0.7, linestyle=":", zorder=1)
    ax2.set_xticks(xs_cl)
    ax2.set_xticklabels(CLUSTER_ORDER, rotation=90, ha="center")
    ax2.set_ylabel(r"Compression ratio $\xi$", fontsize=9)
    ax2.set_xlabel("", fontsize=9)
    ax2.set_xlim(-0.5, len(CLUSTER_ORDER) - 0.5)
    ax2.set_ylim(bottom=0)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.grid(axis="y", color="#eeeeee", linewidth=0.6, zorder=0)
    ax2.tick_params(axis="both", labelsize=9)

    # ── Shared legend ─────────────────────────────────────────────────────────
    handles = [
        Line2D([0], [0], color=DIM_COLORS[d], marker=DIM_MARKERS[d],
               markersize=5, linewidth=1.5, label=DIM_LABELS[d])
        for d in DIMS
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=9,
               frameon=False, bbox_to_anchor=(0.5, -0.22))

    plt.tight_layout(rect=[0, 0.16, 1, 1])
    fig.savefig(OUT, dpi=300, bbox_inches="tight")
    plt.close(fig)
    matplotlib.rcParams.update(matplotlib.rcParamsDefault)
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
