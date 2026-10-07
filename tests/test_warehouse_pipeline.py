import json

import pandas as pd
import pytest

from zomato_analytics import metrics, pipeline, sample_data, warehouse


@pytest.fixture(scope="module")
def con(df):
    c = warehouse.build(df)
    yield c
    c.close()


def test_star_schema_reconciles(con, df):
    counts = warehouse.reconcile(con).set_index("object")["row_count"]
    assert counts["fact_restaurant"] == len(df)
    assert counts["restaurants_without_cuisine"] == 0


def test_sql_matches_python_country_kpis(con, df):
    """The SQL layer and the pandas layer are two implementations of the same KPI;
    they must agree, or one of them is wrong."""
    sql = warehouse.run_analysis(con)["01_country_kpis"].set_index("country")
    py = metrics.market_overview(df).set_index("country")
    for country in py.index:
        assert sql.loc[country, "restaurants"] == py.loc[country, "restaurants"]
        assert sql.loc[country, "mean_rating"] == pytest.approx(
            py.loc[country, "mean_rating"], abs=0.011
        )
        assert sql.loc[country, "median_cost_for_two_gbp"] == pytest.approx(
            py.loc[country, "median_cost_for_two_gbp"], abs=0.011
        )


def test_one_top_cuisine_per_city(con):
    top = warehouse.run_analysis(con)["03_top_cuisine_per_city"]
    assert top["city"].is_unique


def test_pareto_reaches_100(con):
    p = warehouse.run_analysis(con)["06_cuisine_votes_pareto"]
    assert p["cumulative_share_pct"].iloc[-1] == pytest.approx(100, abs=0.05)


def test_end_to_end_pipeline(tmp_path):
    src = sample_data.write_sample(tmp_path / "raw.csv", n=800, seed=3)
    out = tmp_path / "out"
    result = pipeline.run(src, out, is_sample=True, make_charts=True)

    manifest = json.loads((out / "run_manifest.json").read_text())
    assert manifest["synthetic_sample"] is True
    assert manifest["rows_out"] == len(result.clean)
    for rel in (
        "executive_summary.md",
        "zomato_kpi_pack.xlsx",
        "powerbi/fact_restaurant.csv",
        "tables/statistical_tests.csv",
        "figures/01_market_footprint.png",
    ):
        assert (out / rel).exists(), rel

    summary = (out / "executive_summary.md").read_text()
    assert "Synthetic demo data" in summary
    sheets = pd.ExcelFile(out / "zomato_kpi_pack.xlsx").sheet_names
    assert "headline_kpis" in sheets and "dq_clean_checks" in sheets
