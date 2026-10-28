"""
figure_C03_scenario_correlations.py — Figure C.3: cross-scenario correlations of GENeSYS-MOD price patterns.

Cross-scenario GENeSYS-MOD Pearson rho heatmaps.

For each temporal dimension: one 4x4 symmetric matrix where
  rows/cols = scenarios (GoRES, NECPEssentials, REPowerEU++, Trinity)
  value     = mean Pearson rho averaged over COUNTRIES x YEARS (2018, 2025, 2030)
  diagonal  = 1 (same scenario)

Output: results/figures/Figure_C3.pdf
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

SCENARIO_LABELS = [
    "GoRES",
    "NECP",
    "REPower++",
    "Trinity",
]

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


# ── Profile computation ────────────────────────────────────────────────────────

def build_profiles(df_raw: pd.DataFrame, available: list) -> dict:
    """
    profiles[dim][scenario][year] = {country: group-mean array}
    """
    profiles = {dim: {s: {} for s in SCENARIOS} for dim in DIM_LABELS}

    for year in YEARS:
        tm = build_time_map(year)
        for scenario in SCENARIOS:
            sub = df_raw[
                (df_raw["year"] == year) & (df_raw["scenario"] == scenario)
            ].copy()
            if sub.empty:
                continue
            sub = sub.merge(tm, on="Hour", how="left")
            for dim in DIM_LABELS:
                profiles[dim][scenario][year] = {
                    c: sub.groupby(dim)[c].mean().values
                    for c in available
                }

    return profiles


# ── Cross-scenario matrix ──────────────────────────────────────────────────────

def compute_cross_scenario_matrix(profiles: dict, dim: str, available: list) -> np.ndarray:
    """
    4x4 symmetric matrix: mean Pearson rho between scenario pairs,
    averaged over countries x years.
    """
    n = len(SCENARIOS)
    mat = np.full((n, n), np.nan)
    # diagonal left as NaN -> rendered grey via cmap.set_bad

    for i, s1 in enumerate(SCENARIOS):
        for j, s2 in enumerate(SCENARIOS):
            if i == j:
                continue
            rhos = []
            for year in YEARS:
                if year not in profiles[dim][s1] or year not in profiles[dim][s2]:
                    continue
                for c in available:
                    v1 = profiles[dim][s1][year].get(c)
                    v2 = profiles[dim][s2][year].get(c)
                    if v1 is None or v2 is None:
                        continue
                    if np.std(v1) < 1e-10 or np.std(v2) < 1e-10:
                        continue
                    rho, _ = pearsonr(v1, v2)
                    if not np.isnan(rho):
                        rhos.append(rho)
            if rhos:
                mat[i, j] = float(np.mean(rhos))

    return mat


# ── Combined matrix (dual-triangle) ───────────────────────────────────────────

def build_combined_matrix(profiles: dict, dim_upper: str, dim_lower: str,
                          available: list) -> np.ndarray:
    """
    4×4 combined matrix:
      diagonal       : 1.0
      upper triangle : dim_upper
      lower triangle : dim_lower
    """
    n = len(SCENARIOS)
    mat = np.full((n, n), np.nan)
    # diagonal left as NaN -> rendered grey via cmap.set_bad

    for dim, triangle in [(dim_upper, "upper"), (dim_lower, "lower")]:
        src = compute_cross_scenario_matrix(profiles, dim, available)
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


# ── Plot ───────────────────────────────────────────────────────────────────────

def make_figure(profiles: dict, available: list):
    cmap = plt.get_cmap("RdYlGn").copy()
    cmap.set_bad("lightgrey")

    n = len(SCENARIOS)

    fig, axes = plt.subplots(1, 2, figsize=(6.67, 3.5))
    fig.subplots_adjust(left=0.23, right=0.95, top=0.88, bottom=0.15,
                        wspace=0.65)

    im = None
    for ax, (dim_upper, dim_lower, _) in zip(axes, PANELS):
        mat = build_combined_matrix(profiles, dim_upper, dim_lower, available)

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
        ax.set_xticklabels(SCENARIO_LABELS, rotation=35, ha="right")
        ax.set_yticklabels(SCENARIO_LABELS)
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
    for i, lbl in enumerate(SCENARIO_LABELS):
        _, y_disp = axes[0].transData.transform((0, i))
        _, y_fig  = fig.transFigure.inverted().transform((0, y_disp))
        fig.text(mid_x, y_fig, lbl, ha="center", va="center", fontsize=9)
    pos = axes[0].get_position()
    cax = fig.add_axes([0.02, pos.y0, 0.015, pos.height])
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_ticks([-1, -0.5, 0, 0.5, 1])
    cbar.ax.tick_params(labelsize=10)
    cbar.ax.yaxis.set_ticks_position("left")
    cbar.ax.yaxis.set_label_position("left")
    cbar.set_label(r"Pearson $\rho$")

    out_path = OUT_DIR / "Figure_C3.pdf"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading GENeSYS-MOD data ...")
    df_raw = pd.read_csv(GENESYS_FILE)
    df_raw = df_raw[df_raw["year"].isin(YEARS)]

    available = [c for c in COUNTRIES if c in df_raw.columns]
    print(f"  {len(available)} countries available")

    print("Computing group-mean profiles ...")
    profiles = build_profiles(df_raw, available)

    print("Generating figure ...")
    make_figure(profiles, available)

    matplotlib.rcParams.update(matplotlib.rcParamsDefault)
    print("Done.")
