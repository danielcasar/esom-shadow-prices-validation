"""
plot_pearson_stability_decay.py

Plots mean ENTSO-E cross-year Pearson rho (averaged across all countries)
as a function of temporal distance (lag in years), separately for each
of the four temporal dimensions.

Output: results/plots/pearson_stability_decay.png
"""

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import os
from pathlib import Path

matplotlib.rcParams.update({
    "font.family":     "sans-serif",
    "font.sans-serif": ["Arial"],
    "font.size":       9,
    "axes.titlesize":  9,
    "axes.labelsize":  9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 9,
})

BASE = str(Path(__file__).parent.parent.parent)

INPUT  = os.path.join(BASE, "results", "calendar_effects", "entsoe_cross_year_pearson.csv")
OUTPUT = os.path.join(BASE, "paper", "plots", "Figure_8.pdf")

# ── Load and aggregate ────────────────────────────────────────────────────────

df = pd.read_csv(INPUT)
df["lag"] = df["year2"] - df["year1"]

def q25(x): return x.quantile(0.25)
def q75(x): return x.quantile(0.75)

summary = (df.groupby(["dimension", "lag"])["rho"]
             .agg(["median", q25, q75])
             .reset_index())

dim_map = {
    "hour":    "Hour-of-Day",
    "weekday": "Day-of-Week",
    "month":   "Month-of-Year",
    "season":  "Season",
}
dim_order  = ["hour", "weekday", "month", "season"]
dim_colors = {
    "hour":    "#1f77b4",
    "weekday": "#ff7f0e",
    "month":   "#2ca02c",
    "season":  "#d62728",
}
dim_markers = {
    "hour":    "o",
    "weekday": "s",
    "month":   "^",
    "season":  "D",
}

# ── Plot ──────────────────────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(6.67, 3.0))

ax.axhline(0, color="gray", linewidth=0.6, linestyle="--", zorder=0)

for dim in dim_order:
    sub = summary[summary["dimension"] == dim].sort_values("lag")
    ax.plot(sub["lag"], sub["median"],
            label=dim_map[dim],
            color=dim_colors[dim],
            marker=dim_markers[dim],
            markersize=4,
            linewidth=1.2)
    ax.fill_between(sub["lag"],
                    sub["q25"],
                    sub["q75"],
                    color=dim_colors[dim],
                    alpha=0.10)

ax.set_xlabel("Temporal distance (years)", fontsize=9)
ax.set_ylabel("Median Pearson $\\rho$", fontsize=9)
ax.set_xticks(range(1, 8))
ax.set_ylim(-0.2, 1.05)
ax.set_xlim(0.7, 7.3)
ax.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.5)
ax.spines[["top", "right"]].set_visible(False)

fig.legend(loc="lower center", ncol=4, fontsize=9,
           frameon=False, bbox_to_anchor=(0.5, -0.04))
plt.tight_layout(pad=0.5, rect=[0, 0.08, 1, 1])
fig.savefig(OUTPUT, dpi=300, bbox_inches="tight")
plt.close()
print(f"Saved: {OUTPUT}")
