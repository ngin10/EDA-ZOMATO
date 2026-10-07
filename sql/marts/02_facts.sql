-- Fact and bridge tables. Grain of fact_restaurant: one row per restaurant.

CREATE OR REPLACE TABLE fact_restaurant AS
SELECT
    s.restaurant_id,
    s.restaurant_name,
    c.city_key,
    s.country_code,
    s.locality,
    s.latitude,
    s.longitude,
    s.price_range,
    s.primary_cuisine,
    s.n_cuisines,
    s.cost_for_two_local,
    s.cost_for_two_gbp,
    s.is_cost_outlier,
    s.has_online_delivery,
    s.has_table_booking,
    s.is_rated,
    s.aggregate_rating,
    s.weighted_rating,
    s.rating_text,
    s.votes,
    s.has_encoding_issue
FROM stg_restaurants AS s
JOIN dim_city AS c
  ON c.city = s.city
 AND c.country_code = s.country_code;

-- Many-to-many: a restaurant can serve several cuisines.
CREATE OR REPLACE TABLE bridge_restaurant_cuisine AS
SELECT
    b.restaurant_id,
    d.cuisine_key,
    b.is_primary
FROM stg_restaurant_cuisine AS b
JOIN dim_cuisine AS d USING (cuisine);
