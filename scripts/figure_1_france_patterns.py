"""
figure_1_france_patterns.py — data for Figure 1.

Figure 1 is drawn with TikZ/pgfplots directly in the manuscript; this script
computes its coordinates from the ENTSO-E data. For France, 2018–2025, the
hourly day-ahead prices are pooled across all years and the median price of
each hour-of-day, day-of-week, and month-of-year group is taken. The dashed
reference line is the median of all hourly prices in the sample.

Input : data/ENTSOE_day_ahead_prices.csv
Output: results/figures/Figure_1_data.csv  (dimension, group, median_price)
        results/tables/values_figure_1_france_patterns.csv
"""

import pandas as pd

from config import ENTSOE_PRICES_FILE, ENTSOE_YEARS, PLOTS_DIR
from outputs import ValueLog

COUNTRY = "FR"
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main():
    log = ValueLog("figure_1_france_patterns")
    prices = pd.read_csv(ENTSOE_PRICES_FILE, index_col=0, parse_dates=True)[COUNTRY].dropna()
    prices = prices[prices.index.year.isin(ENTSOE_YEARS)]

    groupings = {
        "hour":    (prices.index.hour, list(range(24))),
        "weekday": (prices.index.weekday, WEEKDAYS),
        "month":   (prices.index.month, MONTHS),
    }
    rows = []
    for dim, (keys, labels) in groupings.items():
        medians = prices.groupby(keys).median()
        for (group, value), label in zip(medians.items(), labels):
            rows.append({"dimension": dim, "group": label, "median_price": round(value, 1)})
            log.add("Figure 1", f"{dim} {label}", value)
    overall = prices.median()
    rows.append({"dimension": "overall", "group": "all hours", "median_price": round(overall, 1)})
    log.add("Figure 1", "overall median", overall)

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    out = PLOTS_DIR / "Figure_1_data.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Saved Figure 1 coordinates -> {out}")
    log.save()


if __name__ == "__main__":
    main()
