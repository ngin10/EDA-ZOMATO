-- Dimensions for the restaurant star schema.
-- Source: stg_restaurants (the cleaned, feature-enriched table loaded by warehouse.py).

CREATE OR REPLACE TABLE dim_country AS
SELECT DISTINCT
    country_code,
    country,
    region,
    iso_currency,
    country = 'United Kingdom' AS is_uk
FROM stg_restaurants;

CREATE OR REPLACE TABLE dim_city AS
SELECT
    ROW_NUMBER() OVER (ORDER BY country_code, city) AS city_key,
    city,
    country_code
FROM (SELECT DISTINCT city, country_code FROM stg_restaurants);

CREATE OR REPLACE TABLE dim_cuisine AS
SELECT
    ROW_NUMBER() OVER (ORDER BY cuisine) AS cuisine_key,
    cuisine
FROM (SELECT DISTINCT cuisine FROM stg_restaurant_cuisine);

CREATE OR REPLACE TABLE dim_price_band AS
SELECT DISTINCT price_range, price_band
FROM stg_restaurants
WHERE price_range IS NOT NULL;
