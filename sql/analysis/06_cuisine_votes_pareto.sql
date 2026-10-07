-- Pareto view: how concentrated is customer engagement across cuisines?
WITH cuisine_votes AS (
    SELECT cu.cuisine, SUM(f.votes) AS total_votes
    FROM bridge_restaurant_cuisine AS b
    JOIN fact_restaurant AS f  USING (restaurant_id)
    JOIN dim_cuisine     AS cu USING (cuisine_key)
    GROUP BY cu.cuisine
)
SELECT
    cuisine,
    total_votes,
    ROUND(100.0 * total_votes / SUM(total_votes) OVER (), 2)                      AS share_pct,
    ROUND(100.0 * SUM(total_votes) OVER (ORDER BY total_votes DESC, cuisine
                                         ROWS UNBOUNDED PRECEDING)
          / SUM(total_votes) OVER (), 2)                                          AS cumulative_share_pct,
    ROW_NUMBER() OVER (ORDER BY total_votes DESC, cuisine)                         AS rank
FROM cuisine_votes
ORDER BY rank;
