-- UK estate benchmarked against the rest of the platform.
SELECT
    CASE WHEN dc.is_uk THEN 'United Kingdom' ELSE 'Rest of platform' END   AS segment,
    COUNT(*)                                                               AS restaurants,
    ROUND(MEDIAN(f.cost_for_two_gbp) FILTER (WHERE NOT f.is_cost_outlier), 2)
                                                                           AS median_cost_for_two_gbp,
    ROUND(AVG(f.aggregate_rating) FILTER (WHERE f.is_rated), 2)            AS mean_rating,
    ROUND(MEDIAN(f.votes), 1)                                              AS median_votes,
    ROUND(100.0 * AVG(CASE WHEN f.has_table_booking THEN 1 ELSE 0 END), 1) AS pct_table_booking
FROM fact_restaurant AS f
JOIN dim_country AS dc USING (country_code)
GROUP BY 1
ORDER BY 1 DESC;
