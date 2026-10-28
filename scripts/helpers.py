"""
helpers.py — Helper functions for saving tables and the numbers quoted in the text.

Every script that produces a number quoted in the paper records it with a
ValueLog. The log is written to results/tables/values_<script>.csv with columns

    script, exhibit, item, value

where `exhibit` names the table, figure, or section of the paper (e.g.
"Table 5", "Section 3.3") and `item` identifies the quantity, so that every
number quoted in the text can be traced to its computation.
"""

import pandas as pd

from config import TABLES_DIR


class ValueLog:
    """Collect (exhibit, item, value) records for one script."""

    def __init__(self, script: str):
        self.script = script
        self.rows = []

    def add(self, exhibit: str, item: str, value) -> None:
        self.rows.append({"exhibit": exhibit, "item": item, "value": float(value)})

    def save(self) -> None:
        TABLES_DIR.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(self.rows, columns=["exhibit", "item", "value"])
        df.insert(0, "script", self.script)
        out = TABLES_DIR / f"values_{self.script}.csv"
        df.to_csv(out, index=False)
        print(f"Saved {len(df)} reported values -> {out.relative_to(TABLES_DIR.parent.parent)}")


def save_table(df: pd.DataFrame, name: str, index: bool = True) -> None:
    """Write a paper table as CSV to results/tables/<name>.csv."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    out = TABLES_DIR / f"{name}.csv"
    df.to_csv(out, index=index)
    print(f"Saved {name} -> {out.relative_to(TABLES_DIR.parent.parent)}")
