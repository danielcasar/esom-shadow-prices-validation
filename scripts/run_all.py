"""
run_all.py — Runs the full replication.

Executes the numbered analysis scripts (01-08) in order, then the figure
scripts, and reproduces all tables, figures, and numbers reported in the paper
from the input data in data/. Run from any directory:

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

# Analysis steps (numbered in run order), then one script per figure
STEPS = [
    "01_stage1_kruskal_wallis.py",
    "02_stage2_t_tests.py",
    "03_stage3_benchmark_correlations.py",
    "04_stage3_model_market_correlations.py",
    "05_stage3_pearson_vs_spearman.py",
    "06_compression_factors.py",
    "07_value_factors.py",
    "08_tables.py",
    "figure_04_annual_prices.py",
    "figure_05_price_duration_curves.py",
    "figure_06_temporal_profiles.py",
    "figure_07_compression.py",
    "figure_08_benchmark_stability.py",
    "figure_09_alignment_heatmap.py",
    "figure_C01_country_clusters.py",
    "figure_C02_price_distribution.py",
    "figure_C03_scenario_correlations.py",
    "figure_C04_model_year_correlations.py",
    "figure_C05_market_year_correlations.py",
    "figure_C06-C09_alignment_by_dimension.py",
    "figure_C10_pearson_vs_spearman.py",
]


def run(script: str, i: int, n: int) -> None:
    print(f"\n{'=' * 70}")
    print(f"  [{i}/{n}] {script}")
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
    for i, script in enumerate(STEPS, start=1):
        run(script, i, len(STEPS))

    print(f"\n{'=' * 70}")
    print(f"  All steps completed in {(time.time() - t0) / 60:.1f} min.")
    print("  Figures:              results/figures/")
    print("  Tables and values:    results/tables/")
    print("  Intermediate results: results/intermediate/")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
