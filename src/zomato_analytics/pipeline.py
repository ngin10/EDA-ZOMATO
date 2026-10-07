"""Orchestrates the end-to-end run: extract -> validate -> clean -> model -> analyse -> publish."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import cleaning, config, features, io, metrics, quality, reporting, stats, viz, warehouse
from .config import DEFAULT_CONFIG, AnalysisConfig

log = logging.getLogger(__name__)


@dataclass
class RunResult:
    clean: pd.DataFrame
    tables: dict[str, pd.DataFrame]
    sql_results: dict[str, pd.DataFrame]
    stats: pd.DataFrame
    outputs: list[Path]


def build_tables(df: pd.DataFrame, cfg: AnalysisConfig) -> dict[str, pd.DataFrame]:
    return {
        "market_overview": metrics.market_overview(df),
        "uk_benchmark": metrics.uk_benchmark(df),
        "uk_city_summary": metrics.uk_city_summary(df),
        "city_league_table": metrics.city_league_table(df, cfg),
        "cuisine_performance": metrics.cuisine_performance(df, cfg),
        "price_band_summary": metrics.price_band_summary(df),
        "service_impact": metrics.service_impact(df),
        "opportunity_matrix": metrics.opportunity_matrix(df, cfg),
        "top_restaurants": metrics.top_restaurants(df, cfg),
        "rating_distribution": metrics.rating_distribution(df),
    }


def run(
    input_path: Path,
    out_dir: Path = config.REPORTS_DIR,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
    is_sample: bool = False,
    make_charts: bool = True,
) -> RunResult:
    t0 = time.perf_counter()
    out_dir = Path(out_dir)
    outputs: list[Path] = []

    log.info("1/6 Extract")
    raw = io.read_raw(input_path)
    raw_profile = quality.profile_raw(raw)

    log.info("2/6 Clean + validate")
    df, clog = cleaning.clean(raw, cfg)
    df = features.add_features(df, cfg)
    clean_checks = quality.assert_clean(df)

    log.info("3/6 Model (DuckDB star schema)")
    db_path = out_dir / "zomato.duckdb"
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    con = warehouse.build(df, db_path)
    sql_results = warehouse.run_analysis(con)
    outputs += warehouse.export_star_schema(con, out_dir / "powerbi")
    con.close()
    outputs.append(db_path)

    log.info("4/6 Analyse")
    kpis = metrics.headline_kpis(df)
    tables = build_tables(df, cfg)
    test_results = stats.run_all(df, cfg)

    log.info("5/6 Visualise")
    figures = (
        viz.render_all(df, tables, cfg.price_band_labels, out_dir / "figures")
        if make_charts
        else []
    )
    outputs += figures

    log.info("6/6 Publish")
    dq_tables = {
        "dq_raw_profile": raw_profile,
        "dq_clean_checks": clean_checks,
        "cleaning_log": clog.to_frame(),
    }
    kpi_table = pd.DataFrame(list(kpis.items()), columns=["kpi", "value"])
    excel_tables = {
        "headline_kpis": kpi_table,
        **tables,
        "statistical_tests": test_results,
        **{f"sql_{k}": v for k, v in sql_results.items()},
        **dq_tables,
    }
    outputs.append(reporting.write_excel(excel_tables, out_dir / "zomato_kpi_pack.xlsx"))
    outputs += reporting.write_csvs(
        {**tables, "statistical_tests": test_results, **dq_tables}, out_dir / "tables"
    )
    processed = out_dir / "data"
    processed.mkdir(parents=True, exist_ok=True)
    df.to_csv(processed / "restaurants_clean.csv", index=False)
    outputs.append(processed / "restaurants_clean.csv")
    outputs.append(
        reporting.executive_summary(
            kpis,
            tables,
            test_results,
            clog.to_frame(),
            cfg,
            Path(input_path).name,
            is_sample,
            figures,
            out_dir / "executive_summary.md",
        )
    )

    manifest = {
        "source": str(input_path),
        "synthetic_sample": is_sample,
        "rows_in": clog.rows_in,
        "rows_out": clog.rows_out,
        "runtime_seconds": round(time.perf_counter() - t0, 2),
        "kpis": kpis,
        "outputs": sorted(str(p.relative_to(out_dir)) for p in outputs),
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    log.info(
        "Done in %.1fs: %s rows in, %s rows out -> %s",
        manifest["runtime_seconds"],
        clog.rows_in,
        clog.rows_out,
        out_dir,
    )
    return RunResult(df, tables, sql_results, test_results, outputs)
