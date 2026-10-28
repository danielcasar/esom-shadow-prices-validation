"""
prepare_vre_generation.py — build the two small solar/wind input files used by
compute_value_factors.py (Section 4.2) from the full source files.

This is a data-preparation step that was run once; run_all.py does not call it
because the full source files are too large to ship (139 MB and 1.08 GB). The
two extracts it writes are included in data/.

Usage:
    python prepare_vre_generation.py <ENTSOE_generation_mix.csv> <output_production.csv>

Inputs
------
ENTSOE_generation_mix.csv
    Hourly actual generation per production type (MW, hourly means, UTC) from
    the ENTSO-E Transparency Platform [16.1.B&C], 2018–2025, one column per
    <country>_<production type> (aggregated generation only).
output_production.csv
    GENeSYS-MOD EU-EnVis-2060 v1.2.0 production output (PJ per timeslice).

Outputs
-------
data/ENTSOE_vre_generation_2025.csv
    timestamp (UTC), <country>_solar, <country>_wind (onshore + offshore), MW.
data/GENeSYS_MOD_vre_production_2025.csv
    Model Version, PathwayScenario, Region, carrier (solar/wind), Timeslice,
    production (PJ, summed over all PV / wind technologies of the power sector).
"""

import sys

import numpy as np
import pandas as pd

from config import COUNTRIES, DATA_DIR

YEAR = 2025


def entsoe_extract(path: str) -> None:
    gen = pd.read_csv(path, index_col=0, parse_dates=True)
    gen = gen[gen.index.year == YEAR]
    out = pd.DataFrame(index=gen.index)
    for c in COUNTRIES:
        solar = [k for k in gen.columns if k == f"{c}_Solar"]
        wind = [k for k in gen.columns if k in (f"{c}_Wind_Onshore", f"{c}_Wind_Offshore")]
        if solar:
            out[f"{c}_solar"] = gen[solar].sum(axis=1, min_count=1)
        if wind:
            out[f"{c}_wind"] = gen[wind].sum(axis=1, min_count=1)
    target = DATA_DIR / "ENTSOE_vre_generation_2025.csv"
    out.to_csv(target)
    print(f"Saved {target} ({len(out)} hours, {out.shape[1]} series)")


def genesys_extract(path: str) -> None:
    cols = ["Model Version", "PathwayScenario", "Region", "Sector", "Technology",
            "Type", "Timeslice", "Year", "Value "]
    parts = []
    for chunk in pd.read_csv(path, usecols=cols, chunksize=1_000_000):
        chunk = chunk[(chunk["Year"] == YEAR) & (chunk["Type"] == "Production")
                      & (chunk["Sector"] == "Power") & chunk["Region"].isin(COUNTRIES)]
        chunk = chunk[chunk["Technology"].str.contains("PV|Wind", case=False, na=False)]
        if len(chunk):
            chunk = chunk.assign(carrier=np.where(
                chunk["Technology"].str.contains("PV", case=False), "solar", "wind"))
            parts.append(chunk)
    prod = pd.concat(parts)
    print("Model versions / scenarios in extract:",
          prod[["Model Version", "PathwayScenario"]].drop_duplicates().values.tolist())
    prod = (prod.groupby(["Model Version", "PathwayScenario", "Region", "carrier", "Timeslice"])
                ["Value "].sum().rename("production").reset_index())
    target = DATA_DIR / "GENeSYS_MOD_vre_production_2025.csv"
    prod.to_csv(target, index=False)
    print(f"Saved {target} ({len(prod)} rows)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    entsoe_extract(sys.argv[1])
    genesys_extract(sys.argv[2])
