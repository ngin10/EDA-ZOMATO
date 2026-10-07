# Presenting this project for UK data analyst roles

UK job specs for Data Analyst roles keep asking for the same things: **SQL**,
**Python or R**, **Excel**, **Power BI/Tableau**, **data quality**, **stakeholder
communication** and, more and more, **version control and testing**. This
project shows evidence of each one.

| Skill in job spec | Where it is evidenced |
|---|---|
| SQL (joins, CTEs, window functions) | `sql/marts/` star schema; `sql/analysis/` uses `RANK`, `ROW_NUMBER … QUALIFY`, running totals, `FILTER`, quantiles |
| Data modelling | Star schema with a bridge table for many-to-many cuisines (`docs/data_dictionary.md`) |
| Python / pandas | `src/zomato_analytics/`: modular, typed, tested |
| Data cleaning & quality | `cleaning.py`, `quality.py`, cleaning log, reconciliation checks |
| Statistics | Non-parametric tests with effect sizes and checks for confounding (`stats.py`) |
| Power BI | `docs/powerbi_dashboard_spec.md`: model, DAX measures, page design |
| Excel | `reports/zomato_kpi_pack.xlsx`: one filterable tab per KPI table |
| Communication | Auto-generated `executive_summary.md` written for a non-technical reader |
| Engineering hygiene | Git, CI (GitHub Actions), pytest (95%+ line coverage), ruff, reproducible CLI |

## CV bullets (pick 2–3)

Run the pipeline on the real Kaggle file first, then replace the `[placeholders]` with
your numbers. Never quote numbers from the synthetic demo.

- Rebuilt an exploratory notebook into a **tested, reproducible analytics pipeline**
  (Python, DuckDB SQL, GitHub Actions) that processes 9.5k restaurant records from 15
  countries into a Power BI star schema, an Excel KPI pack and an executive brief in under 10 seconds.
- Found and fixed **data-quality problems that biased the original analysis**:
  0.0 used as a placeholder for unrated restaurants (~22% of rows), currency
  labels shared across countries or wrong, and prices mixed across 12 currencies.
  Normalised all prices to GBP.
- Tested rating drivers with non-parametric tests and effect sizes, **controlling for
  market and price band**: table booking uplift of `[overall uplift]` overall vs
  `[min–max]` within price bands *(fill in from `tables/service_impact.csv`)*.
- Wrote **30+ automated tests**, including a check that the SQL and pandas KPI
  implementations agree, and row-count reconciliation between staging and fact tables.

## The 2-minute walkthrough (STAR)

- **Situation.** I had an exploratory notebook on Zomato's restaurant data. It was full of
  charts but hard to trust or repeat.
- **Task.** Turn it into something a commercial team could rely on: correct numbers,
  repeatable runs, and a clear answer on how the UK market compares and what drives ratings.
- **Action.** Profiled the raw file and found that zero ratings were placeholders, currencies
  were mislabelled and costs were mixed. Built a cleaning layer that logs every change and a
  validation layer that stops the pipeline when checks fail. Modelled a star schema in SQL and
  tested drivers with effect sizes, controlling for market and price band. Published to
  Excel, Power BI and a short brief.
- **Result.** One command rebuilds every output, and CI runs the whole pipeline on every
  change. *(Add your headline finding from `reports/executive_summary.md`, e.g. how much of
  the table-booking uplift remains within price bands.)*

## Questions to prepare for

1. *Why median instead of mean for cost?* Prices are heavily skewed. In the raw data the mean was 3× the median.
2. *Why not just drop the 0.0 ratings?* Those restaurants still exist and count towards
   coverage KPIs. They only drop out of rating averages.
3. *Why 2017 FX rates?* To match when the prices were collected. With today's rates the
   Turkish prices would look far too cheap.
4. *Is table booking causing higher ratings?* No causal claim is possible. The data is
   observational and booking is confounded with price. To find out, I'd suggest an A/B test or
   a matched comparison.
5. *How would you productionise this?* Schedule the CLI (Airflow, ADF or cron). Swap
   DuckDB for Snowflake, BigQuery or Azure SQL, since the SQL is portable. Point Power BI at
   the warehouse with scheduled refresh. Add alerting on the data-quality checks.
6. *GDPR?* It's business-listing data with no personal data. If customer-level data were
   added, I'd pseudonymise IDs, minimise fields and record a lawful basis.
