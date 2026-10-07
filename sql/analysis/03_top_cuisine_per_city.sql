-- The most widely offered cuisine in each city (ties broken by total votes).
WITH city_cuisine AS (
    SELECT
        ci.city,
        cu.cuisine,
        COUNT(DISTINCT f.restaurant_id) AS restaurants,
        SUM(f.votes)                    AS total_votes
    FROM bridge_restaurant_cuisine AS b
    JOIN fact_restaurant AS f  USING (restaurant_id)
    JOIN dim_city        AS ci USING (city_key)
    JOIN dim_cuisine     AS cu USING (cuisine_key)
    GROUP BY ci.city, cu.cuisine
)
SELECT city, cuisine AS top_cuisine, restaurants, total_votes
FROM city_cuisine
QUALIFY ROW_NUMBER() OVER (PARTITION BY city ORDER BY restaurants DESC, total_votes DESC) = 1
ORDER BY restaurants DESC;
