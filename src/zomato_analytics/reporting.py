"""Write the deliverables: an Excel KPI pack, BI-ready CSVs, and a Markdown
executive brief whose every number is computed, never typed by hand."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from .config import AnalysisConfig


def write_excel(tables: dict[str, pd.DataFrame], path: Path) -> Path:
    """One tab per table, header frozen, columns auto-sized, filter enabled."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as xl:
        for name, table in tables.items():
            sheet = name[:31]
            table.to_excel(xl, sheet_name=sheet, index=False)
            ws = xl.sheets[sheet]
            ws.freeze_panes = "A2"
            if ws.max_row > 1:
                ws.auto_filter.ref = ws.dimensions
            for col_cells in ws.columns:
                width = max(len(str(c.value)) if c.value is not None else 0 for c in col_cells)
                ws.column_dimensions[col_cells[0].column_letter].width = min(max(10, width + 2), 60)
    return path


def write_csvs(tables: dict[str, pd.DataFrame], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, table in tables.items():
        p = out_dir / f"{name}.csv"
        table.to_csv(p, index=False)
        paths.append(p)
    return paths


def _gbp(x: float) -> str:
    return "n/a" if pd.isna(x) else f"£{x:,.2f}"


def _pct(x: float) -> str:
    return "n/a" if pd.isna(x) else f"{x:.1f}%"


def _md_table(df: pd.DataFrame, cols: list[str], n: int = 10) -> str:
    d = df[cols].head(n)
    header = "| " + " | ".join(cols) + " |"
    sep = "|" + "|".join("---" for _ in cols) + "|"
    rows = [
        "| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |"
        for r in d.itertuples(index=False)
    ]
    return "\n".join([header, sep, *rows])


def _test(stats: pd.DataFrame, scope: str, test: str) -> pd.Series | None:
    hit = stats[(stats["scope"] == scope) & (stats["test"] == test)]
    return None if hit.empty else hit.iloc[0]


def executive_summary(
    kpis: dict,
    tables: dict[str, pd.DataFrame],
    stats: pd.DataFrame,
    cleaning_log: pd.DataFrame,
    cfg: AnalysisConfig,
    source: str,
    is_sample: bool,
    figures: list[Path],
    out_path: Path,
) -> Path:
    market = tables["market_overview"]
    uk_bench = tables["uk_benchmark"].set_index("market")
    service = tables["service_impact"]
    cuisine = tables["cuisine_performance"]
    opp = tables["opportunity_matrix"]
    lines: list[str] = []
    add = lines.append

    add("# Zomato Restaurant Market Analysis: Executive Brief")
    add("")
    add(f"_Generated {date.today():%d %B %Y} from `{source}` by the `zomato-analytics` pipeline._")
    add("")
    if is_sample:
        add(
            "> **Synthetic demo data.** These numbers come from the built-in data generator and "
            "only show the pipeline working. Do not quote them. Run the pipeline on the real "
            "Kaggle file to produce real findings."
        )
        add("")

    add("## Headline KPIs")
    add("")
    add("| KPI | Value |")
    add("|---|---|")
    add(f"| Restaurants analysed | {kpis['restaurants']:,} |")
    add(f"| Countries / cities | {kpis['countries']} / {kpis['cities']} |")
    add(f"| Rated restaurants | {_pct(kpis['pct_rated'])} |")
    add(f"| Mean rating (rated only) | {kpis['mean_rating_rated']:.2f} / 5 |")
    add(f"| Median cost for two | {_gbp(kpis['median_cost_for_two_gbp'])} |")
    add(f"| Offer online delivery | {_pct(kpis['pct_online_delivery'])} |")
    add(f"| Offer table booking | {_pct(kpis['pct_table_booking'])} |")
    add("")

    add("## Key findings")
    add("")
    top = market.iloc[0]
    add(
        f"1. **The platform is concentrated in one market.** {top['country']} accounts for "
        f"{top['share_of_restaurants_pct']:.1f}% of listings, so platform-wide averages mostly "
        "describe that market. Every comparison below is therefore also reported per market."
    )

    if "United Kingdom" in uk_bench.index:
        uk = uk_bench.loc["United Kingdom"]
        gap = uk["mean_rating"] - kpis["mean_rating_rated"]
        rating_word = (
            "rates above" if gap >= 0.1 else "rates below" if gap <= -0.1 else "rates in line with"
        )
        platform_votes = float(tables["uk_benchmark"]["median_votes"].median())
        engagement = "more" if uk["median_votes"] > platform_votes else "no more"
        add(
            f"2. **The UK estate {rating_word} the platform.** {int(uk['restaurants']):,} UK "
            f"restaurants ({uk['restaurants'] / kpis['restaurants']:.1%} of listings), mean "
            f"rating {uk['mean_rating']:.2f} vs {kpis['mean_rating_rated']:.2f} platform-wide, "
            f"median cost for two {_gbp(uk['median_cost_for_two_gbp'])}. UK listings get a "
            f"median of {uk['median_votes']:.0f} votes each, {engagement} engagement per "
            "restaurant than the typical market segment."
        )
    else:
        add("2. **No UK restaurants were found in this extract.**")

    tb = _test(stats, "All markets", "table booking")
    tb_india = _test(stats, "India only", "table booking")
    tb_rows = service[service["service"] == "table_booking"].set_index("price_band")
    if tb is not None and "All" in tb_rows.index:
        band_uplifts = tb_rows.drop(index="All", errors="ignore")["rating_uplift"].dropna()
        add(
            f"3. **Table booking goes with higher ratings, but price explains much of it.** "
            f"Overall uplift {tb_rows.loc['All', 'rating_uplift']:+.2f} points "
            f"({tb['effect_magnitude']} effect, p={tb['p_value']:.1g}). Within a price band "
            f"the uplift is {band_uplifts.min():+.2f} to {band_uplifts.max():+.2f}, because "
            "booking is far more common at expensive restaurants."
            + (
                f" India-only effect: {tb_india['effect_magnitude']}."
                if tb_india is not None
                else ""
            )
        )
    od = _test(stats, "All markets", "online delivery")
    od_india = _test(stats, "India only", "online delivery")
    if od is not None:
        add(
            f"4. **Online delivery has a {od['effect_magnitude']} relationship with rating** "
            f"(rank-biserial r={od['effect_size']:+.2f}). "
            + (
                f"Within India, where delivery is actually offered, it is "
                f"{od_india['effect_magnitude']} (r={od_india['effect_size']:+.2f}). "
                if od_india is not None
                else ""
            )
            + "Delivery is mostly offered in India in this dataset, so the platform-wide "
            "comparison mixes up market and service."
        )
    pb = _test(stats, "All markets", "rating differs by price band")
    if pb is not None:
        add(
            f"5. **Price band is a {pb['effect_magnitude']} driver of rating** "
            f"(Kruskal-Wallis epsilon²={pb['effect_size']:.3f}). Customers rate premium "
            "experiences higher, so comparisons between restaurants should be made within a "
            "price band."
        )
    ev = _test(stats, "All markets", "engagement (votes) vs rating")
    if ev is not None:
        add(
            f"6. **Engagement and quality move together** (Spearman rho={ev['statistic']:.2f}). "
            "Because raw ratings from a handful of votes are noisy, rankings in this report use "
            f"a Bayesian-weighted rating (prior = {cfg.bayes_prior_votes} votes)."
        )
    if not cuisine.empty:
        widest = cuisine.iloc[0]
        best = cuisine.sort_values("mean_weighted_rating", ascending=False).iloc[0]
        add(
            f"7. **Cuisine mix:** the most widely offered cuisine is {widest['cuisine']} "
            f"({int(widest['restaurants']):,} restaurants). The best rated (weighted, at least "
            f"{cfg.min_group_size} rated restaurants) is {best['cuisine']} "
            f"({best['mean_weighted_rating']:.2f})."
        )
    add("")

    add("## Recommendations")
    add("")
    add(
        "- **Report KPIs per market, not just platform-wide.** Mixing in the dominant market "
        "hides UK performance. The Power BI model has a country slicer for this."
    )
    add(
        "- **Compare restaurants within a price band** when using ratings for sales "
        "targeting or merchant health scores."
    )
    add(
        "- **Use the weighted rating, not the raw rating, for any league table** shown to "
        "customers or merchants, so restaurants with only a few votes don't top the list."
    )
    add(
        "- **Fix the data at source:** currency should come from the country (not a free-text "
        "label), 'not rated' should be stored as null instead of 0.0, and text should be "
        "saved as UTF-8. See the data-quality section below."
    )
    if not opp.empty:
        uk_opp = opp[opp["country"] == "United Kingdom"].head(3)
        focus = uk_opp if not uk_opp.empty else opp.head(3)
        cells = ", ".join(f"{r.cuisine} in {r.city}" for r in focus.itertuples())
        add(
            f"- **Where to look first for new restaurants:** {cells} have high engagement per "
            "restaurant but few restaurants offering them. Treat this as a shortlist to test, "
            "not a forecast."
        )
    add("")

    if "United Kingdom" in uk_bench.index and not tables["uk_city_summary"].empty:
        add("## UK spotlight")
        add("")
        add(
            _md_table(
                tables["uk_city_summary"],
                [
                    "city",
                    "restaurants",
                    "mean_rating",
                    "median_cost_for_two_gbp",
                    "median_votes",
                    "pct_table_booking",
                ],
            )
        )
        add("")

    add("## Market overview (GBP)")
    add("")
    add(
        _md_table(
            market,
            [
                "country",
                "restaurants",
                "share_of_restaurants_pct",
                "median_cost_for_two_gbp",
                "mean_rating",
                "pct_online_delivery",
            ],
            15,
        )
    )
    add("")

    add("## Statistical evidence")
    add("")
    add(
        "Non-parametric tests, each with an effect size: with this many rows almost any gap "
        "is 'significant', so what matters is how big the effect is."
    )
    add("")
    s = stats.assign(p_value=stats["p_value"].map(lambda p: f"{p:.2g}"))
    add(_md_table(s, ["scope", "test", "n", "effect_size", "effect_magnitude", "p_value"], 20))
    add("")

    add("## Data quality & cleaning log")
    add("")
    add(_md_table(cleaning_log, ["step", "rows_affected", "note"], 30))
    add("")

    if figures:
        add("## Charts")
        add("")
        for f in figures:
            add(f"![{f.stem}](figures/{f.name})")
        add("")

    add("## Caveats")
    add("")
    add(
        "- Data is a single, undated scrape (circa 2017–2018), not a time series, so these "
        "are associations, not causal effects."
    )
    add(
        "- GBP conversion uses approximate 2017 average FX rates "
        "(`data/seeds/fx_rates_to_gbp.csv`) to match the data's vintage. "
        "These are not today's prices."
    )
    add("- 'Votes' measures engagement on the platform, not footfall or revenue.")
    add(
        "- Small markets (including the UK) have few restaurants, so treat sub-group results "
        "there as directional."
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
