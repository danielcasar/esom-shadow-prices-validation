"""
run_all.py  —  Full replication pipeline

Executes every analysis script in order and reproduces all tables, figures,
and numbers reported in the paper from the input data in data/. Run from any
directory:

    python scripts/run_all.py

Expected runtime: 5–10 minutes on a standard laptop. Outputs are written to
results/ (figures, tables, intermediate), which is created on the first run.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 output on Windows (avoids cp1252 encoding errors)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPTS_DIR = Path(__file__).parent
DATA_DIR    = SCRIPTS_DIR.parent / "data"
PYTHON      = sys.executable
ENV         = {**os.environ, "PYTHONIOENCODING": "utf-8", "MPLBACKEND": "Agg"}

REQUIRED_DATA = [
    "ENTSOE_day_ahead_prices.csv",
    "GENeSYS_MOD_prices.csv",
    "ENTSOE_vre_generation_2025.csv",
    "GENeSYS_MOD_vre_production_2025.csv",
]

STEPS = [
    # ── Stage 1 and Stage 2 statistics ───────────────────────────────────────
    ("stage1_kruskal_wallis.py",                "Stage 1: Kruskal-Wallis tests"),
    ("stage2_t_tests.py",                       "Stage 2: group t-tests"),
    # ── Stage 3 correlations and benchmark ───────────────────────────────────
    ("compute_benchmark_correlations.py",       "Cross-year and cross-country Pearson correlations"),
    ("compute_model_market_correlations.py",    "GENeSYS-MOD vs. ENTSO-E Pearson correlations"),
    ("stage3_pearson_correlations.py",          "Stage 3: profile correlations (Pearson and Spearman)"),
    # ── Compression factors and value factors ────────────────────────────────
    ("compute_compression_factors.py",          "Compression factors xi"),
    ("compute_value_factors.py",                "Solar and wind value factors (Section 4.2)"),
    # ── Tables and numbers quoted in the text ────────────────────────────────
    ("tables.py",                               "All tables, Figure 1 data, and numbers quoted in the text"),
    # ── Figures (main text) ──────────────────────────────────────────────────
    ("plot_annual_mean_prices.py",              "Figure 4"),
    ("plot_price_duration_curves.py",           "Figure 5"),
    ("plot_dimension_profiles.py",              "Figure 6"),
    ("plot_compression_factors.py",             "Figure 7"),
    ("plot_pearson_stability_decay.py",         "Figure 8"),
    ("plot_pearson_alignment_heatmap.py",       "Figure 9"),
    # ── Figures (Appendix C) ─────────────────────────────────────────────────
    ("plot_country_clusters.py",                "Figure C.1"),
    ("plot_price_distribution.py",              "Figure C.2"),
    ("plot_genesys_cross_scenario_heatmap.py",  "Figure C.3"),
    ("plot_genesys_cross_year_heatmap.py",      "Figure C.4"),
    ("plot_entsoe_cross_year_heatmap.py",       "Figure C.5"),
    ("plot_pearson_benchmark.py",               "Figures C.6-C.9"),
    ("plot_pearson_vs_spearman.py",             "Figure C.10"),
]


def run(script: str, description: str, i: int, n: int) -> None:
    print(f"\n{'=' * 70}")
    print(f"  [{i}/{n}] {description}")
    print(f"  {script}")
    print(f"{'=' * 70}", flush=True)
    t0 = time.time()
    result = subprocess.run([PYTHON, str(SCRIPTS_DIR / script)], check=False,
                            env=ENV, cwd=SCRIPTS_DIR)
    if result.returncode != 0:
        print(f"\n[FAILED] {script} exited with code {result.returncode}")
        sys.exit(result.returncode)
    print(f"  Done in {time.time() - t0:.1f}s", flush=True)


def main():
    missing = [f for f in REQUIRED_DATA if not (DATA_DIR / f).exists()]
    if missing:
        print("[ERROR] Missing input data in data/:")
        for f in missing:
            print(f"  - {f}")
        print("See data/README.md.")
        sys.exit(1)

    t0 = time.time()
    for i, (script, description) in enumerate(STEPS, start=1):
        run(script, description, i, len(STEPS))

    print(f"\n{'=' * 70}")
    print(f"  All steps completed in {(time.time() - t0) / 60:.1f} min.")
    print("  Figures:              results/figures/")
    print("  Tables and values:    results/tables/")
    print("  Intermediate results: results/intermediate/")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
