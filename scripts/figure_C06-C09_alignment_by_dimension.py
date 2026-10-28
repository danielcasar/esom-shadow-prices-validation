"""
figure_C06-C09_alignment_by_dimension.py — Figures C.6-C.9: model-market alignment by model year, one figure per dimension.

Dots: cluster-mean model-market Pearson rho per model year (2018, 2025,
2030), pooled across the four scenarios. Shaded bars: 95% bootstrap CI of the
cluster-median ENTSO-E cross-year rho (10,000 resamples). Benchmark and
model-market rho are defined as in Figure 9:
  Hour-of-Day: model years 2018/2025 vs. the same ENTSO-E year, benchmark of
               adjacent-year pairs; model year 2030 vs. all ENTSO-E years
               except 2021 and 2022, benchmark of 5-year pairs
  Other dimensions: all ENTSO-E years, benchmark of all year pairs

Inputs:
  results/intermediate/genesys_vs_entsoe_year_pearson.csv
  results/intermediate/entsoe_cross_year_pearson.csv
Outputs (results/figures/): Figure_C6.pdf (Hour-of-Day), Figure_C7.pdf
  (Day-of-Week), Figure_C8.pdf (Month-of-Year), Figure_C9.pdf (Season)
"""

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import CLUSTERS

matplotlib.rcParams.update({
    "font.family":     "sans-serif",
    "font.sans-serif": ["Arial"],
    "font.size":       9,
    "axes.labelsize":  9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.linewidth":  0.8,
})

BASE       = Path(__file__).parent.parent
YEAR_FILE  = BASE / "results" / "intermediate" / "genesys_vs_entsoe_year_pearson.csv"
CROSS_FILE = BASE / "results" / "intermediate" / "entsoe_cross_year_pearson.csv"
OUT_DIR    = BASE / "results" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RNG    = np.random.default_rng(42)
N_BOOT = 10_000
CRISIS = {2021, 2022}

C_BAND_EDGE = "#1a6faf"

YEAR_COLORS  = {2018: "#2166ac", 2025: "#4dac26", 2030: "#ca0020"}
YEAR_MARKERS = {2018: "o",       2025: "s",       2030: "^"}

cluster_names = list(CLUSTERS.keys())
n = len(cluster_names)
x = np.arange(n)


def bootstrap_ci(values, n_boot=N_BOOT, ci=95):
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) < 2:
        m = np.median(values) if len(values) else np.nan
        return m, m, m
    boot = np.array([np.median(RNG.choice(values, size=len(values), replace=True))
                     for _ in range(n_boot)])
    lo = np.percentile(boot, (100 - ci) / 2)
    hi = np.percentile(boot, 100 - (100 - ci) / 2)
    return np.median(values), lo, hi


# ── Load data ─────────────────────────────────────────────────────────────────
df_year  = pd.read_csv(YEAR_FILE)
df_cross = pd.read_csv(CROSS_FILE)
df_cross["lag"] = df_cross["year2"] - df_cross["year1"]

all_entsoe_years = sorted(df_year["entsoe_year"].unique().tolist())
nocrisis_entsoe  = [y for y in all_entsoe_years if y not in CRISIS]


def get_bm_vals(dim, lag=None):
    """Per-cluster mean-rho values across year-pairs (optionally filtered by lag)."""
    sub = df_cross[df_cross["dimension"] == dim]
    if lag is not None:
        sub = sub[sub["lag"] == lag]
    out = {}
    for cname, members in CLUSTERS.items():
        vals = (sub[sub["country"].isin(members)]
                .groupby(["year1", "year2"])["rho"]
                .mean()
                .tolist())
        out[cname] = vals if vals else [float("nan")]
    return out


def get_dots(dim, g_years, e_year_filter=None):
    """Mean pearson_r per (country, genesys_year), pooled across scenarios."""
    sub = df_year[(df_year["dimension"] == dim) &
                  (df_year["genesys_year"].isin(g_years))]
    if e_year_filter is not None:
        sub = sub[sub["entsoe_year"].isin(e_year_filter)]
    return sub.groupby(["country", "genesys_year"])["pearson_r"].mean().reset_index()


# ── Common drawing helper ─────────────────────────────────────────────────────
def draw_simple(ax, bm, dots_df, active_years):
    """One CI bar per cluster + dots offset by year."""
    offsets = dict(zip(active_years, np.linspace(-0.22, 0.22, len(active_years))))
    y_vals = []

    for i, cname in enumerate(cluster_names):
        vals = bm.get(cname, [])
        if len(vals) >= 2:
            _, ci_lo, ci_hi = bootstrap_ci(vals)
            ax.bar(i, ci_hi - ci_lo, bottom=ci_lo, width=0.65,
                   color=C_BAND_EDGE, alpha=0.35, linewidth=0, zorder=2)
            y_vals.extend([ci_lo, ci_hi])

    for i, (cname, members) in enumerate(CLUSTERS.items()):
        for yr in active_years:
            rows = dots_df[(dots_df["country"].isin(members)) &
                           (dots_df["genesys_year"] == yr)]
            if rows.empty:
                continue
            val = rows["pearson_r"].mean()
            y_vals.append(val)
            ax.scatter(i + offsets[yr], val,
                       color=YEAR_COLORS[yr], marker=YEAR_MARKERS[yr],
                       s=32, zorder=5, edgecolors="white", linewidths=0.4)

    _format_axes(ax, y_vals)


def _format_axes(ax, y_vals):
    ax.axhline(0, color="black", linewidth=0.6, linestyle=":", zorder=3)
    ax.set_xlim(-0.7, n - 0.3)
    ax.set_xticks(x)
    ax.set_xticklabels(cluster_names, rotation=45, ha="right")
    ax.tick_params(axis="x", pad=1)
    ax.set_ylabel(r"Pearson $\rho$")
    ax.grid(True, axis="y", alpha=0.25, linestyle="--", linewidth=0.5)
    y_bot = min(y_vals) - 0.08 if y_vals and min(y_vals) < 0 else -0.08
    ax.set_ylim(y_bot, 1.0)


def add_bottom_legend(ax, active_years):
    band_p = mpatches.Patch(facecolor=C_BAND_EDGE, alpha=0.35, linewidth=0,
                            label="ENTSO-E benchmark")
    handles = [band_p] + [
        plt.Line2D([0], [0], marker=YEAR_MARKERS[yr], color="w",
                   markerfacecolor=YEAR_COLORS[yr], markersize=7,
                   label=f"GENeSYS {yr}")
        for yr in active_years
    ]
    ax.legend(handles=handles, fontsize=8, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.25),
              ncol=len(handles))


# ── Hour-of-Day merged: split bars (2018+2025 left, 2030 right) ───────────────
TOTAL_W  = 0.72
W_LEFT   = TOTAL_W * 2 / 3
W_RIGHT  = TOTAL_W * 1 / 3
CX_LEFT  = -TOTAL_W / 2 + W_LEFT  / 2
CX_RIGHT =  TOTAL_W / 2 - W_RIGHT / 2
OFF_2018 = CX_LEFT  - 0.10
OFF_2025 = CX_LEFT  + 0.08
OFF_2030 = CX_RIGHT


def draw_hod_merged(ax, bm_left, bm_right, dots_2018, dots_2025, dots_2030):
    y_vals = []

    for i, cl in enumerate(cluster_names):
        vals = bm_left.get(cl, [])
        if len(vals) >= 2:
            _, ci_lo, ci_hi = bootstrap_ci(vals)
            ax.bar(i + CX_LEFT, ci_hi - ci_lo, bottom=ci_lo,
                   width=W_LEFT * 0.85, color=C_BAND_EDGE, alpha=0.35,
                   linewidth=0, zorder=2)
            y_vals.extend([ci_lo, ci_hi])

    for i, cl in enumerate(cluster_names):
        vals = bm_right.get(cl, [])
        if len(vals) >= 2:
            _, ci_lo, ci_hi = bootstrap_ci(vals)
            ax.bar(i + CX_RIGHT, ci_hi - ci_lo, bottom=ci_lo,
                   width=W_RIGHT * 0.85, color=C_BAND_EDGE, alpha=0.35,
                   linewidth=0, zorder=2)
            y_vals.extend([ci_lo, ci_hi])

    for i, (cname, members) in enumerate(CLUSTERS.items()):
        for dots_df, offset, yr in [
            (dots_2018, OFF_2018, 2018),
            (dots_2025, OFF_2025, 2025),
            (dots_2030, OFF_2030, 2030),
        ]:
            rows = dots_df[dots_df["country"].isin(members)]
            if rows.empty:
                continue
            val = rows["pearson_r"].mean()
            y_vals.append(val)
            ax.scatter(i + offset, val,
                       color=YEAR_COLORS[yr], marker=YEAR_MARKERS[yr],
                       s=32, zorder=5, edgecolors="white", linewidths=0.4)

    _format_axes(ax, y_vals)


# ── Generate the four figures ─────────────────────────────────────────────────
def save_figure(filename, draw_fn, active_years):
    fig, ax = plt.subplots(figsize=(6.67, 2.8))
    draw_fn(ax)
    add_bottom_legend(ax, active_years)
    out = OUT_DIR / filename
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


# Figure C.6 — Hour-of-Day merged (year-matched + 2030)
hod_2018 = get_dots("hour", [2018], e_year_filter=[2018])
hod_2025 = get_dots("hour", [2025], e_year_filter=[2025])
hod_2030 = get_dots("hour", [2030], e_year_filter=nocrisis_entsoe)
bm_hour_a = get_bm_vals("hour", lag=1)   # adjacent-year pairs
bm_hour_b = get_bm_vals("hour", lag=5)   # ~5-year lag pairs

save_figure(
    "Figure_C6.pdf",
    lambda ax: draw_hod_merged(ax, bm_hour_a, bm_hour_b,
                               hod_2018, hod_2025, hod_2030),
    [2018, 2025, 2030],
)

# Figure C.7 — Day-of-Week
dow_dots = get_dots("weekday", [2018, 2025, 2030])
bm_dow   = get_bm_vals("weekday")
save_figure(
    "Figure_C7.pdf",
    lambda ax: draw_simple(ax, bm_dow, dow_dots, [2018, 2025, 2030]),
    [2018, 2025, 2030],
)

# Figure C.8 — Month-of-Year
month_dots = get_dots("month", [2018, 2025, 2030])
bm_month   = get_bm_vals("month")
save_figure(
    "Figure_C8.pdf",
    lambda ax: draw_simple(ax, bm_month, month_dots, [2018, 2025, 2030]),
    [2018, 2025, 2030],
)

# Figure C.9 — Season
season_dots = get_dots("season", [2018, 2025, 2030])
bm_season   = get_bm_vals("season")
save_figure(
    "Figure_C9.pdf",
    lambda ax: draw_simple(ax, bm_season, season_dots, [2018, 2025, 2030]),
    [2018, 2025, 2030],
)

matplotlib.rcParams.update(matplotlib.rcParamsDefault)
print("Done.")
