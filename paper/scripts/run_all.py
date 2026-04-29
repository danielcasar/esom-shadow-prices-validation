"""
run_all.py  —  Full replication pipeline

Executes every script in the correct order to reproduce all figures and
intermediate results reported in the paper. Run from any directory:

    python run_all.py

Expected runtime: ~15–30 minutes (dominated by data import and Stage 2).
Skip the data-import steps if data/ENTSOE_day_ahead_prices.csv and
data/GENeSYS_MOD_prices.csv already exist.
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
PYTHON      = sys.executable
ENV         = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def run(script: str, description: str):
    path = SCRIPTS_DIR / script
    print(f"\n{'='*70}")
    print(f"  {description}")
    print(f"  {script}")
    print(f"{'='*70}")
    t0 = time.time()
    result = subprocess.run([PYTHON, str(path)], check=False, env=ENV)
    elapsed = time.time() - t0
    if result.returncode != 0:
        print(f"\n[FAILED] {script} exited with code {result.returncode}")
        sys.exit(result.returncode)
    print(f"  Done in {elapsed:.1f}s")


def main():
    data_dir    = SCRIPTS_DIR.parent.parent / "data"
    entsoe_csv  = data_dir / "ENTSOE_day_ahead_prices.csv"
    genesys_csv = data_dir / "GENeSYS_MOD_prices.csv"

    # ── Step 0: Data import ──────────────────────────────────────────────────
    if not entsoe_csv.exists():
        run("import_entsoe_prices.py",
            "Step 0a: Download ENTSO-E day-ahead prices (requires API token)")
    else:
        print(f"\n[SKIP] ENTSO-E data already present: {entsoe_csv}")

    if not genesys_csv.exists():
        print("\n[ERROR] GENeSYS-MOD data not found.")
        print(f"  Expected: {genesys_csv}")
        print("  See README.md — Section 'Data' for instructions.")
        sys.exit(1)
    else:
        print(f"\n[SKIP] GENeSYS-MOD data already present: {genesys_csv}")

    # ── Step 1: Stage 1 — Kruskal-Wallis tests ───────────────────────────────
    run("stage1_kruskal_wallis.py",
        "Step 1: Stage 1 — Kruskal-Wallis tests (Table A1, Table A2)")

    # ── Step 2: Stage 2 — t-tests + deviation summary ────────────────────────
    run("stage2_t_tests.py",
        "Step 2: Stage 2 — group t-tests + deviation summary (Table 2, Figure 7)")

    # ── Step 3: Cross-year Pearson benchmarks ────────────────────────────────
    run("compute_entsoe_cross_year_pearson.py",
        "Step 3a: ENTSO-E cross-year Pearson (Figures 8, 9, A5, A6–A9)")
    run("compute_entsoe_cross_country_pearson.py",
        "Step 3b: ENTSO-E cross-country Pearson (Figure A1)")
    run("compute_genesys_vs_entsoe_year_pearson.py",
        "Step 3c: GENeSYS-MOD vs. ENTSO-E year Pearson (Figure 9)")

    # ── Step 4: Stage 3 — profile correlations ───────────────────────────────
    run("stage3_pearson_correlations.py",
        "Step 4: Stage 3 — profile correlations (Figures A4, A6–A9)")

    # ── Step 5: Compression factors ──────────────────────────────────────────
    run("compute_compression_factors.py",
        "Step 5: Compression factors ξ (Table A3)")

    # ── Step 6: Figures ──────────────────────────────────────────────────────
    run("plot_annual_mean_prices.py",      "Step 6a: Figure 4")
    run("plot_price_duration_curves.py",   "Step 6b: Figure 5")
    run("plot_dimension_profiles.py",      "Step 6c: Figure 6")
    run("plot_compression_factors.py",     "Step 6d: Figure 7")
    run("plot_pearson_stability_decay.py", "Step 6e: Figure 8")
    run("plot_pearson_alignment_heatmap.py","Step 6f: Figure 9")

    # ── Step 7: Appendix figures ─────────────────────────────────────────────
    run("plot_country_clusters.py",                "Step 7a: Figure A1")
    run("plot_genesys_cross_scenario_heatmap.py",  "Step 7b: Figure A2")
    run("plot_genesys_cross_year_heatmap.py",      "Step 7c: Figure A3")
    run("plot_entsoe_cross_year_heatmap.py",       "Step 7d: Figure A4")
    run("plot_pearson_benchmark.py",               "Step 7e: Figures A5-A8")
    run("plot_pearson_vs_spearman.py",             "Step 7f: Figure A9")

    print(f"\n{'='*70}")
    print("  All steps completed successfully.")
    print(f"  Figures saved to: paper/plots/")
    print(f"  Results saved to: results/calendar_effects/")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
