
-- ============================================================
-- E-COMMERCE CUSTOMER & REVENUE INTELLIGENCE PLATFORM
-- Advanced PostgreSQL Business Analytics
-- ============================================================


-- 1. MONTHLY DELIVERED-ORDER REVENUE AND AVERAGE ORDER VALUE
-- Uses order-level aggregation to avoid counting individual
-- order items as separate orders.

WITH order_revenue AS (
    SELECT
        order_id,
        DATE_TRUNC(
            'month',
            order_purchase_timestamp::timestamp
        ) AS month,
        SUM((price + freight_value)::numeric) AS revenue
    FROM fact_order_items
    WHERE order_status = 'delivered'
    GROUP BY
        order_id,
        DATE_TRUNC('month', order_purchase_timestamp::timestamp)
)
SELECT
    month,
    ROUND(SUM(revenue), 2) AS revenue,
    COUNT(*) AS delivered_orders,
    ROUND(
        SUM(revenue) / NULLIF(COUNT(*), 0),
        2
    ) AS average_order_value
FROM order_revenue
GROUP BY month
ORDER BY month;


-- 2. TOP PRODUCT CATEGORIES BY GROSS VALUE

SELECT
    product_category_name_english AS category,
    ROUND(SUM((price + freight_value)::numeric), 2) AS gross_value,
    COUNT(DISTINCT order_id) AS orders,
    COUNT(*) AS units
FROM fact_order_items
WHERE order_status = 'delivered'
GROUP BY product_category_name_english
ORDER BY gross_value DESC
LIMIT 15;


-- 3. REPEAT-PURCHASE RATE BY UNIQUE CUSTOMER

WITH customer_frequency AS (
    SELECT
        customer_unique_id,
        COUNT(DISTINCT order_id) AS orders
    FROM fact_order_items
    WHERE order_status = 'delivered'
    GROUP BY customer_unique_id
)
SELECT
    COUNT(*) FILTER (WHERE orders >= 2) AS repeat_customers,
    COUNT(*) AS total_customers,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE orders >= 2)
        / NULLIF(COUNT(*), 0),
        2
    ) AS repeat_customer_rate_pct
FROM customer_frequency;


-- 4. STATE-LEVEL SALES PERFORMANCE

SELECT
    customer_state,
    ROUND(SUM((price + freight_value)::numeric), 2) AS gross_value,
    COUNT(DISTINCT order_id) AS orders,
    COUNT(DISTINCT customer_unique_id) AS customers
FROM fact_order_items
WHERE order_status = 'delivered'
GROUP BY customer_state
ORDER BY gross_value DESC;


-- 5. CUSTOMER FIRST-PURCHASE COHORTS
-- Calculates customer activity by month since first purchase.

WITH customer_orders AS (
    SELECT DISTINCT
        customer_unique_id,
        DATE_TRUNC(
            'month',
            order_purchase_timestamp::timestamp
        )::date AS order_month
    FROM fact_order_items
    WHERE order_status = 'delivered'
),
cohorts AS (
    SELECT
        customer_unique_id,
        order_month,
        MIN(order_month) OVER (
            PARTITION BY customer_unique_id
        ) AS cohort_month
    FROM customer_orders
)
SELECT
    cohort_month,
    (
        (EXTRACT(YEAR FROM order_month)
        - EXTRACT(YEAR FROM cohort_month)) * 12
        + EXTRACT(MONTH FROM order_month)
        - EXTRACT(MONTH FROM cohort_month) + 1
    )::integer AS cohort_index,
    COUNT(DISTINCT customer_unique_id) AS active_customers
FROM cohorts
GROUP BY cohort_month, cohort_index
ORDER BY cohort_month, cohort_index;


-- 6. RANK PRODUCT CATEGORIES WITHIN EACH MONTH
-- Demonstrates DENSE_RANK() window function.

WITH monthly_category AS (
    SELECT
        DATE_TRUNC(
            'month',
            order_purchase_timestamp::timestamp
        ) AS month,
        product_category_name_english AS category,
        SUM((price + freight_value)::numeric) AS revenue
    FROM fact_order_items
    WHERE order_status = 'delivered'
    GROUP BY
        DATE_TRUNC('month', order_purchase_timestamp::timestamp),
        product_category_name_english
)
SELECT
    month,
    category,
    ROUND(revenue, 2) AS revenue,
    DENSE_RANK() OVER (
        PARTITION BY month
        ORDER BY revenue DESC
    ) AS category_rank
FROM monthly_category
ORDER BY month, category_rank;
