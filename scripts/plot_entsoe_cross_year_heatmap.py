"""
Stage 3 cross-year ENTSO-E heatmap.

Two combined 8×8 subplots, each showing two temporal dimensions:
  Left : upper triangle = Hour-of-Day, lower triangle = Day-of-Week
  Right: upper triangle = Month-of-Year, lower triangle = Season

Diagonal = 1 (same year).  A thin diagonal line separates the two dimensions
within each subplot, and dimension labels are placed in each triangle.

Input : results/intermediate/entsoe_cross_year_pearson.csv
Output: results/figures/Figure_C5.pdf
"""

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from pathlib import Path

matplotlib.rcParams.update({
    "font.family":     "sans-serif",
    "font.sans-serif": ["Arial"],
    "font.size":       9,
    "axes.labelsize":  9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.linewidth":  0.8,
})

BASE    = Path(__file__).parent.parent
INPUT   = BASE / "results" / "intermediate" / "entsoe_cross_year_pearson.csv"
OUT_DIR = BASE / "results" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT  = OUT_DIR / "Figure_C5.pdf"

DIM_LABELS = {
    'hour'   : 'Hour-of-Day',
    'weekday': 'Day-of-Week',
    'month'  : 'Month-of-Year',
    'season' : 'Season',
}
YEARS = list(range(2018, 2026))   # 2018 … 2025

# Two combined subplots: (upper_dim, lower_dim, subplot_title)
PANELS = [
    ('hour',  'weekday', 'Hour-of-Day (upper) / Day-of-Week (lower)'),
    ('month', 'season',  'Month-of-Year (upper) / Season (lower)'),
]

# ---------------------------------------------------------------------------

def build_combined_matrix(df, dim_upper, dim_lower):
    """
    8×8 matrix combining two dimensions:
      - diagonal        : 1.0
      - upper triangle  : mean rho for dim_upper
      - lower triangle  : mean rho for dim_lower
    """
    n = len(YEARS)
    mat = np.full((n, n), np.nan)
    # diagonal left as NaN -> rendered grey via cmap.set_bad

    for dim, triangle in [(dim_upper, 'upper'), (dim_lower, 'lower')]:
        means = df[df['dimension'] == dim].groupby(['year1', 'year2'])['rho'].mean()
        for (y1, y2), val in means.items():
            i = YEARS.index(y1)
            j = YEARS.index(y2)
            # raw data always has year1 < year2, so j > i
            if triangle == 'upper':
                mat[i, j] = val          # upper triangle
            else:
                mat[j, i] = val          # mirror to lower triangle

    return mat


def main():
    df = pd.read_csv(INPUT)

    cmap = plt.get_cmap('RdYlGn').copy()
    cmap.set_bad('lightgrey')

    n = len(YEARS)

    # Reserve space on the left for the colorbar; use full width
    fig, axes = plt.subplots(1, 2, figsize=(6.67, 3))
    fig.subplots_adjust(left=0.14, right=0.99, top=0.90, bottom=0.12,
                        wspace=0.30)

    im = None
    for ax, (dim_upper, dim_lower, _) in zip(axes, PANELS):
        mat = build_combined_matrix(df, dim_upper, dim_lower)

        im = ax.imshow(mat, vmin=-1, vmax=1, cmap=cmap, aspect='equal')

        # ── diagonal separator line ────────────────────────────────────
        ax.plot([-0.5, n - 0.5], [-0.5, n - 0.5],
                color='black', linewidth=1.2, zorder=5)

        # ── axes: labels on all four sides ────────────────────────────
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(YEARS, rotation=45, ha='right')
        ax.set_yticklabels(YEARS)
        is_right_panel = ax is axes[1]
        ax.tick_params(top=True, bottom=True, left=True, right=True,
                       labeltop=True, labelbottom=True,
                       labelleft=not is_right_panel, labelright=is_right_panel,
                       labelsize=10)
        ax.xaxis.set_tick_params(which='both', rotation=45, labelsize=10)
        # fix top x-label alignment (ha='right' is correct for bottom, not top)
        for tick in ax.xaxis.get_major_ticks():
            tick.label2.set_ha('left')
            tick.label2.set_va('bottom')

        # ── upper dimension bold above, lower dimension bold below ─────
        ax.set_title(DIM_LABELS[dim_upper], fontsize=9, fontweight='bold', pad=8)
        ax.set_xlabel(DIM_LABELS[dim_lower], fontsize=9, fontweight='bold', labelpad=8)
        ax.set_ylabel('')

    # ── single shared colourbar on the far left, matching plot height ─
    fig.canvas.draw()                          # force layout so positions are final
    # shared y-axis labels centred in the gap between the two panels
    pos0 = axes[0].get_position()
    pos1 = axes[1].get_position()
    mid_x = (pos0.x1 + pos1.x0) / 2
    for i, yr in enumerate(YEARS):
        _, y_disp = axes[0].transData.transform((0, i))
        _, y_fig  = fig.transFigure.inverted().transform((0, y_disp))
        fig.text(mid_x, y_fig, str(yr), ha='center', va='center', fontsize=9)
    pos = axes[0].get_position()               # actual axes position in figure fraction
    cax = fig.add_axes([0.02, pos.y0, 0.015, pos.height])
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_ticks([-1, -0.5, 0, 0.5, 1])
    cbar.ax.tick_params(labelsize=10)
    cbar.ax.yaxis.set_ticks_position('left')
    cbar.ax.yaxis.set_label_position('left')
    cbar.set_label(r'Pearson $\rho$', fontsize=9)

    fig.savefig(OUTPUT, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {OUTPUT}')


if __name__ == '__main__':
    main()

matplotlib.rcParams.update(matplotlib.rcParamsDefault)
