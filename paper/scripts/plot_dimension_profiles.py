"""
plot_stage2_profiles.py

Paper figure: Stage 2 price deviation profiles — ENTSO-E vs. GENeSYS-MOD.

Each of the four calendar dimensions gets one panel:
  Mean deviation from overall mean (€/MWh), ±1 std band across countries.
  ENTSO-E = black solid line / dark fill
  GENeSYS-MOD = red dashed line / red fill  (all scenarios pooled)

Input : results/calendar_effects/stage2_ttest_groups_detail.csv
Output: paper/plots/stage2_profiles.png
"""

import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE  = Path(__file__).parent.parent.parent
INPUT = BASE / "results" / "calendar_effects" / "stage2_ttest_groups_detail.csv"
OUT   = BASE / "paper" / "plots" / "Figure_6.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
DIM_LABELS = {
    "hour":    "Hour-of-Day",
    "weekday": "Day-of-Week",
    "month":   "Month-of-Year",
    "season":  "Season",
}
_WEEKDAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_MONTH   = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_SEASON  = {1: "Winter", 2: "Spring", 3: "Summer", 4: "Autumn"}

ENTSOE_COLOR  = "#2166ac"
GENESYS_COLOR = "#d6604d"
BAND_ALPHA    = 0.12


def _xlabels(dim, groups):
    if dim == "hour":
        return [f"{int(g):02d}:00" if int(g) % 4 == 0 else "" for g in groups]
    elif dim == "weekday":
        return [_WEEKDAY[int(g)] for g in groups]
    elif dim == "month":
        return [_MONTH[int(g) - 1] for g in groups]
    elif dim == "season":
        return [_SEASON.get(int(g), str(g)) for g in groups]
    return [str(g) for g in groups]


# ── Main ───────────────────────────────────────────────────────────────────────

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

    df = pd.read_csv(INPUT)

    fig = plt.figure(figsize=(6.67, 4.0))
    gs  = GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.32)

    dim_layout = [
        ("hour",    0, 0),
        ("weekday", 0, 1),
        ("month",   1, 0),
        ("season",  1, 1),
    ]

    for dim, row, col in dim_layout:
        ax = fig.add_subplot(gs[row, col])

        sub    = df[df["dimension"] == dim]
        groups = sorted(sub["group"].unique())
        xs     = np.arange(len(groups))

        def quantiles(src, col="deviation"):
            grp = src.groupby("group")[col]
            med = grp.median()
            p25 = grp.quantile(0.25)
            p75 = grp.quantile(0.75)
            return (np.array([med.get(g, np.nan) for g in groups]),
                    np.array([p25.get(g, np.nan) for g in groups]),
                    np.array([p75.get(g, np.nan) for g in groups]))

        # ENTSO-E
        entsoe = sub[sub["source"] == "ENTSOE"]
        ey, e25, e75 = quantiles(entsoe)
        ax.fill_between(xs, e25, e75, color=ENTSOE_COLOR, alpha=0.25, zorder=2)
        ax.plot(xs, ey, color=ENTSOE_COLOR, linewidth=2.0, zorder=4)

        # GENeSYS-MOD (pooled)
        genesys = sub[sub["source"] == "GENeSYS-MOD"]
        gy, g25, g75 = quantiles(genesys)
        ax.fill_between(xs, g25, g75, color=GENESYS_COLOR, alpha=0.25, zorder=2)
        ax.plot(xs, gy, color=GENESYS_COLOR, linewidth=2.0, linestyle="--", zorder=3)

        ax.axhline(0, color="#aaaaaa", linewidth=0.7, linestyle=":", zorder=1)

        ax.set_title(DIM_LABELS[dim], fontsize=9, fontweight="bold")
        ax.set_ylabel("Deviation from mean\n(€/MWh)", fontsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", color="#eeeeee", linewidth=0.6, zorder=0)
        ax.set_xticks(xs)
        ax.set_xticklabels(
            _xlabels(dim, groups),
            rotation=45 if dim in ("hour", "month") else 0,
            ha="right" if dim in ("hour", "month") else "center",
        )

    # Legend
    handles = [
        Line2D([0], [0], color=ENTSOE_COLOR,  linewidth=2.0,
               label="ENTSO-E"),
        Line2D([0], [0], color=GENESYS_COLOR, linewidth=2.0, linestyle="--",
               label="GENeSYS-MOD (all scenarios pooled)"),
        mpatches.Patch(color="grey", alpha=0.3, label="IQR across countries"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=9,
               frameon=False, bbox_to_anchor=(0.5, -0.04))

    plt.tight_layout(rect=[0, 0.10, 1, 1])
    fig.savefig(OUT, dpi=300, bbox_inches="tight")
    plt.close(fig)
    matplotlib.rcParams.update(matplotlib.rcParamsDefault)
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
