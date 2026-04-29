"""
config.py — Central parameter file for all analysis scripts.

Countries, years, scenarios, and regions are defined here.
All scripts import their configuration from this file.
"""

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

# ── Geographic regions (CCR-based; see Table 2 in the paper) ─────────────────
REGIONS = {
    "Core":              ["AT", "BE", "CZ", "DE", "HR", "HU", "NL", "SI", "SK"],
    "South-West Europe": ["ES", "FR", "PT"],
    "Baltic":            ["EE", "FI", "LT", "LV", "PL"],
    "South-East Europe": ["BG", "GR", "RO"],
    "Unassigned":        ["CH", "IE"],
}

# ── Country clusters for Pearson benchmark figures (Figures A6–A9) ─────────────
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
