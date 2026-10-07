"""Derived analytical fields built on top of the cleaned table."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DEFAULT_CONFIG, AnalysisConfig


def split_cuisines(cuisines: pd.Series) -> pd.Series:
    """'North Indian, Chinese' -> ['North Indian', 'Chinese'] (deduplicated, order kept)."""
    return cuisines.fillna("Unknown").map(
        lambda s: (
            list(dict.fromkeys(c.strip() for c in str(s).split(",") if c.strip())) or ["Unknown"]
        )
    )


def bayesian_rating(
    rating: pd.Series, votes: pd.Series, prior_mean: float, prior_votes: int
) -> pd.Series:
    """Shrink each rating towards the global mean in proportion to its evidence.

    WR = (v / (v + m)) * R + (m / (v + m)) * C  -- the IMDb top-250 formula.
    A 4.9 from 6 votes should not outrank a 4.6 from 3,000 votes.
    """
    v = votes.astype(float)
    m = float(prior_votes)
    return (v / (v + m)) * rating + (m / (v + m)) * prior_mean


def add_features(df: pd.DataFrame, cfg: AnalysisConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    df = df.copy()
    cuisine_lists = split_cuisines(df["cuisines"])
    df["primary_cuisine"] = cuisine_lists.str[0]
    df["n_cuisines"] = cuisine_lists.str.len().astype("Int64")
    df["price_band"] = df["price_range"].map(cfg.price_band_labels).astype("string")
    df["log_votes"] = np.log1p(df["votes"].astype(float))

    rated = df["is_rated"]
    prior_mean = float(df.loc[rated, "aggregate_rating"].mean())
    df["weighted_rating"] = bayesian_rating(
        df["aggregate_rating"], df["votes"], prior_mean, cfg.bayes_prior_votes
    ).round(3)

    df["is_uk"] = df["country"].eq("United Kingdom")
    df["market"] = np.where(
        df["country"].eq("India"), "India", np.where(df["is_uk"], "United Kingdom", "Other")
    )
    return df


def explode_cuisines(df: pd.DataFrame) -> pd.DataFrame:
    """Bridge table: one row per (restaurant, cuisine). Needed because cuisine is a
    multi-valued field; counting the raw string treats 'Chinese, Thai' and
    'Thai, Chinese' as different cuisines."""
    bridge = df[["restaurant_id"]].assign(cuisine=split_cuisines(df["cuisines"]))
    bridge = bridge.explode("cuisine", ignore_index=True)
    bridge["is_primary"] = ~bridge.duplicated(subset="restaurant_id", keep="first")
    return bridge
