-- Final sanity checks for the PostgreSQL model.
-- Run after python -m src.etl and python -m src.load_postgres.
-- Adjust table/column names only if your schema differs.

-- 1. Row counts
SELECT 'orders' AS table_name, COUNT(*) AS row_count FROM orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL
SELECT 'customers', COUNT(*) FROM customers
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'sellers', COUNT(*) FROM sellers;

-- 2. Delivered-order KPIs at order-item grain
SELECT
    COUNT(*) AS delivered_order_item_rows,
    COUNT(DISTINCT order_id) AS delivered_orders,
    COUNT(DISTINCT customer_unique_id) AS delivered_customers,
    ROUND(SUM(price::numeric + freight_value::numeric), 2) AS delivered_gross_order_item_value,
    ROUND(
        SUM(price::numeric + freight_value::numeric)
        / NULLIF(COUNT(DISTINCT order_id), 0),
        2
    ) AS average_order_value
FROM fact_order_items
WHERE LOWER(order_status) = 'delivered';

-- 3. Customer city/state validation for generated location pairs
SELECT COUNT(*) AS customer_location_mismatches
FROM customers
WHERE NOT (
    (customer_city = 'Sao Paulo' AND customer_state = 'SP') OR
    (customer_city = 'Rio de Janeiro' AND customer_state = 'RJ') OR
    (customer_city = 'Belo Horizonte' AND customer_state = 'MG') OR
    (customer_city = 'Curitiba' AND customer_state = 'PR') OR
    (customer_city = 'Porto Alegre' AND customer_state = 'RS') OR
    (customer_city = 'Salvador' AND customer_state = 'BA') OR
    (customer_city = 'Brasilia' AND customer_state = 'DF')
);

-- 4. Seller city/state validation
SELECT COUNT(*) AS seller_location_mismatches
FROM sellers
WHERE NOT (
    (seller_city = 'Sao Paulo' AND seller_state = 'SP') OR
    (seller_city = 'Rio de Janeiro' AND seller_state = 'RJ') OR
    (seller_city = 'Belo Horizonte' AND seller_state = 'MG') OR
    (seller_city = 'Curitiba' AND seller_state = 'PR') OR
    (seller_city = 'Porto Alegre' AND seller_state = 'RS') OR
    (seller_city = 'Salvador' AND seller_state = 'BA') OR
    (seller_city = 'Brasilia' AND seller_state = 'DF')
);

-- 5. Duplicate order IDs in the orders table (expected 0)
SELECT COUNT(*) AS duplicate_order_id_groups
FROM (
    SELECT order_id
    FROM orders
    GROUP BY order_id
    HAVING COUNT(*) > 1
) d;
