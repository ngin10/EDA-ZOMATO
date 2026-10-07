# Methodology & assumptions

Every decision below can be changed in `src/zomato_analytics/config.py` or the seed files.

## 1. Cleaning decisions

| Issue in source | Evidence | Decision | Why |
|---|---|---|---|
| `Aggregate rating = 0.0` for unrated restaurants | ~22% of rows; always paired with "Not rated" | Set to null; add `is_rated` | 0.0 means "missing", not "terrible". Leaving it in pulls every average down. The original notebook's mean rating had this bias. |
| Currency labels unreliable | "Dollar($)" covers 4 countries; the Philippines is labelled "Botswana Pula(P)" | Take the currency from `country_code` | Country code is the reliable key. The label is kept for audit. |
| Prices in 12 currencies | 800,000 IDR next to 40 GBP | Convert to GBP at **2017 average** rates | Gives one currency to compare. Using 2017 rates matches when the data was collected, so 2017 prices aren't distorted by later FX moves (e.g. TRY). |
| Extreme prices | Max 800,000 (IDR, which is genuine) | Robust z-score on log cost **within country**, flag at \|z\|>5 | Flag, don't delete. A single global cutoff would wrongly flag whole currencies. |
| Cost for two = 0 | A handful of rows | Null | Missing, not free. |
| (0, 0) coordinates | A handful of rows | Null | "Null Island" means a missing geocode. |
| Garbled text (e.g. `ÛÁstanbul`) | Turkish / Brazilian names | Repair if the latin-1/UTF-8 mix-up can be reversed; otherwise flag | The data stays usable and stays honest about what couldn't be fixed. |
| Duplicates | Exact and same-ID rows | Drop, keep first, log the count | A unique primary key is required for the star schema. |
| Constant column | `Switch to order menu` = "No" everywhere | Drop | It holds no information. |

Every change is counted in the cleaning log (`tables/cleaning_log.csv`). Hard
post-conditions (`quality.assert_clean`) stop the pipeline if they fail. The
warehouse reconciles row counts between staging and fact tables.

## 2. KPI definitions

| KPI | Definition |
|---|---|
| Restaurants | `COUNT(restaurant_id)` |
| Rated restaurants % | `COUNT(is_rated) / COUNT(*)` |
| Mean rating | `AVG(aggregate_rating)` over **rated** restaurants only |
| Weighted rating | `v/(v+m)·R + m/(v+m)·C`, where v = votes, R = rating, C = global mean of rated restaurants, m = 50 (`bayes_prior_votes`) |
| Median cost for two (GBP) | `MEDIAN(cost_for_two_gbp)` excluding `is_cost_outlier` |
| Online delivery % / Table booking % | Share of restaurants offering the service |
| Votes per restaurant | `SUM(votes) / COUNT(DISTINCT restaurant_id)`: engagement intensity |
| Opportunity index | Within a city, for each cuisine: percentile of median votes (demand) minus percentile of restaurant count (supply). Range −1 to 1. |

**Medians, not means, for cost.** Prices are heavily right-skewed. In the original
notebook the mean cost (1,199) was three times the median (400), and the
currencies were mixed as well.

**Minimum group size.** Rankings need at least 10 rated restaurants
(`min_group_size`), so a city with two restaurants can't top a league table.

## 3. Statistical approach

* Ratings are bounded and skewed, so all tests are **non-parametric**:
  Mann–Whitney U (two groups), Kruskal–Wallis (price bands), Spearman (associations).
* Each p-value is reported **with an effect size**: rank-biserial r, epsilon²
  or rho, labelled negligible / small / medium / large. With about 9,500 rows nearly any
  difference is "significant", so the effect size shows whether it matters.
* **Confounding:** online delivery is almost only offered in India, and table booking is
  concentrated in high price bands. So tests are repeated **India-only**, and the
  service uplift is shown **within each price band**.
* The data is one snapshot with no experiment, so all results are **associations,
  not causal effects**.

## 4. Known limitations

* A single scrape from around 2017–2018, with no time dimension. Trends and seasonality can't be studied.
* Zomato's coverage outside India was a selected set of restaurants, not a census. Results for small
  markets (including the UK, ~80 restaurants in the real file) are directional only.
* FX rates are approximate annual averages. They're good enough for comparing markets but
  not for financial reporting.
* "Votes" measures engagement on the app, not revenue or footfall.

## 5. Data protection

The dataset holds business listings only (restaurant names, addresses, aggregate
scores). It contains no personal data about individuals, so UK GDPR does not apply to the
analysis. The raw file is not committed, to respect Kaggle's distribution terms.
