"""
config.py — Settings shared by all scripts: countries, years, scenarios, clusters, paths, and the GENeSYS-MOD calendar.

All scripts import their configuration from this file.
"""

from pathlib import Path

import pandas as pd

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

# ── GENeSYS-MOD calendar ──────────────────────────────────────────────────────
# GENeSYS-MOD hours (Hour 1-8760) carry no dates. In every model year they
# follow the same 365-day calendar: Hour 1 is 00:00 on 1 January, and the
# weekly price pattern places Saturday and Sunday on days 5 and 6 of the year,
# i.e. 1 January is a Tuesday. Hour-of-day, day-of-week, month and season of
# the model prices are therefore taken from one non-leap year that starts on a
# Tuesday (2030), not from the calendar of each model year.
MODEL_CALENDAR_START = "2030-01-01"


def model_calendar(n_hours: int = 8760) -> pd.DatetimeIndex:
    """Timestamps of GENeSYS-MOD Hour 1 ... n_hours (used for calendar groups only)."""
    return pd.date_range(MODEL_CALENDAR_START, periods=n_hours, freq="h")

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
