"""
figure_09_alignment_heatmap.py — Figure 9: model-market alignment relative to the benchmark.

Rows: dimension x model year (12); columns: country clusters (10).
Cell: absolute distance of the cluster-mean model-market rho from the 95%
bootstrap CI of the cluster-median ENTSO-E cross-year rho (0 = within the CI).

Benchmark (ENTSO-E cross-year pairs, Table 8):
  Hour-of-Day: adjacent years (lag 1) for model years 2018 and 2025,
               5-year pairs for model year 2030
  Other dimensions: all year pairs
Model-market rho (mean over countries, scenarios, and ENTSO-E years):
  Hour-of-Day 2018 / 2025: ENTSO-E year = model year
  Hour-of-Day 2030: all ENTSO-E years except 2021 and 2022
  Other dimensions: all ENTSO-E years

Inputs:
  results/intermediate/genesys_vs_entsoe_year_pearson.csv
  results/intermediate/entsoe_cross_year_pearson.csv
Output:
  results/figures/Figure_9.pdf
"""

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path

RNG = np.random.default_rng(42)

BASE       = Path(__file__).parent.parent
YEAR_FILE  = BASE / "results" / "intermediate" / "genesys_vs_entsoe_year_pearson.csv"
CROSS_FILE = BASE / "results" / "intermediate" / "entsoe_cross_year_pearson.csv"
OUT        = BASE / "results" / "figures" / "Figure_9.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

CRISIS = {2021, 2022}
GENESYS_YEARS = [2018, 2025, 2030]

CLUSTERS = {
    "Iberian":    ["ES", "PT"],
    "Baltic":     ["EE", "LT", "LV"],
    "South-East": ["BG", "HR", "HU", "SI"],
    "Core-East":  ["AT", "CZ", "DE", "SK"],
    "Core-West":  ["BE", "CH", "FR", "NL"],
    "FI": ["FI"], "GR": ["GR"], "RO": ["RO"], "IE": ["IE"], "PL": ["PL"],
}
CLUSTER_ORDER = list(CLUSTERS.keys())

DIMS = ["hour", "weekday", "month", "season"]
DIM_LABELS = {
    "hour":    "Hour-of-Day",
    "weekday": "Day-of-Week",
    "month":   "Month-of-Year",
    "season":  "Season",
}

# ── Load data ─────────────────────────────────────────────────────────────────
df_year  = pd.read_csv(YEAR_FILE)
df_cross = pd.read_csv(CROSS_FILE)
df_cross["lag"] = df_cross["year2"] - df_cross["year1"]

all_entsoe_years = sorted(df_year["entsoe_year"].unique())
nocrisis = [y for y in all_entsoe_years if y not in CRISIS]


def bootstrap_ci(values, n_boot=10_000, ci=95):
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if len(values) < 2:
        m = float(np.nanmedian(values))
        return m, m, m
    boot = np.array([np.median(RNG.choice(values, size=len(values), replace=True))
                     for _ in range(n_boot)])
    lo = np.percentile(boot, (100 - ci) / 2)
    hi = np.percentile(boot, 100 - (100 - ci) / 2)
    return np.median(values), lo, hi


def benchmark_ci_cluster(dim, genesys_year, cluster_members):
    """95% bootstrap CI of ENTSO-E cross-year median ρ for a specific cluster."""
    sub = df_cross[df_cross["dimension"] == dim]
    if dim == "hour":
        if genesys_year in (2018, 2025):
            sub = sub[sub["lag"] == 1]
        else:
            sub = sub[sub["lag"] == 5]
    # all other dimensions: all year pairs
    sub = sub[sub["country"].isin(cluster_members)]
    vals = sub.groupby(["year1", "year2"])["rho"].mean().values
    if len(vals) < 2:
        m = float(np.nanmedian(vals)) if len(vals) else np.nan
        return m, m
    _, lo, hi = bootstrap_ci(vals)
    return lo, hi


def model_rho(dim, genesys_year, cluster_members):
    """Mean model-market ρ for a cluster, averaged across scenarios and matched ENTSO-E years."""
    sub = df_year[
        (df_year["dimension"] == dim) &
        (df_year["genesys_year"] == genesys_year) &
        (df_year["country"].isin(cluster_members))
    ]
    if dim == "hour":
        if genesys_year in (2018, 2025):
            sub = sub[sub["entsoe_year"] == genesys_year]
        else:
            sub = sub[~sub["entsoe_year"].isin(CRISIS)]
    # all dimensions except HoD: all ENTSO-E years
    if sub.empty:
        return np.nan
    return sub["pearson_r"].mean()


# ── Build distance matrix ─────────────────────────────────────────────────────
# Rows: (dim, year) grouped by dimension, Cols: clusters
rows = [(d, y) for d in DIMS for y in GENESYS_YEARS]
row_labels = []
for i, (d, y) in enumerate(rows):
    row_labels.append(str(y))

dist_mat = np.full((len(rows), len(CLUSTER_ORDER)), np.nan)

for r_idx, (dim, yr) in enumerate(rows):
    for c_idx, cname in enumerate(CLUSTER_ORDER):
        members = CLUSTERS[cname]
        ci_lo, ci_hi = benchmark_ci_cluster(dim, yr, members)
        rho = model_rho(dim, yr, members)
        if np.isnan(rho):
            dist_mat[r_idx, c_idx] = np.nan
        elif rho < ci_lo:
            dist_mat[r_idx, c_idx] = ci_lo - rho   # positive: below benchmark
        elif rho > ci_hi:
            dist_mat[r_idx, c_idx] = rho - ci_hi   # positive: above benchmark
        else:
            dist_mat[r_idx, c_idx] = 0.0            # within benchmark

# ── Plot ──────────────────────────────────────────────────────────────────────
matplotlib.rcParams.update({
    "font.family":     "sans-serif",
    "font.sans-serif": ["Arial"],
    "font.size":       8,
    "axes.labelsize":  8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.linewidth":  0.8,
})

fig, ax = plt.subplots(figsize=(6.67, 3.8))

vmax = 1.0
# Soft green (0) -> light yellow -> muted red (large distance)
cmap = mcolors.LinearSegmentedColormap.from_list(
    "soft_traffic", ["#74c476", "#ffffbf", "#fc8d59"], N=256
)
norm = mcolors.Normalize(vmin=0, vmax=vmax)

im = ax.imshow(dist_mat, cmap=cmap, norm=norm, aspect="auto")


# Separator lines between dimension groups (every 3 rows)
for sep in [2.5, 5.5, 8.5]:
    ax.axhline(sep, color="black", linewidth=1.2, linestyle="-")


ax.set_xticks(range(len(CLUSTER_ORDER)))
ax.set_xticklabels(CLUSTER_ORDER, rotation=35, ha="right", fontsize=9)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels(row_labels, fontsize=9)

# Dimension labels: bold horizontal abbreviations to the left of the year ticks
from matplotlib.transforms import blended_transform_factory
DIM_ABBR = {"hour": "HoD", "weekday": "DoW", "month": "MoY", "season": "Sea"}
trans = blended_transform_factory(ax.transAxes, ax.transData)
dim_midpoints = [1, 4, 7, 10]   # centre row of each 3-row group (0-indexed)
for dim, mid in zip(DIMS, dim_midpoints):
    ax.text(-0.12, mid, DIM_ABBR[dim], transform=trans,
            rotation=0, va="center", ha="center",
            fontsize=9, fontweight="bold")

cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
cbar.set_label("Distance from benchmark CI", fontsize=9)
cbar.ax.tick_params(labelsize=9)

fig.subplots_adjust(left=0.18, right=0.91, top=0.97, bottom=0.14)
fig.savefig(OUT, dpi=300, bbox_inches="tight")
plt.close(fig)
matplotlib.rcParams.update(matplotlib.rcParamsDefault)
print(f"Saved: {OUT}")
