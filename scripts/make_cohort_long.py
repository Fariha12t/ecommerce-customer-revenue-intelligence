"""Create reports/generated/cohort_retention_long.csv for Power BI.

Turns the wide cohort table (one column per month) into one row per
cohort_month and period, so Power BI needs no unpivot step.
"""

from pathlib import Path

import pandas as pd

SRC = Path("reports/generated/cohort_retention.csv")
DST = Path("reports/generated/cohort_retention_long.csv")


def main() -> None:
    wide = pd.read_csv(SRC, dtype={"cohort_month": str})
    long = wide.melt(id_vars="cohort_month", var_name="period", value_name="retention")
    long = long.dropna(subset=["retention"])
    long["period"] = long["period"].astype(int)
    long = long.sort_values(["cohort_month", "period"]).reset_index(drop=True)
    long.to_csv(DST, index=False)
    print(f"{DST}: {len(long)} rows, cohorts {long['cohort_month'].nunique()}")


if __name__ == "__main__":
    main()
