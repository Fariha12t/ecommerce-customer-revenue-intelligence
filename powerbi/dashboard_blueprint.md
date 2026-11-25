# Power BI Dashboard Blueprint

## Data model
Use a star schema where possible:
- Fact: `fact_order_items` (grain: one row per order item)
- Dimensions: Customers, Products, Sellers, Date
- Optional separate facts: `fact_orders`, payments and reviews

Relationships:
- Customers[customer_id] 1 → * fact_order_items[customer_id]
- Products[product_id] 1 → * fact_order_items[product_id]
- Sellers[seller_id] 1 → * fact_order_items[seller_id]
- Date[Date] 1 → * fact_order_items[order_purchase_timestamp] (date only)

Create a Date table and mark it as the model's date table. Avoid directly joining raw payments and order items in one flattened table because both can have multiple rows per order.

## Page 1 — Executive Overview
KPI cards: Gross Value, Delivered Orders, Average Order Value, Unique Customers, Repeat Customer Rate.
Visuals:
- Monthly gross value trend (line)
- Revenue by product category (bar)
- Revenue by customer state (filled map or bar)
- Slicers: date, state, category

## Page 2 — Customer Intelligence
Visuals:
- Customer segment distribution (RFM segment)
- Recency vs monetary scatter
- Top customers by historical value
- Repeat vs one-time customers
- Slicers: RFM segment, state

## Page 3 — Retention & Cohorts
Visuals:
- Cohort retention matrix (cohort month by month index)
- Repeat customer rate by cohort
- Customer count by first-purchase month

## Page 4 — Product & Geography
Visuals:
- Top 15 categories by gross value
- Category monthly trend
- State and city ranking
- Orders and units by category

## Design guidance
Use a consistent two- or three-colour palette, clear titles, dynamic tooltips, and visible metric definitions. Add a "Data refreshed on" card. Use report-page tooltips for category and region details.

## Validation before publishing
- Reconcile total item value to the sum of `price + freight_value` for delivered items.
- Ensure order counts use distinct `order_id`.
- Confirm filters do not change the grain of a KPI unexpectedly.
- Validate repeat-customer counts at `customer_unique_id` grain.
