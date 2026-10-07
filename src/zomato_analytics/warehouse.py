"""Build a DuckDB star schema from the cleaned data and run the SQL analysis layer.

DuckDB gives us a real SQL engine with no server to run. The SQL in ``sql/`` is
plain ANSI-style SQL (plus ``QUALIFY`` / ``FILTER``) and ports to Snowflake,
BigQuery or Postgres with minimal changes.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from . import config
from .features import explode_cuisines

STAR_TABLES = [
    "dim_country",
    "dim_city",
    "dim_cuisine",
    "dim_price_band",
    "fact_restaurant",
    "bridge_restaurant_cuisine",
]


class ReconciliationError(RuntimeError):
    pass


def _run_script(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    con.execute(path.read_text(encoding="utf-8"))


def build(
    df: pd.DataFrame, db_path: str | Path = ":memory:", sql_dir: Path = config.SQL_DIR
) -> duckdb.DuckDBPyConnection:
    """Load the staging tables and materialise every script in ``sql/marts``."""
    con = duckdb.connect(str(db_path))
    stg = df.copy()
    for col in stg.columns:  # DuckDB prefers plain numpy / python dtypes for strings
        if pd.api.types.is_string_dtype(stg[col]):
            stg[col] = stg[col].astype(object).where(stg[col].notna(), None)
    con.register("_stg", stg)
    con.execute("CREATE OR REPLACE TABLE stg_restaurants AS SELECT * FROM _stg")
    con.register("_bridge", explode_cuisines(df).astype({"cuisine": object}))
    con.execute("CREATE OR REPLACE TABLE stg_restaurant_cuisine AS SELECT * FROM _bridge")
    con.unregister("_stg")
    con.unregister("_bridge")
    for script in sorted((sql_dir / "marts").glob("*.sql")):
        _run_script(con, script)
    reconcile(con)
    return con


def reconcile(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    counts = run_query(con, config.SQL_DIR / "analysis" / "07_reconciliation.sql")
    c = dict(zip(counts["object"], counts["row_count"], strict=True))
    problems = []
    if c["fact_restaurant"] != c["stg_restaurants"]:
        problems.append("fact_restaurant row count differs from staging (bad join to dim_city?)")
    if c["fact_restaurant_distinct_ids"] != c["fact_restaurant"]:
        problems.append("fact_restaurant grain violated: duplicate restaurant_id")
    if c["restaurants_without_cuisine"]:
        problems.append("restaurants missing from bridge_restaurant_cuisine")
    if problems:
        raise ReconciliationError("; ".join(problems))
    return counts


def run_query(con: duckdb.DuckDBPyConnection, path: Path) -> pd.DataFrame:
    return con.execute(path.read_text(encoding="utf-8")).df()


def run_analysis(
    con: duckdb.DuckDBPyConnection, sql_dir: Path = config.SQL_DIR
) -> dict[str, pd.DataFrame]:
    """Run each query in ``sql/analysis`` and return results keyed by file stem."""
    return {p.stem: run_query(con, p) for p in sorted((sql_dir / "analysis").glob("*.sql"))}


def export_star_schema(con: duckdb.DuckDBPyConnection, out_dir: Path) -> list[Path]:
    """Write each star-schema table to CSV for Power BI / Tableau import."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for table in STAR_TABLES:
        path = out_dir / f"{table}.csv"
        con.table(table).df().to_csv(path, index=False)
        paths.append(path)
    return paths
