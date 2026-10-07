"""Business KPIs. Each function answers one stakeholder question and returns a
tidy DataFrame that can go straight into a report, Excel tab or BI tool.

Conventions:
* Cost KPIs use GBP and exclude flagged cost outliers; medians, not means,
  because restaurant prices are heavily right-skewed.
* Rating KPIs use rated restaurants only (0.0 means "not rated").
* Groups smaller than ``cfg.min_group_size`` are excluded from rankings.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DEFAULT_CONFIG, AnalysisConfig
from .features import explode_cuisines


def _cost(df: pd.DataFrame) -> pd.Series:
    return df["cost_for_two_gbp"].where(~df["is_cost_outlier"])


def _summary(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    d = df.assign(_cost=_cost(df), _rating=df["aggregate_rating"])
    out = d.groupby(by, observed=True).agg(
        restaurants=("restaurant_id", "size"),
        rated_restaurants=("is_rated", "sum"),
        median_cost_for_two_gbp=("_cost", "median"),
        mean_rating=("_rating", "mean"),
        median_votes=("votes", "median"),
        total_votes=("votes", "sum"),
        pct_online_delivery=("has_online_delivery", "mean"),
        pct_table_booking=("has_table_booking", "mean"),
    )
    for col in ("pct_online_delivery", "pct_table_booking"):
        out[col] = (100 * out[col].astype(float)).round(1)
    out["mean_rating"] = out["mean_rating"].round(2)
    out["median_cost_for_two_gbp"] = out["median_cost_for_two_gbp"].round(2)
    return out.reset_index()


def headline_kpis(df: pd.DataFrame) -> dict[str, float]:
    rated = df["is_rated"]
    return {
        "restaurants": int(len(df)),
        "countries": int(df["country"].nunique()),
        "cities": int(df["city"].nunique()),
        "pct_rated": round(100 * rated.mean(), 1),
        "mean_rating_rated": round(float(df.loc[rated, "aggregate_rating"].mean()), 2),
        "median_cost_for_two_gbp": round(float(_cost(df).median()), 2),
        "pct_online_delivery": round(100 * float(df["has_online_delivery"].mean()), 1),
        "pct_table_booking": round(100 * float(df["has_table_booking"].mean()), 1),
        "total_votes": int(df["votes"].sum()),
    }


def market_overview(df: pd.DataFrame) -> pd.DataFrame:
    """Q: Where is the platform's footprint, and how do markets compare in GBP?"""
    out = _summary(df, ["country", "region"])
    out["share_of_restaurants_pct"] = (100 * out["restaurants"] / out["restaurants"].sum()).round(2)
    return out.sort_values("restaurants", ascending=False, ignore_index=True)


def city_league_table(df: pd.DataFrame, cfg: AnalysisConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    """Q: Which cities have the best-rated restaurant scenes (with enough evidence)?"""
    out = _summary(df, ["country", "city"])
    out = out[out["rated_restaurants"] >= cfg.min_group_size]
    wr = df.groupby("city")["weighted_rating"].mean().round(3).rename("mean_weighted_rating")
    out = out.merge(wr, on="city", how="left")
    out["rank"] = out["mean_weighted_rating"].rank(ascending=False, method="min").astype(int)
    return out.sort_values("rank", ignore_index=True)


def cuisine_performance(df: pd.DataFrame, cfg: AnalysisConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    """Q: Which cuisines are most common, most popular and best rated?

    Uses the exploded bridge table, so a restaurant serving three cuisines counts
    once towards each.
    """
    bridge = explode_cuisines(df).merge(
        df[
            [
                "restaurant_id",
                "aggregate_rating",
                "weighted_rating",
                "votes",
                "is_rated",
                "cost_for_two_gbp",
                "is_cost_outlier",
            ]
        ],
        on="restaurant_id",
    )
    bridge["_cost"] = _cost(bridge)
    out = bridge.groupby("cuisine").agg(
        restaurants=("restaurant_id", "nunique"),
        rated_restaurants=("is_rated", "sum"),
        mean_rating=("aggregate_rating", "mean"),
        mean_weighted_rating=("weighted_rating", "mean"),
        total_votes=("votes", "sum"),
        median_cost_for_two_gbp=("_cost", "median"),
    )
    out = out[out["rated_restaurants"] >= cfg.min_group_size].copy()
    out["share_of_votes_pct"] = (100 * out["total_votes"] / out["total_votes"].sum()).round(2)
    out["votes_per_restaurant"] = (out["total_votes"] / out["restaurants"]).round(1)
    out = out.round({"mean_rating": 2, "mean_weighted_rating": 3, "median_cost_for_two_gbp": 2})
    return out.sort_values("restaurants", ascending=False).reset_index()


def price_band_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Q: Does paying more buy a better-rated experience?"""
    out = _summary(df, ["price_range", "price_band"])
    return out.sort_values("price_range", ignore_index=True)


def service_impact(df: pd.DataFrame) -> pd.DataFrame:
    """Q: Do restaurants offering online delivery / table booking rate higher?

    Reported overall and within price band, because table booking is far more
    common at expensive restaurants -- the headline gap is partly a price effect.
    """
    rated = df[df["is_rated"]]
    frames = []
    for feature in ("has_online_delivery", "has_table_booking"):
        overall = rated.groupby(feature)["aggregate_rating"].agg(["mean", "size"])
        overall["price_band"] = "All"
        by_band = rated.groupby(["price_band", feature])["aggregate_rating"].agg(["mean", "size"])
        by_band = by_band.reset_index(level="price_band")
        both = pd.concat([overall, by_band]).reset_index(names="offers_service")
        both.insert(0, "service", feature.removeprefix("has_"))
        frames.append(both)
    out = pd.concat(frames, ignore_index=True)
    wide = out.pivot_table(
        index=["service", "price_band"], columns="offers_service", values=["mean", "size"]
    )
    wide.columns = [
        f"{'rating' if m == 'mean' else 'n'}_{'with' if f else 'without'}" for m, f in wide.columns
    ]
    wide = wide.reset_index()
    wide["rating_uplift"] = (wide["rating_with"] - wide["rating_without"]).round(2)
    return wide.round({"rating_with": 2, "rating_without": 2})


def uk_benchmark(df: pd.DataFrame) -> pd.DataFrame:
    """Q: How does the UK estate compare with the rest of the platform?"""
    out = _summary(df, ["market"])
    order = {"United Kingdom": 0, "India": 1, "Other": 2}
    return out.sort_values("market", key=lambda s: s.map(order), ignore_index=True)


def uk_city_summary(df: pd.DataFrame) -> pd.DataFrame:
    uk = df[df["is_uk"]]
    if uk.empty:
        return pd.DataFrame()
    return _summary(uk, ["city"]).sort_values("restaurants", ascending=False, ignore_index=True)


def opportunity_matrix(df: pd.DataFrame, cfg: AnalysisConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    """Q: Where is demand high relative to supply? (white-space for acquisition)

    Demand proxy = median votes per restaurant for a city x cuisine cell.
    Supply = number of restaurants in that cell.
    Opportunity index = demand percentile - supply percentile within the city, so a
    positive score means "customers engage heavily, but few restaurants offer it".
    It is a prioritisation heuristic for a sales team, not a forecast.
    """
    bridge = explode_cuisines(df).merge(
        df[["restaurant_id", "city", "country", "votes", "weighted_rating"]], on="restaurant_id"
    )
    cells = (
        bridge.groupby(["country", "city", "cuisine"])
        .agg(
            restaurants=("restaurant_id", "nunique"),
            median_votes=("votes", "median"),
            mean_weighted_rating=("weighted_rating", "mean"),
        )
        .reset_index()
    )
    city_size = df.groupby("city").size()
    big_cities = city_size[city_size >= 5 * cfg.min_group_size].index
    cells = cells[cells["city"].isin(big_cities) & (cells["restaurants"] >= 3)].copy()
    g = cells.groupby("city")
    cells["demand_pctile"] = g["median_votes"].rank(pct=True)
    cells["supply_pctile"] = g["restaurants"].rank(pct=True)
    cells["opportunity_index"] = (cells["demand_pctile"] - cells["supply_pctile"]).round(3)
    cells = cells.round(
        {"median_votes": 1, "mean_weighted_rating": 3, "demand_pctile": 3, "supply_pctile": 3}
    )
    return cells.sort_values("opportunity_index", ascending=False, ignore_index=True)


def top_restaurants(df: pd.DataFrame, cfg: AnalysisConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    """Top restaurants by evidence-weighted rating (not raw rating)."""
    cols = [
        "restaurant_name",
        "city",
        "country",
        "primary_cuisine",
        "price_band",
        "aggregate_rating",
        "votes",
        "weighted_rating",
        "cost_for_two_gbp",
    ]
    return df[df["is_rated"]].nlargest(cfg.top_n, "weighted_rating")[cols].reset_index(drop=True)


def rating_distribution(df: pd.DataFrame) -> pd.DataFrame:
    bins = np.arange(1.75, 5.01, 0.25)
    rated = df.loc[df["is_rated"], "aggregate_rating"]
    counts = pd.cut(rated, bins).value_counts(sort=False)
    return pd.DataFrame({"rating_bin": counts.index.astype(str), "restaurants": counts.to_numpy()})
