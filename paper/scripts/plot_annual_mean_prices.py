"""
analysis_yearly_average.py

Paper figure: Annual mean electricity prices.
  - ENTSO-E  : one box per year, distribution over countries (2018–2025)
  - GENeSYS-MOD: one box per snapshot year, distribution over countries × scenarios (2018, 2025, 2030)
  Side-by-side boxes at years shared by both sources (2018, 2025).
  X-axis break between 2025 and 2030 to avoid the visual gap.

Output: Code/paper/plots/Figure_4.png
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
from matplotlib.gridspec import GridSpec

sys.path.insert(0, str(Path(__file__).parent))
from config import COUNTRIES, ANALYSIS_YEARS, SCENARIOS

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE         = Path(__file__).parent.parent.parent
ENTSOE_FILE  = BASE / "data" / "ENTSOE_day_ahead_prices.csv"
GENESYS_FILE = BASE / "data" / "GENeSYS_MOD_prices.csv"
OUT_DIR      = BASE / "paper" / "plots"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MIN_HOURS  = 7500
BREAK_YEAR = 2025   # axis break between BREAK_YEAR and the next model year

# ── Colours ────────────────────────────────────────────────────────────────────
COLOR_E = "#2166ac"
COLOR_G = "#d6604d"


# ── Data loading ───────────────────────────────────────────────────────────────

def annual_means_entsoe(path):
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    if ANALYSIS_YEARS:
        df = df[df.index.year.isin(ANALYSIS_YEARS)]
    rows = []
    for country in COUNTRIES:
        if country not in df.columns:
            continue
        for year, grp in df[country].dropna().groupby(df.index.year):
            if len(grp) >= MIN_HOURS:
                rows.append({"country": country, "year": int(year),
                             "mean_price": grp.mean()})
    return pd.DataFrame(rows)


def annual_means_genesys(path):
    df = pd.read_csv(path)
    if ANALYSIS_YEARS:
        df = df[df["year"].isin(ANALYSIS_YEARS)]
    rows = []
    for scenario in SCENARIOS:
        s = df[df["scenario"] == scenario]
        if s.empty:
            continue
        for country in COUNTRIES:
            if country not in s.columns:
                continue
            for year, grp in s.groupby("year")[country]:
                vals = grp.dropna()
                if len(vals) >= MIN_HOURS:
                    rows.append({"country": country, "scenario": scenario,
                                 "year": int(year), "mean_price": vals.mean()})
    return pd.DataFrame(rows)


# ── Plot ───────────────────────────────────────────────────────────────────────

def make_boxplot_figure(df_e, df_g):
    matplotlib.rcParams.update({
        "font.family":     "sans-serif",
        "font.sans-serif": ["Arial"],
        "font.size":       8,
        "axes.labelsize":  8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "axes.linewidth":  0.8,
    })

    e_years = sorted(df_e["year"].unique()) if not df_e.empty else []
    g_years = sorted(df_g["year"].unique()) if not df_g.empty else []
    shared  = sorted(set(e_years) & set(g_years))
    offset  = 0.25
    width   = 0.40

    # Split into left (≤ BREAK_YEAR) and right (> BREAK_YEAR)
    e_left  = [y for y in e_years if y <= BREAK_YEAR]
    g_left  = [y for y in g_years if y <= BREAK_YEAR]
    g_right = [y for y in g_years if y >  BREAK_YEAR]
    all_left  = sorted(set(e_left)  | set(g_left))
    all_right = sorted(g_right)

    def box_style(color, alpha=0.55):
        return dict(
            patch_artist=True,
            manage_ticks=False,
            widths=width,
            boxprops=dict(facecolor=color, color=color, alpha=alpha, linewidth=0.9),
            medianprops=dict(color="black", linewidth=1.5),
            whiskerprops=dict(color=color, linewidth=0.9),
            capprops=dict(color=color, linewidth=0.9),
            flierprops=dict(marker=".", color=color, markersize=3, alpha=0.5),
        )

    # Width ratios: left panel spans len(all_left) years, right panel spans len(all_right)*2
    n_left  = max(len(all_left), 1)
    n_right = max(len(all_right) * 2, 2)

    fig = plt.figure(figsize=(6.67, 3.5))
    gs  = GridSpec(1, 2, figure=fig,
                   width_ratios=[n_left, n_right],
                   wspace=0.06)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharey=ax1)

    # ── Left panel ────────────────────────────────────────────────────────────
    for yr in e_left:
        vals = df_e.loc[df_e["year"] == yr, "mean_price"].values
        pos  = yr - offset if yr in shared else yr
        ax1.boxplot([vals], positions=[pos], **box_style(COLOR_E))

    for yr in g_left:
        vals = df_g.loc[df_g["year"] == yr, "mean_price"].values
        pos  = yr + offset if yr in shared else yr
        ax1.boxplot([vals], positions=[pos], **box_style(COLOR_G))

    ax1.set_xticks(all_left)
    ax1.set_xticklabels(all_left, fontsize=8)
    ax1.set_xlim(min(all_left) - 0.8, max(all_left) + 0.8)
    ax1.set_ylim(bottom=0)
    ax1.set_xlabel("Year", fontsize=8)
    ax1.set_ylabel("Price (€/MWh)", fontsize=8)
    ax1.grid(True, axis="y", alpha=0.25, linewidth=0.5)
    ax1.spines["right"].set_visible(False)

    # ── Right panel ───────────────────────────────────────────────────────────
    for yr in g_right:
        vals = df_g.loc[df_g["year"] == yr, "mean_price"].values
        ax2.boxplot([vals], positions=[yr], **box_style(COLOR_G))

    ax2.set_xticks(all_right)
    ax2.set_xticklabels(all_right, fontsize=8)
    ax2.set_xlim(min(all_right) - 0.8, max(all_right) + 0.8)
    ax2.tick_params(left=False, labelleft=False)
    ax2.grid(True, axis="y", alpha=0.25, linewidth=0.5)
    ax2.spines["left"].set_visible(False)

    # ── Diagonal break marks on inner edges ──────────────────────────────────
    d  = 0.04
    kw = dict(color="k", clip_on=False, linewidth=0.9, transform=ax1.transAxes)
    ax1.plot([1 - d, 1 + d], [-d,  +d], **kw)
    ax1.plot([1 - d, 1 + d], [1 - d, 1 + d], **kw)
    kw["transform"] = ax2.transAxes
    ax2.plot([-d, +d], [-d,  +d], **kw)
    ax2.plot([-d, +d], [1 - d, 1 + d], **kw)

    # ── Legend ────────────────────────────────────────────────────────────────
    legend_handles = [
        mpatches.Patch(facecolor=COLOR_E, alpha=0.7, label="ENTSO-E"),
        mpatches.Patch(facecolor=COLOR_G, alpha=0.7, label="GENeSYS-MOD"),
    ]
    ax1.legend(handles=legend_handles, fontsize=8, framealpha=0.85)

    plt.tight_layout()
    out_path = OUT_DIR / "Figure_4.pdf"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    matplotlib.rcParams.update(matplotlib.rcParamsDefault)
    print(f"Saved: {out_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading ENTSO-E data …")
    df_e = annual_means_entsoe(ENTSOE_FILE)
    print(f"  {len(df_e)} country-year observations, years: {sorted(df_e['year'].unique())}")

    print("Loading GENeSYS-MOD data …")
    df_g = annual_means_genesys(GENESYS_FILE)
    print(f"  {len(df_g)} country-scenario-year observations, years: {sorted(df_g['year'].unique())}")

    print("Generating figure …")
    make_boxplot_figure(df_e, df_g)
    print("Done.")
