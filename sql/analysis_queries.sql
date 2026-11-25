-- 1. Monthly delivered-order revenue and AOV.
WITH order_revenue AS (
    SELECT order_id, DATE_TRUNC('month', order_purchase_timestamp) AS month,
           SUM(price + freight_value) AS revenue
    FROM fact_order_items
    WHERE order_status = 'delivered'
    GROUP BY order_id, DATE_TRUNC('month', order_purchase_timestamp)
)
SELECT month, SUM(revenue) AS revenue,
       COUNT(*) AS delivered_orders,
       ROUND(SUM(revenue) / NULLIF(COUNT(*), 0), 2) AS average_order_value
FROM order_revenue
GROUP BY month
ORDER BY month;

-- 2. Top product categories by gross value.
SELECT product_category_name_english AS category,
       ROUND(SUM(price + freight_value), 2) AS gross_value,
       COUNT(DISTINCT order_id) AS orders,
       COUNT(*) AS units
FROM fact_order_items
WHERE order_status = 'delivered'
GROUP BY 1
ORDER BY gross_value DESC
LIMIT 15;

-- 3. Repeat-purchase rate by unique customer.
WITH customer_frequency AS (
    SELECT customer_unique_id, COUNT(DISTINCT order_id) AS orders
    FROM fact_order_items
    WHERE order_status = 'delivered'
    GROUP BY customer_unique_id
)
SELECT COUNT(*) FILTER (WHERE orders >= 2) AS repeat_customers,
       COUNT(*) AS total_customers,
       ROUND(100.0 * COUNT(*) FILTER (WHERE orders >= 2) / NULLIF(COUNT(*), 0), 2)
           AS repeat_customer_rate_pct
FROM customer_frequency;

-- 4. State-level performance.
SELECT customer_state,
       ROUND(SUM(price + freight_value), 2) AS gross_value,
       COUNT(DISTINCT order_id) AS orders,
       COUNT(DISTINCT customer_unique_id) AS customers
FROM fact_order_items
WHERE order_status = 'delivered'
GROUP BY customer_state
ORDER BY gross_value DESC;

-- 5. Customer first-purchase cohorts and month offset.
WITH customer_orders AS (
    SELECT DISTINCT customer_unique_id,
           DATE_TRUNC('month', order_purchase_timestamp)::date AS order_month
    FROM fact_order_items
    WHERE order_status = 'delivered'
),
cohorts AS (
    SELECT customer_unique_id, order_month,
           MIN(order_month) OVER (PARTITION BY customer_unique_id) AS cohort_month
    FROM customer_orders
)
SELECT cohort_month,
       (EXTRACT(YEAR FROM order_month) - EXTRACT(YEAR FROM cohort_month)) * 12
       + EXTRACT(MONTH FROM order_month) - EXTRACT(MONTH FROM cohort_month) + 1
           AS cohort_index,
       COUNT(DISTINCT customer_unique_id) AS active_customers
FROM cohorts
GROUP BY cohort_month, cohort_index
ORDER BY cohort_month, cohort_index;

-- 6. Rank categories within each month using a window function.
WITH monthly_category AS (
    SELECT DATE_TRUNC('month', order_purchase_timestamp) AS month,
           product_category_name_english AS category,
           SUM(price + freight_value) AS revenue
    FROM fact_order_items
    WHERE order_status = 'delivered'
    GROUP BY 1, 2
)
SELECT month, category, revenue,
       DENSE_RANK() OVER (PARTITION BY month ORDER BY revenue DESC) AS category_rank
FROM monthly_category
ORDER BY month, category_rank;
