"""
config.py — Central parameter file for all analysis scripts.

Countries, years, scenarios, regions, and repository paths are defined here.
All scripts import their configuration from this file.
"""

from pathlib import Path

# ── Repository paths ──────────────────────────────────────────────────────────
BASE        = Path(__file__).resolve().parent.parent
DATA_DIR    = BASE / "data"
RESULTS_DIR = BASE / "results" / "intermediate"   # intermediate results
PLOTS_DIR   = BASE / "results" / "figures"        # figures (paper numbering)
TABLES_DIR  = BASE / "results" / "tables"         # tables and in-text values

ENTSOE_PRICES_FILE  = DATA_DIR / "ENTSOE_day_ahead_prices.csv"
GENESYS_PRICES_FILE = DATA_DIR / "GENeSYS_MOD_prices.csv"

# ── Countries ─────────────────────────────────────────────────────────────────
# 22 European countries
COUNTRIES = [
    "AT", "BE", "BG", "CH", "CZ", "DE", "EE", "ES", "FI", "FR",
    "GR", "HR", "HU", "IE", "LT", "LV", "NL", "PL", "PT", "RO", "SI", "SK",
]

# ── Years ─────────────────────────────────────────────────────────────────────
# ENTSO-E market data (hourly day-ahead prices)
ENTSOE_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

# GENeSYS-MOD model runs (snapshot years)
GENESYS_YEARS = [2018, 2025, 2030]

# Union of both year sets (for scripts that combine both sources)
ANALYSIS_YEARS = sorted(set(ENTSOE_YEARS) | set(GENESYS_YEARS))

# ── Scenarios ─────────────────────────────────────────────────────────────────
SCENARIOS = ["GoRES", "NECPEssentials", "REPowerEU++", "Trinity"]

# ── Country clusters (Table 4, Figure C.1; used in Figures 7, 9, C.6–C.9 and
#    Table C.6) ─────────────────────────────────────────────────────────────────
CLUSTERS = {
    "Iberian":    ["ES", "PT"],
    "Baltic":     ["EE", "LT", "LV"],
    "South-East": ["BG", "HR", "HU", "SI"],
    "Core-East":  ["AT", "CZ", "DE", "SK"],
    "Core-West":  ["BE", "CH", "FR", "NL"],
    "FI":         ["FI"],
    "GR":         ["GR"],
    "RO":         ["RO"],
    "IE":         ["IE"],
    "PL":         ["PL"],
}
