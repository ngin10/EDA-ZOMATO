# Power BI dashboard specification

The pipeline exports a ready-to-load star schema to `reports/powerbi/`. Build the
dashboard like this (Tableau works the same way).

## 1. Model

1. **Get data → Text/CSV**: load all six files from `reports/powerbi/`.
2. Relationships (all single-direction, filter flows dimension → fact):
   * `dim_country[country_code]` 1 → * `fact_restaurant[country_code]`
   * `dim_city[city_key]` 1 → * `fact_restaurant[city_key]`
   * `dim_price_band[price_range]` 1 → * `fact_restaurant[price_range]`
   * `fact_restaurant[restaurant_id]` 1 → * `bridge_restaurant_cuisine[restaurant_id]` (**both directions**, so a cuisine slicer filters the fact table)
   * `dim_cuisine[cuisine_key]` 1 → * `bridge_restaurant_cuisine[cuisine_key]`
3. Set the data category on `fact_restaurant[latitude/longitude]` to Latitude/Longitude.

## 2. DAX measures

```DAX
Restaurants = COUNTROWS ( fact_restaurant )

Rated Restaurants = CALCULATE ( [Restaurants], fact_restaurant[is_rated] = TRUE () )

% Rated = DIVIDE ( [Rated Restaurants], [Restaurants] )

Mean Rating =
CALCULATE ( AVERAGE ( fact_restaurant[aggregate_rating] ), fact_restaurant[is_rated] = TRUE () )

Weighted Rating = AVERAGE ( fact_restaurant[weighted_rating] )

Median Cost for Two (GBP) =
CALCULATE (
    MEDIAN ( fact_restaurant[cost_for_two_gbp] ),
    fact_restaurant[is_cost_outlier] = FALSE ()
)

Total Votes = SUM ( fact_restaurant[votes] )

Votes per Restaurant = DIVIDE ( [Total Votes], [Restaurants] )

% Online Delivery =
DIVIDE ( CALCULATE ( [Restaurants], fact_restaurant[has_online_delivery] = TRUE () ), [Restaurants] )

% Table Booking =
DIVIDE ( CALCULATE ( [Restaurants], fact_restaurant[has_table_booking] = TRUE () ), [Restaurants] )

UK Rating Gap vs Platform =
VAR uk = CALCULATE ( [Mean Rating], dim_country[is_uk] = TRUE () )
VAR platform = CALCULATE ( [Mean Rating], REMOVEFILTERS ( dim_country ) )
RETURN uk - platform

Table Booking Rating Uplift =
CALCULATE ( [Mean Rating], fact_restaurant[has_table_booking] = TRUE () )
    - CALCULATE ( [Mean Rating], fact_restaurant[has_table_booking] = FALSE () )
```

## 3. Pages

| Page | Audience question | Visuals |
|---|---|---|
| **Executive overview** | How big is the platform and how is it doing? | KPI cards (Restaurants, % Rated, Mean Rating, Median Cost GBP); bar chart of restaurants by country; map of restaurants coloured by rating band |
| **UK spotlight** | How does the UK compare? | KPI cards with *UK Rating Gap vs Platform*; bar chart by UK city; UK vs Rest table; cuisine mix in the UK |
| **Rating drivers** | What goes with a high rating? | Clustered bar of *Mean Rating* by price band × table booking; box/violin by price band; scatter of votes vs rating |
| **Cuisine & opportunity** | Where should merchant acquisition focus? | Treemap of cuisines by restaurants; matrix of city × cuisine with conditional formatting on votes per restaurant (import `tables/opportunity_matrix.csv`) |
| **Data quality** | Can we trust it? | Table of `tables/dq_raw_profile.csv` and `cleaning_log.csv`; card with rows in vs rows out |

**Slicers** (top row, synced across pages): Country, City, Price band, Cuisine.

## 4. Design rules

* One accent colour for the subject (e.g. UK) and neutral grey for context.
* Medians for cost, rated-only for ratings. Put the definitions in each visual's tooltip.
* Hide the raw `aggregate_rating` from report view and expose measures only, so nobody averages 0.0 sentinels by accident.
