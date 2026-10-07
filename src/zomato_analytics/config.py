"""Project-wide paths and analytical constants.

Every threshold used in the analysis lives here so that a reviewer can see (and
challenge) the assumptions in one place rather than hunting through notebooks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SEEDS_DIR = DATA_DIR / "seeds"
PROCESSED_DIR = DATA_DIR / "processed"
SQL_DIR = PROJECT_ROOT / "sql"
REPORTS_DIR = PROJECT_ROOT / "reports"

DEFAULT_RAW_FILE = RAW_DIR / "zomato.csv"
COUNTRY_SEED = SEEDS_DIR / "country_codes.csv"
FX_SEED = SEEDS_DIR / "fx_rates_to_gbp.csv"

UK_COUNTRY_CODE = 215


@dataclass(frozen=True)
class AnalysisConfig:
    """Tunable thresholds. Defaults are documented in docs/methodology.md."""

    # A group needs at least this many restaurants before it appears in a league table.
    min_group_size: int = 10
    # Prior strength (in votes) for the Bayesian-weighted rating. Restaurants with
    # far fewer votes than this are pulled towards the global mean.
    bayes_prior_votes: int = 50
    # Cost-for-two above this many robust z-scores (MAD) within a country is flagged.
    outlier_mad_threshold: float = 5.0
    # Significance level for hypothesis tests.
    alpha: float = 0.05
    # Number of rows to keep in "top N" outputs.
    top_n: int = 10
    price_band_labels: dict[int, str] = field(
        default_factory=lambda: {1: "Budget", 2: "Mid-range", 3: "Premium", 4: "Luxury"}
    )


DEFAULT_CONFIG = AnalysisConfig()
