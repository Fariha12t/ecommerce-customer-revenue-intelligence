# Power BI Dashboard Blueprint

## Report objective
Create a decision-ready overview of the synthetic e-commerce dataset. All values are illustrative of the generated data and must not be presented as actual market results.

## Model and relationships
Use `public fact_order_items` as the main sales fact table.

Recommended dimensions:
- `public customers` — one row per `customer_id`
- `public products` — one row per `product_id`
- `public sellers` — one row per `seller_id`
- `public orders` — one row per `order_id`
- Optional dedicated Date table

Recommended active relationships:
- fact_order_items[customer_id] → customers[customer_id] (many-to-one)
- fact_order_items[product_id] → products[product_id] (many-to-one)
- fact_order_items[seller_id] → sellers[seller_id] (many-to-one)
- fact_order_items[order_id] → orders[order_id] (many-to-one)

Use single-direction filtering from dimensions to the fact wherever possible. Avoid ambiguous bidirectional paths. Do not connect `orders` to both payments and reviews with bidirectional filters unless there is a specific validated need. Keep the inactive `orders[customer_id]` relationship inactive if customer filtering already flows through the fact table. Do not create a relationship using a non-unique column on the one-side.

## Page 1 — Executive Overview
Canvas: 16:9. Theme: deep navy `#10243A`, teal `#16B8A6`, blue `#4C8BF5`, light background `#F4F7FB`, white cards.

Top:
- Title: `E-Commerce | Executive Overview`
- Subtitle: `Customer, revenue and order performance · Synthetic dataset`

KPI row:
1. Total Revenue — `[Total Revenue]`, display units Auto or Thousands, label currency explicitly as `R$`.
2. Total Orders — `[Total Orders]`, whole number.
3. Total Customers — `[Total Customers]`, whole number.
4. Average Order Value — `[Average Order Value]`, currency-style number, label `R$`.

Charts:
- Monthly Revenue Trend: line chart; X-axis purchase month; Y-axis `[Total Revenue]`.
- Revenue by Category: horizontal bar; category on Y-axis; `[Total Revenue]` on X-axis; descending.
- Revenue by State: horizontal bar; customer_state and `[Total Revenue]`.
- Customer Mix: donut chart using customer segment if a segment table is imported; otherwise use Repeat Customers vs Non-repeat Customers only if separately modelled.

Slicers:
- Purchase date/month
- Customer state
- Product category
- Order status (default delivered)

## Page 2 — Product Performance
- KPI cards: `[Total Revenue]`, `[Total Units Sold]`, `[Total Orders]`.
- Bar chart: category revenue.
- Bar chart: top 10 products by revenue.
- Matrix: category, revenue, units, orders, revenue share.
- Use product category from the product dimension or fact table, but do not mix duplicate category columns in one visual.

## Page 3 — Customer Intelligence
- KPI cards: `[Total Customers]`, `[Repeat Customers]`, `[Repeat Customer Rate]`, `[Delivered Revenue per Customer]`.
- Bar/donut chart: RFM segment counts, if the notebook's customer RFM output is loaded as a separate table.
- Table: customer identifier, recency, frequency, monetary value, segment.
- Do not infer predictive churn. Label at-risk groups as rule-based RFM segments.

## Page 4 — Geographic Performance
- Bar chart: revenue by customer state.
- Bar chart: revenue by customer city.
- Optional map only if valid geographic categories/coordinates are available.
- Seller-side view: revenue by seller state/city, clearly distinguished from customer geography.
- The synthetic generator pairs city/state values; location mismatch check should return zero.

## Page 5 — Retention Analysis
- Cohort matrix from the notebook's cohort output, if imported.
- Explain that cohort activity/retention is based on first delivered-order month.
- Keep cohort retention denominator consistent (cohort size).

## Formatting and interaction
- Use consistent navy/teal palette and restrained accent colours.
- Use concise titles and meaningful axis labels.
- Add report-page navigation buttons only after all pages exist.
- Add tooltip pages only if they add useful context.
- Use synced date and geography slicers where appropriate.
- Set visual-level filters to delivered orders for sales KPIs.
- Use `R$` in titles/subtitles if the installed locale does not provide Brazilian Real in the measure format list.

## Validation before publishing
- Compare Power BI `[Total Revenue]`, `[Total Orders]`, `[Total Customers]` and `[Average Order Value]` against SQL/Python outputs from the same refreshed dataset.
- Check one order with multiple item rows: it must count as one order.
- Check cancelled/shipped orders are excluded from delivered metrics.
- Check totals do not inflate when adding product/customer/seller attributes.
- Save the finished `.pbix` and capture genuine screenshots in `powerbi/screenshots/`.
