"""Data-quality checks.

Two layers:

* ``profile_raw`` describes problems found in the source file (what a data owner
  needs to fix upstream).
* ``assert_clean`` enforces post-conditions on the cleaned table; the pipeline
  stops if any fails, so a broken extract can never silently reach a dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .schema import RAW_COLUMNS, VALID_RANGES


@dataclass
class Check:
    name: str
    severity: str  # "error" blocks the pipeline, "warning" is reported only
    failing_rows: int
    total_rows: int
    detail: str

    @property
    def passed(self) -> bool:
        return self.failing_rows == 0

    def as_dict(self) -> dict:
        pct = 100 * self.failing_rows / self.total_rows if self.total_rows else 0.0
        return {
            "check": self.name,
            "severity": self.severity,
            "status": "PASS" if self.passed else "FAIL",
            "failing_rows": self.failing_rows,
            "failing_pct": round(pct, 2),
            "detail": self.detail,
        }


class DataQualityError(RuntimeError):
    pass


def profile_raw(raw: pd.DataFrame) -> pd.DataFrame:
    """Profile the untouched source file. Everything is a warning here: we report
    on the source, and cleaning decides what to do about each issue."""
    n = len(raw)
    checks: list[Check] = []

    def num(col: str) -> pd.Series:
        return pd.to_numeric(raw[col], errors="coerce")

    checks.append(
        Check(
            "duplicate_restaurant_id",
            "warning",
            int(raw["Restaurant ID"].duplicated().sum()),
            n,
            "Restaurant ID should be unique",
        )
    )
    for col in RAW_COLUMNS:
        blanks = int((raw[col].astype(str).str.strip() == "").sum())
        if blanks:
            checks.append(Check(f"blank_{col}", "warning", blanks, n, f"Blank values in '{col}'"))

    checks.append(
        Check(
            "zero_rating_means_unrated",
            "warning",
            int((num("Aggregate rating") == 0).sum()),
            n,
            "Rating 0.0 used as a sentinel for 'Not rated'",
        )
    )
    checks.append(
        Check(
            "zero_cost_for_two",
            "warning",
            int((num("Average Cost for two") == 0).sum()),
            n,
            "Cost for two recorded as 0",
        )
    )
    lat, lon = num("Latitude"), num("Longitude")
    checks.append(
        Check(
            "null_island_coordinates",
            "warning",
            int(((lat == 0) & (lon == 0)).sum()),
            n,
            "Latitude and longitude both 0",
        )
    )
    labels_per_country = raw.groupby("Country Code")["Currency"].nunique()
    checks.append(
        Check(
            "currency_label_inconsistent",
            "warning",
            int((labels_per_country > 1).sum()),
            int(labels_per_country.size),
            "Countries with more than one currency label",
        )
    )
    shared = raw.groupby("Currency")["Country Code"].nunique()
    checks.append(
        Check(
            "currency_label_ambiguous",
            "warning",
            int((shared > 1).sum()),
            int(shared.size),
            "Currency labels shared by several countries (e.g. 'Dollar($)')",
        )
    )
    checks.append(
        Check(
            "garbled_text",
            "warning",
            int(
                raw["City"].str.contains(r"[ÃÂÛ±Ó]", regex=True, na=False).sum()
                + raw["Restaurant Name"].str.contains(r"[ÃÂÛ±Ó]", regex=True, na=False).sum()
            ),
            n,
            "City / name values with encoding artefacts",
        )
    )
    for col in ("Switch to order menu",):
        if (raw[col] == raw[col].iloc[0]).all():
            checks.append(Check(f"constant_{col}", "warning", n, n, "Column holds a single value"))
    return pd.DataFrame([c.as_dict() for c in checks])


def assert_clean(df: pd.DataFrame, raise_on_error: bool = True) -> pd.DataFrame:
    """Post-conditions every downstream consumer relies on."""
    n = len(df)
    checks = [
        Check(
            "restaurant_id_unique",
            "error",
            int(df["restaurant_id"].duplicated().sum()),
            n,
            "Primary key must be unique",
        ),
        Check(
            "restaurant_id_not_null",
            "error",
            int(df["restaurant_id"].isna().sum()),
            n,
            "Primary key must be present",
        ),
        Check(
            "country_resolved",
            "error",
            int((df["country"] == "Unknown").sum()),
            n,
            "Every country code maps to the reference table",
        ),
        Check(
            "rated_flag_consistent",
            "error",
            int(
                (df["is_rated"] & df["aggregate_rating"].isna()).sum()
                + (~df["is_rated"] & df["aggregate_rating"].notna()).sum()
            ),
            n,
            "is_rated agrees with aggregate_rating",
        ),
        Check(
            "gbp_cost_present_when_local_present",
            "error",
            int((df["cost_for_two_local"].notna() & df["cost_for_two_gbp"].isna()).sum()),
            n,
            "Every local cost converts to GBP",
        ),
    ]
    for col, (lo, hi) in VALID_RANGES.items():
        s = df[col].astype(float)
        bad = int((s.notna() & ~s.between(lo, hi)).sum())
        checks.append(Check(f"{col}_in_range", "error", bad, n, f"{col} within [{lo}, {hi}]"))
    checks.append(
        Check(
            "cost_outliers",
            "warning",
            int(df["is_cost_outlier"].sum()),
            n,
            "Flagged by within-country robust z-score; kept but excluded from cost medians",
        )
    )
    checks.append(
        Check(
            "encoding_issues",
            "warning",
            int(df["has_encoding_issue"].sum()),
            n,
            "Text that could not be repaired automatically",
        )
    )
    report = pd.DataFrame([c.as_dict() for c in checks])
    failed = report[(report["severity"] == "error") & (report["status"] == "FAIL")]
    if raise_on_error and not failed.empty:
        raise DataQualityError(f"Clean-data checks failed:\n{failed.to_string(index=False)}")
    return report
