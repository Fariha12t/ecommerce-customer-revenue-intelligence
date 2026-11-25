-- Analytics landing schema. The Python loader creates/replaces these tables.
-- Run this file first to create a dedicated schema if desired.
CREATE SCHEMA IF NOT EXISTS ecommerce;
SET search_path TO ecommerce, public;

-- Example analytics views. The loader currently writes tables to the default schema;
-- either set search_path in your connection or adapt the loader schema setting.
CREATE OR REPLACE VIEW delivered_order_summary AS
SELECT
    order_id,
    customer_id,
    order_purchase_timestamp,
    item_revenue,
    freight_revenue,
    gross_item_value,
    order_status
FROM public.fact_orders
WHERE order_status = 'delivered';

CREATE OR REPLACE VIEW delivered_category_revenue AS
SELECT
    product_category_name_english AS category,
    SUM(revenue_including_freight) AS gross_value,
    COUNT(DISTINCT order_id) AS orders,
    COUNT(*) AS units
FROM public.fact_order_items
WHERE order_status = 'delivered'
GROUP BY product_category_name_english;
