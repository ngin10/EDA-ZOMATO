-- Rating spread by price band: does paying more buy a better experience?
SELECT
    p.price_range,
    p.price_band,
    COUNT(*)                                                             AS rated_restaurants,
    ROUND(QUANTILE_CONT(f.aggregate_rating, 0.25), 2)                    AS rating_p25,
    ROUND(MEDIAN(f.aggregate_rating), 2)                                 AS rating_median,
    ROUND(QUANTILE_CONT(f.aggregate_rating, 0.75), 2)                    AS rating_p75,
    ROUND(MEDIAN(f.cost_for_two_gbp) FILTER (WHERE NOT f.is_cost_outlier), 2)
                                                                         AS median_cost_for_two_gbp
FROM fact_restaurant AS f
JOIN dim_price_band AS p USING (price_range)
WHERE f.is_rated
GROUP BY p.price_range, p.price_band
ORDER BY p.price_range;
