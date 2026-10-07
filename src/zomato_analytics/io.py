"""Loading raw data and reference (seed) tables with explicit contracts."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from . import config
from .schema import RAW_COLUMNS

log = logging.getLogger(__name__)


class SchemaError(ValueError):
    """Raised when an input file does not meet the expected column contract."""


def read_raw(path: str | Path = config.DEFAULT_RAW_FILE) -> pd.DataFrame:
    """Read the Kaggle ``zomato.csv`` file.

    The published file is not valid UTF-8, so we try UTF-8 first and fall back to
    latin-1 (which never fails to decode). All columns are read as strings so that
    type coercion happens in one audited place (``cleaning``), not silently here.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Download zomato.csv from "
            "https://www.kaggle.com/datasets/shrutimehta/zomato-restaurants-data "
            "into data/raw/, or run `zomato-analytics demo` to use synthetic data."
        )
    for encoding in ("utf-8", "latin-1"):
        try:
            df = pd.read_csv(path, encoding=encoding, dtype=str, keep_default_na=False)
            log.info("Read %s rows from %s (encoding=%s)", len(df), path.name, encoding)
            break
        except UnicodeDecodeError:
            log.info("%s is not valid %s, retrying", path.name, encoding)
    validate_raw_columns(df)
    return df


def validate_raw_columns(df: pd.DataFrame) -> None:
    """Fail fast if the file does not look like the Zomato extract."""
    missing = [c for c in RAW_COLUMNS if c not in df.columns]
    if missing:
        raise SchemaError(f"Input is missing required columns: {missing}")
    extra = [c for c in df.columns if c not in RAW_COLUMNS]
    if extra:
        log.warning("Ignoring unexpected columns: %s", extra)


def read_country_seed(path: str | Path = config.COUNTRY_SEED) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"country_code": "int64"})


def read_fx_seed(path: str | Path = config.FX_SEED) -> pd.DataFrame:
    return pd.read_csv(path)
