-- Best-rated cities within each country, using the evidence-weighted rating.
-- Cities with fewer than 10 rated restaurants are excluded as too thin to rank.
WITH city_stats AS (
    SELECT
        dc.country,
        ci.city,
        COUNT(*)                         AS restaurants,
        COUNT(*) FILTER (WHERE f.is_rated) AS rated_restaurants,
        AVG(f.weighted_rating)           AS mean_weighted_rating
    FROM fact_restaurant AS f
    JOIN dim_city    AS ci USING (city_key)
    JOIN dim_country AS dc ON dc.country_code = f.country_code
    GROUP BY dc.country, ci.city
    HAVING COUNT(*) FILTER (WHERE f.is_rated) >= 10
)
SELECT
    country,
    city,
    restaurants,
    ROUND(mean_weighted_rating, 3)                                          AS mean_weighted_rating,
    RANK() OVER (PARTITION BY country ORDER BY mean_weighted_rating DESC)   AS rank_in_country,
    RANK() OVER (ORDER BY mean_weighted_rating DESC)                        AS rank_overall
FROM city_stats
ORDER BY country, rank_in_country;
