"""
plot_stage3_genesys_cross_year.py

Cross-year GENeSYS-MOD Pearson ρ heatmap — companion to Fig 10.

For each scenario: a 2-panel figure with dual-triangle 3×3 heatmaps,
matching the style of plot_stage3_entsoe_cross_year.py.
  Left panel : upper triangle = Hour-of-Day, lower = Day-of-Week
  Right panel: upper triangle = Month-of-Year, lower = Season

ρ for each cell = mean over COUNTRIES of Pearson ρ between the
group-mean price profiles of year1 vs year2.
Diagonal = 1 (same year).

Output: results/figures/Figure_C4.pdf
        (one file per scenario)
"""

import warnings
warnings.filterwarnings("ignore")

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from scipy.stats import pearsonr

sys.path.insert(0, str(Path(__file__).parent))
from config import COUNTRIES, GENESYS_YEARS, SCENARIOS

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE         = Path(__file__).parent.parent
GENESYS_FILE = BASE / "data" / "GENeSYS_MOD_prices.csv"
OUT_DIR      = BASE / "results" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = GENESYS_YEARS   # [2018, 2025, 2030]

MONTH_TO_SEASON = {
    12: 1,  1: 1,  2: 1,
     3: 2,  4: 2,  5: 2,
     6: 3,  7: 3,  8: 3,
     9: 4, 10: 4, 11: 4,
}

DIM_LABELS = {
    "hour"   : "Hour-of-Day",
    "weekday": "Day-of-Week",
    "month"  : "Month-of-Year",
    "season" : "Season",
}

PANELS = [
    ("hour",  "weekday", "Hour-of-Day (upper) / Day-of-Week (lower)"),
    ("month", "season",  "Month-of-Year (upper) / Season (lower)"),
]

matplotlib.rcParams.update({
    "font.family":     "sans-serif",
    "font.sans-serif": ["Arial"],
    "font.size":       9,
    "axes.labelsize":  9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.linewidth":  0.8,
})


# ── Calendar mapping ───────────────────────────────────────────────────────────

def build_time_map(year: int) -> pd.DataFrame:
    idx = pd.date_range(start=f"{year}-01-01", periods=8760, freq="h")
    tm = pd.DataFrame({
        "Hour"   : range(1, 8761),
        "hour"   : idx.hour,
        "weekday": idx.weekday,
        "month"  : idx.month,
    })
    tm["season"] = tm["month"].map(MONTH_TO_SEASON)
    return tm


# ── Pearson ρ computation ──────────────────────────────────────────────────────

def compute_cross_year_matrix(df_raw: pd.DataFrame, scenario: str) -> dict:
    """
    Returns {dimension: 3×3 matrix} for a given scenario.
    Diagonal = 1.0; off-diagonal = mean Pearson ρ over COUNTRIES.
    """
    available = [c for c in COUNTRIES if c in df_raw.columns]
    n = len(YEARS)

    # Pre-compute group-mean profiles: profiles[dim][year] = {country: array}
    profiles: dict = {dim: {} for dim in DIM_LABELS}

    for year in YEARS:
        tm = build_time_map(year)
        sub = df_raw[(df_raw["year"] == year) & (df_raw["scenario"] == scenario)].copy()
        if sub.empty:
            continue
        sub = sub.merge(tm, on="Hour", how="left")
        for dim in DIM_LABELS:
            profiles[dim][year] = {
                c: sub.groupby(dim)[c].mean().values
                for c in available
            }

    matrices = {}
    for dim in DIM_LABELS:
        mat = np.full((n, n), np.nan)
        # diagonal left as NaN -> rendered grey via cmap.set_bad

        for i, y1 in enumerate(YEARS):
            for j, y2 in enumerate(YEARS):
                if i == j:
                    continue
                if y1 not in profiles[dim] or y2 not in profiles[dim]:
                    continue
                rhos = []
                for c in available:
                    v1 = profiles[dim][y1].get(c)
                    v2 = profiles[dim][y2].get(c)
                    if v1 is None or v2 is None:
                        continue
                    if np.std(v1) < 1e-10 or np.std(v2) < 1e-10:
                        continue
                    rho, _ = pearsonr(v1, v2)
                    if not np.isnan(rho):
                        rhos.append(rho)
                if rhos:
                    mat[i, j] = float(np.mean(rhos))

        matrices[dim] = mat

    return matrices


# ── Combined matrix (dual-triangle) ───────────────────────────────────────────

def build_combined_matrix(matrices: dict, dim_upper: str, dim_lower: str) -> np.ndarray:
    """
    3×3 combined matrix:
      diagonal       : 1.0
      upper triangle : dim_upper
      lower triangle : dim_lower
    """
    n = len(YEARS)
    mat = np.full((n, n), np.nan)
    # diagonal left as NaN -> rendered grey via cmap.set_bad

    for dim, triangle in [(dim_upper, "upper"), (dim_lower, "lower")]:
        src = matrices[dim]
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                val = src[i, j]
                if np.isnan(val):
                    continue
                if triangle == "upper" and j > i:
                    mat[i, j] = val
                elif triangle == "lower" and j < i:
                    mat[i, j] = val

    return mat


# ── Pooled matrices (average over all scenarios) ──────────────────────────────

def compute_pooled_matrices(df_raw: pd.DataFrame) -> dict:
    """Average cross-year matrices over all scenarios."""
    all_matrices = [compute_cross_year_matrix(df_raw, s) for s in SCENARIOS]
    pooled = {}
    for dim in DIM_LABELS:
        stack = np.array([m[dim] for m in all_matrices])
        pooled[dim] = np.nanmean(stack, axis=0)
        # diagonal left as NaN -> rendered grey via cmap.set_bad
    return pooled


# ── Plot ───────────────────────────────────────────────────────────────────────

def make_figure(scenario: str, matrices: dict):
    n = len(YEARS)
    cmap = plt.get_cmap("RdYlGn").copy()
    cmap.set_bad("lightgrey")

    fig, axes = plt.subplots(1, 2, figsize=(6.67, 3))
    fig.subplots_adjust(left=0.23, right=0.95, top=0.88, bottom=0.13,
                        wspace=0.40)
    if scenario != "pooled":
        fig.suptitle(f"GENeSYS-MOD cross-year Pearson $\\rho$ — {scenario}",
                     fontsize=9, fontweight="bold")

    im = None
    for ax, (dim_upper, dim_lower, _) in zip(axes, PANELS):
        mat = build_combined_matrix(matrices, dim_upper, dim_lower)

        im = ax.imshow(mat, vmin=-1, vmax=1, cmap=cmap, aspect="equal")

        # cell annotations
        for i in range(n):
            for j in range(n):
                val = mat[i, j]
                if np.isnan(val):
                    continue
                txt_col = "black" if abs(val) < 0.75 else "white"
                ax.text(j, i, f"{val:.2f}",
                        ha="center", va="center",
                        fontsize=9, color=txt_col, fontweight="bold")

        # diagonal separator line
        ax.plot([-0.5, n - 0.5], [-0.5, n - 0.5],
                color="black", linewidth=1.2, zorder=5)

        # axes
        is_right = ax is axes[1]
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(YEARS, rotation=35, ha="right")
        ax.set_yticklabels(YEARS)
        ax.tick_params(top=True, bottom=True, left=True, right=True,
                       labeltop=True, labelbottom=True,
                       labelleft=not is_right, labelright=is_right,
                       labelsize=10)
        ax.xaxis.set_tick_params(which="both", rotation=35, labelsize=10)
        for tick in ax.xaxis.get_major_ticks():
            tick.label2.set_ha("left")
            tick.label2.set_va("bottom")

        ax.set_title(DIM_LABELS[dim_upper], fontsize=9, fontweight="bold", pad=8)
        ax.set_xlabel(DIM_LABELS[dim_lower], fontsize=9, fontweight="bold", labelpad=8)
        ax.set_ylabel("")

    # shared colorbar on the far left + in-between y-axis labels
    fig.canvas.draw()
    pos0 = axes[0].get_position()
    pos1 = axes[1].get_position()
    mid_x = (pos0.x1 + pos1.x0) / 2
    for i, yr in enumerate(YEARS):
        _, y_disp = axes[0].transData.transform((0, i))
        _, y_fig  = fig.transFigure.inverted().transform((0, y_disp))
        fig.text(mid_x, y_fig, str(yr), ha="center", va="center", fontsize=9)
    pos = axes[0].get_position()
    cax = fig.add_axes([0.02, pos.y0, 0.015, pos.height])
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_ticks([-1, -0.5, 0, 0.5, 1])
    cbar.ax.tick_params(labelsize=10)
    cbar.ax.yaxis.set_ticks_position("left")
    cbar.ax.yaxis.set_label_position("left")
    cbar.set_label(r"Pearson $\rho$")

    out_path = OUT_DIR / ("Figure_C4.pdf" if scenario == "pooled"
                          else f"stage3_genesys_cross_year_{scenario.replace('+','plus').replace(' ','_')}.pdf")
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading GENeSYS-MOD data …")
    df_raw = pd.read_csv(GENESYS_FILE)
    df_raw = df_raw[df_raw["year"].isin(YEARS)]

    print("Computing pooled cross-year matrices (all scenarios) …")
    pooled = compute_pooled_matrices(df_raw)
    make_figure("pooled", pooled)

    matplotlib.rcParams.update(matplotlib.rcParamsDefault)
    print("\nDone.")
