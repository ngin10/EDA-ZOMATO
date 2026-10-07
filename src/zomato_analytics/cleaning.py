"""Turn the raw extract into an analysis-ready table.

Each step is a small pure function so it can be unit-tested and so the order of
operations is visible in :func:`clean`. Nothing is dropped silently: every row
removed or value nulled is counted in the returned :class:`CleaningLog`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import io
from .config import DEFAULT_CONFIG, AnalysisConfig
from .schema import NUMERIC_COLUMNS, RAW_TO_CLEAN, TEXT_COLUMNS, YES_NO_COLUMNS

# Characters that only appear when UTF-8 text has been mis-decoded as latin-1/cp1252.
_MOJIBAKE = re.compile(r"[ÃÂÛ±Ó¡¼©¤]")


@dataclass
class CleaningLog:
    """Audit trail of what cleaning changed, surfaced in the data-quality report."""

    rows_in: int = 0
    rows_out: int = 0
    steps: list[dict] = field(default_factory=list)

    def record(self, step: str, affected: int, note: str) -> None:
        self.steps.append({"step": step, "rows_affected": int(affected), "note": note})

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.steps, columns=["step", "rows_affected", "note"])


def fix_mojibake(text: str) -> str:
    """Repair UTF-8 text that was decoded as latin-1 where that is reversible."""
    if not isinstance(text, str) or not _MOJIBAKE.search(text):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def has_encoding_artefact(text: object) -> bool:
    return isinstance(text, str) and bool(_MOJIBAKE.search(text))


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df[list(RAW_TO_CLEAN)].rename(columns=RAW_TO_CLEAN)


def normalise_text(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    df = df.copy()
    repaired = 0
    for col in TEXT_COLUMNS:
        stripped = df[col].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
        fixed = stripped.map(fix_mojibake, na_action="ignore")
        repaired += int((fixed != stripped).fillna(False).sum())
        df[col] = fixed.replace("", pd.NA)
    log.record(
        "normalise_text", repaired, "Whitespace trimmed; reversible encoding errors repaired"
    )
    df["has_encoding_issue"] = (
        df[["restaurant_name", "city", "address", "locality"]]
        .map(has_encoding_artefact)
        .any(axis=1)
    )
    log.record(
        "flag_encoding_issue",
        df["has_encoding_issue"].sum(),
        "Irreversibly garbled text flagged (kept, not dropped)",
    )
    return df


def coerce_types(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    df = df.copy()
    for col in NUMERIC_COLUMNS:
        before = df[col].notna() & (df[col].astype("string").str.strip() != "")
        df[col] = pd.to_numeric(df[col], errors="coerce")
        failed = int((before & df[col].isna()).sum())
        if failed:
            log.record(f"coerce_{col}", failed, "Non-numeric values set to null")
    for col in ("restaurant_id", "country_code", "price_range", "votes"):
        df[col] = df[col].astype("Int64")
    for col in YES_NO_COLUMNS:
        df[col] = df[col].astype("string").str.strip().str.lower().map({"yes": True, "no": False})
        df[col] = df[col].astype("boolean")
    return df


def drop_duplicates(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    exact = df.duplicated()
    df = df[~exact]
    by_id = df.duplicated(subset="restaurant_id", keep="first")
    df = df[~by_id]
    removed = int(exact.sum() + by_id.sum())
    log.record("drop_duplicates", removed, "Exact and restaurant_id duplicates")
    return df.reset_index(drop=True)


def handle_ratings(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """A 0.0 rating means *not yet rated*, not *terrible*. Treating it as a score
    drags every average down (the original notebook's mean rating was biased this
    way), so we null it and keep an explicit ``is_rated`` flag."""
    df = df.copy()
    unrated = (df["aggregate_rating"] == 0) | (df["rating_text"] == "Not rated")
    df["is_rated"] = ~unrated
    df.loc[unrated, "aggregate_rating"] = np.nan
    log.record("null_unrated", unrated.sum(), "0.0 / 'Not rated' scores set to null")
    return df


def handle_costs(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    df = df.copy()
    zero = df["cost_for_two_local"] <= 0
    df.loc[zero, "cost_for_two_local"] = np.nan
    log.record("null_zero_cost", zero.sum(), "Cost for two of 0 is missing data, not free")
    return df


def handle_coordinates(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    df = df.copy()
    null_island = (df["latitude"] == 0) & (df["longitude"] == 0)
    out_of_range = ~df["latitude"].between(-90, 90) | ~df["longitude"].between(-180, 180)
    bad = null_island | out_of_range
    df.loc[bad, ["latitude", "longitude"]] = np.nan
    log.record("null_bad_coordinates", bad.sum(), "(0,0) or out-of-range lat/long set to null")
    return df


def fill_cuisines(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    df = df.copy()
    missing = df["cuisines"].isna()
    df["cuisines"] = df["cuisines"].fillna("Unknown")
    log.record("fill_cuisines", missing.sum(), "Missing cuisines labelled 'Unknown'")
    return df


def attach_country_and_currency(
    df: pd.DataFrame,
    countries: pd.DataFrame,
    fx: pd.DataFrame,
    log: CleaningLog,
) -> pd.DataFrame:
    """Derive the ISO currency from the country, not the free-text label.

    The raw ``Currency`` column is unreliable (e.g. Philippine restaurants are
    labelled "Botswana Pula(P)" and four different countries share "Dollar($)").
    Country code is the trustworthy key, so currency is derived from it and the
    label is kept only for audit.
    """
    df = df.merge(countries, on="country_code", how="left", validate="many_to_one")
    unknown = df["country"].isna()
    df["country"] = df["country"].fillna("Unknown")
    log.record("unknown_country_code", unknown.sum(), "Country code not in reference table")

    df = df.merge(fx[["iso_currency", "gbp_per_unit"]], on="iso_currency", how="left")
    df["cost_for_two_gbp"] = (df["cost_for_two_local"] * df["gbp_per_unit"]).round(2)
    no_rate = df["cost_for_two_local"].notna() & df["gbp_per_unit"].isna()
    log.record("missing_fx_rate", no_rate.sum(), "No FX rate: GBP cost left null")
    return df.drop(columns="gbp_per_unit")


def flag_cost_outliers(df: pd.DataFrame, cfg: AnalysisConfig, log: CleaningLog) -> pd.DataFrame:
    """Robust (median/MAD) outlier flag on log cost, computed within country so a
    pricey Jakarta restaurant is not judged against Indian street food."""
    df = df.copy()
    log_cost = np.log1p(df["cost_for_two_gbp"].astype(float))
    grp = log_cost.groupby(df["country_code"])
    med = grp.transform("median")
    mad = grp.transform(lambda s: (s - s.median()).abs().median())
    robust_z = 0.6745 * (log_cost - med) / mad.replace(0, np.nan)
    df["is_cost_outlier"] = (robust_z.abs() > cfg.outlier_mad_threshold).fillna(False)
    log.record(
        "flag_cost_outliers",
        df["is_cost_outlier"].sum(),
        f"|robust z| > {cfg.outlier_mad_threshold} within country (flagged, not dropped)",
    )
    return df


def clean(
    raw: pd.DataFrame,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
    countries: pd.DataFrame | None = None,
    fx: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, CleaningLog]:
    """Run the full cleaning sequence and return ``(clean_df, log)``."""
    countries = io.read_country_seed() if countries is None else countries
    fx = io.read_fx_seed() if fx is None else fx
    log = CleaningLog(rows_in=len(raw))

    df = rename_columns(raw)
    df = normalise_text(df, log)
    df = coerce_types(df, log)
    df = drop_duplicates(df, log)
    df = handle_ratings(df, log)
    df = handle_costs(df, log)
    df = handle_coordinates(df, log)
    df = fill_cuisines(df, log)
    df = attach_country_and_currency(df, countries, fx, log)
    df = flag_cost_outliers(df, cfg, log)

    # Constant column (every value "No" in the published file) carries no information.
    col = df["switch_to_order_menu"].dropna()
    if col.empty or (col == col.iloc[0]).all():
        df = df.drop(columns="switch_to_order_menu")
        log.record("drop_constant_column", 0, "switch_to_order_menu has a single value")

    log.rows_out = len(df)
    return df, log
