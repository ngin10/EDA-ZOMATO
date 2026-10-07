-- Country scorecard in GBP. Medians exclude flagged price outliers;
-- ratings exclude unrated restaurants (0.0 is a sentinel, not a score).
SELECT
    dc.country,
    dc.region,
    COUNT(*)                                                         AS restaurants,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)               AS share_pct,
    ROUND(MEDIAN(f.cost_for_two_gbp) FILTER (WHERE NOT f.is_cost_outlier), 2)
                                                                     AS median_cost_for_two_gbp,
    ROUND(AVG(f.aggregate_rating) FILTER (WHERE f.is_rated), 2)      AS mean_rating,
    ROUND(100.0 * AVG(CASE WHEN f.has_online_delivery THEN 1 ELSE 0 END), 1)
                                                                     AS pct_online_delivery,
    SUM(f.votes)                                                     AS total_votes
FROM fact_restaurant AS f
JOIN dim_country AS dc USING (country_code)
GROUP BY dc.country, dc.region
ORDER BY restaurants DESC;
