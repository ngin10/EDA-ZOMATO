import pandas as pd
import pytest

from zomato_analytics import features, metrics, stats


def test_split_cuisines_dedupes_and_strips():
    s = features.split_cuisines(pd.Series(["Thai,  Chinese , Thai", None]))
    assert s.tolist() == [["Thai", "Chinese"], ["Unknown"]]


def test_bayesian_rating_shrinks_low_evidence():
    r = pd.Series([4.9, 4.6])
    v = pd.Series([5, 3000])
    wr = features.bayesian_rating(r, v, prior_mean=3.5, prior_votes=50)
    assert wr[1] > wr[0]  # many votes at 4.6 beats few votes at 4.9
    assert 3.5 < wr[0] < 4.9


def test_bridge_has_one_primary_per_restaurant(df):
    bridge = features.explode_cuisines(df)
    assert bridge.groupby("restaurant_id")["is_primary"].sum().eq(1).all()
    assert set(bridge["restaurant_id"]) == set(df["restaurant_id"])


def test_market_overview_shares_sum_to_100(df):
    m = metrics.market_overview(df)
    assert m["share_of_restaurants_pct"].sum() == pytest.approx(100, abs=0.1)
    assert m["restaurants"].sum() == len(df)


def test_rating_kpis_exclude_unrated(df):
    k = metrics.headline_kpis(df)
    assert k["mean_rating_rated"] == pytest.approx(
        df.loc[df["is_rated"], "aggregate_rating"].mean(), abs=0.01
    )
    assert k["mean_rating_rated"] > df["aggregate_rating"].fillna(0).mean()


def test_league_table_respects_min_group_size(df):
    t = metrics.city_league_table(df)
    assert (t["rated_restaurants"] >= 10).all()
    assert t["rank"].iloc[0] == 1


def test_uk_benchmark_contains_uk(df):
    assert "United Kingdom" in metrics.uk_benchmark(df)["market"].tolist()


def test_service_impact_has_overall_and_band_rows(df):
    s = metrics.service_impact(df)
    assert {"All", "Budget", "Luxury"} <= set(s["price_band"])
    assert {"online_delivery", "table_booking"} == set(s["service"])


def test_opportunity_index_bounded(df):
    o = metrics.opportunity_matrix(df)
    assert o["opportunity_index"].between(-1, 1).all()


def test_stats_report_effect_sizes(df):
    res = stats.run_all(df)
    assert {"All markets", "India only"} == set(res["scope"])
    assert res["effect_size"].notna().all()
    tb = res[(res["scope"] == "All markets") & (res["test"] == "table booking")].iloc[0]
    assert tb["effect_size"] > 0  # generator builds in a positive booking effect
