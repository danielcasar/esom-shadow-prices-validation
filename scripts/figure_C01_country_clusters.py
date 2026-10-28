"""
figure_C01_country_clusters.py — Figure C.1: country clustering dendrogram.

Hierarchical clustering of 22 European countries based on the cross-country
Pearson similarity matrix (averaged over all four temporal dimensions and
years 2018-2025).

Input : results/intermediate/entsoe_cross_country_pearson.csv
Output: results/figures/Figure_C1.pdf
"""

import os
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
from scipy.spatial.distance import squareform

matplotlib.rcParams.update({
    "font.family":     "sans-serif",
    "font.sans-serif": ["Arial"],
    "font.size":       9,
    "axes.labelsize":  9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
})

from config import COUNTRIES

# ---------------------------------------------------------------------------
BASE  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(BASE, 'results', 'intermediate',
                     'entsoe_cross_country_pearson.csv')

# ---------------------------------------------------------------------------

def cluster_countries(n_clusters: int = 7,
                      output_path: str | None = None) -> dict[str, int]:
    """
    Cluster countries via hierarchical clustering on the cross-country
    Pearson similarity matrix (averaged across all four dimensions and years).

    Distance metric: 1 - rho_mean  (ranges 0..2, but in practice 0..1)
    Linkage method : average  (works with precomputed distances)

    Parameters
    ----------
    n_clusters  : int   number of flat clusters to cut from the dendrogram
    output_path : str   if given, save the dendrogram figure there

    Returns
    -------
    dict  country -> cluster_id  (1-indexed)
    """
    df = pd.read_csv(INPUT)
    n  = len(COUNTRIES)

    # ── Build symmetric similarity matrix averaged over all dimensions ────────
    sim = np.zeros((n, n))
    cnt = np.zeros((n, n))
    np.fill_diagonal(sim, 1.0)
    np.fill_diagonal(cnt, 1.0)

    means = df.groupby(['country1', 'country2'])['rho'].mean()
    for (c1, c2), val in means.items():
        if c1 in COUNTRIES and c2 in COUNTRIES:
            i, j = COUNTRIES.index(c1), COUNTRIES.index(c2)
            sim[i, j] += val
            sim[j, i] += val
            cnt[i, j] += 1
            cnt[j, i] += 1

    with np.errstate(invalid='ignore'):
        sim = np.where(cnt > 0, sim / cnt, 0.0)
    np.fill_diagonal(sim, 1.0)

    # ── Distance matrix & condensed form ─────────────────────────────────────
    dist = 1.0 - sim
    np.fill_diagonal(dist, 0.0)
    dist = np.clip(dist, 0, None)          # numerical safety
    condensed = squareform(dist)

    # ── Hierarchical clustering ───────────────────────────────────────────────
    Z      = linkage(condensed, method='average')
    labels = fcluster(Z, t=n_clusters, criterion='maxclust')

    # ── Dendrogram figure ─────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(6.67, 3.5))
    dendrogram(
        Z,
        labels=COUNTRIES,
        ax=ax,
        color_threshold=Z[-(n_clusters - 1), 2],
        above_threshold_color='gray',
        leaf_font_size=9,
    )
    ax.set_ylabel('Distance  (1 − ρ)', fontsize=9)
    ax.tick_params(labelsize=8)
    ax.axhline(Z[-(n_clusters - 1), 2], color='black',
               linewidth=0.8, linestyle='--', alpha=0.6)
    plt.tight_layout()

    out = output_path or os.path.join(
        BASE, 'results', 'figures', 'Figure_C1.pdf')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved dendrogram: {out}')

    # ── Print cluster assignments ─────────────────────────────────────────────
    mapping = {c: int(labels[i]) for i, c in enumerate(COUNTRIES)}
    for cid in sorted(set(labels)):
        members = [c for c, l in mapping.items() if l == cid]
        print(f'  Cluster {cid}: {members}')

    return mapping


if __name__ == '__main__':
    print('Country clustering')
    cluster_countries(n_clusters=10)
