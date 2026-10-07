# Data dictionary

**Source:** [Zomato Restaurants Data (Kaggle, Shruti Mehta)](https://www.kaggle.com/datasets/shrutimehta/zomato-restaurants-data):
9,551 restaurants in 15 countries, scraped from the Zomato API around 2017–2018. The file
is not redistributed in this repository. Put `zomato.csv` in `data/raw/`.

## Cleaned table: `restaurants_clean` / `stg_restaurants`

| Column | Type | Source | Description |
|---|---|---|---|
| `restaurant_id` | int | Restaurant ID | Primary key. Unique after de-duplication. |
| `restaurant_name` | text | Restaurant Name | Trimmed; encoding repaired where reversible. |
| `country_code` | int | Country Code | FK to `dim_country`. |
| `country`, `region` | text | seed | From `data/seeds/country_codes.csv`. |
| `city`, `locality`, `locality_verbose`, `address` | text | raw | Trimmed; encoding repaired where reversible. |
| `latitude`, `longitude` | float | raw | Null when (0, 0) or out of range. |
| `cuisines` | text | Cuisines | Comma-separated list; missing → `Unknown`. |
| `primary_cuisine` | text | derived | First listed cuisine. |
| `n_cuisines` | int | derived | Number of distinct cuisines listed. |
| `cost_for_two_local` | float | Average Cost for two | Local currency; 0 → null. |
| `currency_label` | text | Currency | Raw label, kept **for audit only**, because it is unreliable. |
| `iso_currency` | text | seed | Currency derived from the country (ISO 4217). |
| `cost_for_two_gbp` | float | derived | `cost_for_two_local × gbp_per_unit` (2017 average FX). |
| `is_cost_outlier` | bool | derived | \|robust z\| > 5 on log cost within the country. Kept in the data, left out of cost medians. |
| `has_table_booking`, `has_online_delivery`, `is_delivering_now` | bool | Yes/No | |
| `price_range` | int 1–4 | Price range | Zomato's within-market price tier. |
| `price_band` | text | derived | Budget / Mid-range / Premium / Luxury. |
| `aggregate_rating` | float 1–5 | Aggregate rating | **Null when unrated** (the source uses 0.0). |
| `is_rated` | bool | derived | False when the source rating was 0.0 / "Not rated". |
| `rating_text`, `rating_color` | text | raw | Zomato's labels. |
| `votes` | int | Votes | Number of user ratings: an engagement proxy. |
| `log_votes` | float | derived | `ln(1 + votes)`. |
| `weighted_rating` | float | derived | Bayesian-shrunk rating (see methodology). |
| `market` | text | derived | India / United Kingdom / Other. |
| `is_uk` | bool | derived | Country is United Kingdom. |
| `has_encoding_issue` | bool | derived | Text still garbled after automatic repair. |

Dropped: `Switch to order menu` (it has the same value, "No", in every row).

## Star schema (`reports/powerbi/`)

```
dim_country (country_code PK) ─┐
dim_city    (city_key PK)  ────┼──< fact_restaurant (restaurant_id PK) >──< bridge_restaurant_cuisine >── dim_cuisine (cuisine_key PK)
dim_price_band (price_range PK)┘
```

* **Grain of `fact_restaurant`:** one row per restaurant.
* **`bridge_restaurant_cuisine`:** one row per (restaurant, cuisine). `is_primary` marks the first-listed cuisine.
