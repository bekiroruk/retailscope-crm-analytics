-- Independent examples. Execute in the dedicated RetailScope database.
-- 1. Monthly/channel performance: returns reduce net revenue in their event month.
SELECT * FROM retailscope.v_monthly_performance ORDER BY year_month,channel;
GO
-- 2. Category and brand contribution.
SELECT p.category,p.brand,SUM(f.net_revenue) AS net_revenue,SUM(f.gross_margin) AS gross_margin
FROM retailscope.fact_sales AS f
JOIN retailscope.dim_product AS p ON p.product_id=f.product_id
GROUP BY p.category,p.brand ORDER BY net_revenue DESC;
GO
-- 3. Repeat customer share in the last complete calendar year of this dataset.
WITH orders_per_customer AS (
    SELECT customer_id,COUNT(DISTINCT order_id) AS orders
    FROM retailscope.fact_sales
    WHERE event_type='sale' AND event_date>='2025-01-01' AND event_date<'2026-01-01'
    GROUP BY customer_id
)
SELECT COUNT(*) AS purchasing_customers,
       SUM(CASE WHEN orders>=2 THEN 1 ELSE 0 END) AS repeat_customers,
       1.0*SUM(CASE WHEN orders>=2 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0) AS repeat_share
FROM orders_per_customer;
GO
-- 4. Latest customer snapshot only: never sum value across snapshot dates.
SELECT segment,COUNT(*) AS customers,AVG(inactive_risk90) AS average_risk,
       SUM(expected_margin90) AS expected_margin90
FROM retailscope.customer_scores
WHERE snapshot_date=(SELECT MAX(snapshot_date) FROM retailscope.customer_scores)
GROUP BY segment ORDER BY expected_margin90 DESC;
GO
-- 5. Share of customers shopping in both channels in a defined period.
WITH channel_count AS (
    SELECT customer_id,COUNT(DISTINCT channel) AS channels
    FROM retailscope.fact_sales
    WHERE event_type='sale' AND event_date>='2025-04-01' AND event_date<'2026-04-01'
    GROUP BY customer_id
)
SELECT COUNT(*) AS buyers,SUM(CASE WHEN channels=2 THEN 1 ELSE 0 END) AS omnichannel_buyers
FROM channel_count;
GO
