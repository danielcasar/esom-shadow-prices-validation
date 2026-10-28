"""
figure_C10_pearson_vs_spearman.py — Figure C.10: Pearson vs. Spearman correlations.

Layout  : 2 × 2 subplots (one per dimension)
X-axis  : Pearson r
Y-axis  : Spearman ρ
Each dot: one (country × scenario) observation, coloured by scenario
Diagonal: y = x reference line (perfect agreement between the two metrics)

Input  : results/intermediate/stage3_pearson_correlations.csv
Output : results/figures/Figure_C10.pdf
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import SCENARIOS
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

matplotlib.rcParams.update({
    "font.family":     "sans-serif",
    "font.sans-serif": ["Arial"],
    "font.size":       9,
    "axes.labelsize":  9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
})

# ---------------------------------------------------------------------------
BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT  = os.path.join(BASE, 'results', 'intermediate',
                      'stage3_pearson_correlations.csv')
OUTPUT = os.path.join(BASE, 'results', 'figures', 'Figure_C10.pdf')

# ---------------------------------------------------------------------------
DIM_ORDER  = ['hour', 'weekday', 'month', 'season']
DIM_LABELS = {
    'hour'   : 'Hour-of-Day',
    'weekday': 'Day-of-Week',
    'month'  : 'Month-of-Year',
    'season' : 'Season',
}

SCEN_COLORS = {
    'GoRES'         : '#2166ac',
    'NECPEssentials': '#4dac26',
    'REPowerEU++'   : '#d01c8b',
    'Trinity'       : '#f1a340',
}

DOT_SIZE  = 28
DOT_ALPHA = 0.65

# ---------------------------------------------------------------------------

def main():
    df = pd.read_csv(INPUT)

    fig, axes = plt.subplots(2, 2, figsize=(6.67, 7), sharex=True, sharey=True)
    axes = axes.flatten()

    for ax, dim in zip(axes, DIM_ORDER):
        sub = df[df['dimension'] == dim]

        # ── scatter per scenario ───────────────────────────────────────────
        for scen in SCENARIOS:
            s = sub[sub['scenario'] == scen]
            ax.scatter(
                s['pearson_r'], s['spearman_r'],
                s=DOT_SIZE, color=SCEN_COLORS[scen],
                alpha=DOT_ALPHA, linewidths=0.4,
                edgecolors='white', zorder=3,
                label=scen,
            )

        # ── reference lines ────────────────────────────────────────────────
        lim = (-0.75, 1.05)
        # diagonal y = x  (perfect agreement)
        ax.plot(lim, lim, color='#333333', linewidth=1.0,
                linestyle='--', zorder=2, label='$y = x$')
        # zero axes
        ax.axhline(0, color='#aaaaaa', linewidth=0.7, linestyle=':', zorder=1)
        ax.axvline(0, color='#aaaaaa', linewidth=0.7, linestyle=':', zorder=1)

        # ── Pearson vs Spearman agreement annotation ───────────────────────
        mae = (sub['pearson_r'] - sub['spearman_r']).abs().mean()
        ax.text(0.04, 0.97, f'MAE = {mae:.3f}',
                transform=ax.transAxes, ha='left', va='top',
                fontsize=9, color='#333333',
                bbox=dict(boxstyle='round,pad=0.25', fc='white',
                          ec='#cccccc', alpha=0.8))

        # ── cosmetics ─────────────────────────────────────────────────────
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.set_aspect('equal')
        ax.set_title(DIM_LABELS[dim], fontsize=9, fontweight='bold')
        ax.set_xlabel('Pearson $\\rho$', fontsize=9)
        ax.set_ylabel('Spearman $r$', fontsize=9)
        ax.tick_params(labelsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(color='#eeeeee', linewidth=0.6, zorder=0)

    # ── figure-level legend ───────────────────────────────────────────────
    scen_handles = [
        mpatches.Patch(color=SCEN_COLORS[s], alpha=0.8, label=s)
        for s in SCENARIOS
    ]
    diag_handle = Line2D([0], [0], color='#333333', linewidth=1.2,
                         linestyle='--', label='$y = x$ (perfect agreement)')
    fig.legend(
        handles=scen_handles + [diag_handle],
        loc='lower center',
        ncol=5,
        fontsize=9,
        frameon=False,
        bbox_to_anchor=(0.5, -0.01),
    )

    plt.tight_layout()
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    plt.savefig(OUTPUT, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {OUTPUT}')


if __name__ == '__main__':
    main()
