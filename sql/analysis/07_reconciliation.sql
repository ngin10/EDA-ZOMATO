-- Reconciliation: the warehouse must account for every cleaned row exactly once.
SELECT 'stg_restaurants' AS object, COUNT(*) AS row_count FROM stg_restaurants
UNION ALL
SELECT 'fact_restaurant', COUNT(*) FROM fact_restaurant
UNION ALL
SELECT 'fact_restaurant_distinct_ids', COUNT(DISTINCT restaurant_id) FROM fact_restaurant
UNION ALL
SELECT 'restaurants_without_cuisine',
       COUNT(*) FROM fact_restaurant f
       WHERE NOT EXISTS (SELECT 1 FROM bridge_restaurant_cuisine b
                         WHERE b.restaurant_id = f.restaurant_id);
