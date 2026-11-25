# Power BI Build & Validation Guide

This guide is written for the current PostgreSQL import and the synthetic dataset.

## Before you start

1. Open the existing PBIX in Power BI Desktop.
2. Save a working copy as `powerbi/ecommerce_customer_revenue_intelligence.pbix` on your computer.
3. Confirm the `public fact_order_items` table is refreshed.
4. In Model view, verify that `order_id` is unique in `public orders` and repeated as needed in `public fact_order_items`.
5. Use single-direction filters from dimensions to the fact where Power BI permits it. Avoid ambiguous paths. If a 1:1 relationship only offers Both, leave it only if there is no ambiguous path and validate the results carefully.

## Import the theme

1. In Power BI Desktop, open View → Themes → Browse for themes.
2. Select `powerbi/ecommerce_navy_teal_theme.json`.
3. Apply the theme.
4. Use a 16:9 canvas and keep consistent margins and alignment.

## Create the report pages

### Page 1 — Executive Overview
- Four Card visuals: Total Revenue, Total Orders, Total Customers, Average Order Value.
- Line chart: purchase month on X-axis, Total Revenue on Y-axis.
- Horizontal bar: product category by Total Revenue.
- Horizontal bar: customer state by Total Revenue.
- Slicers: purchase date, customer state, product category.

### Page 2 — Product Performance
- Cards: Total Revenue, Total Units Sold, Total Orders.
- Bar chart: category revenue.
- Bar chart: top 10 products by revenue.
- Matrix: category, revenue, units sold, distinct orders.

### Page 3 — Customer Intelligence
- Cards: Total Customers, Repeat Customers, Repeat Customer Rate, Delivered Revenue per Customer.
- If the notebook RFM CSV is imported, add a segment count chart and a customer-level table.
- Do not label RFM segments as a predictive churn model.

### Page 4 — Geographic Performance
- Bar charts: customer revenue by state and city.
- Separate seller revenue by seller state/city.
- Use a map only if the visual geocodes the synthetic city/state fields reliably.

### Page 5 — Retention Analysis
- Import the cohort output CSV from the local `reports/generated` folder if available.
- Build a matrix with cohort month as rows and cohort age/month index as columns.
- Use retention percentage as values.
- Clearly label the metric as cohort activity/retention based on first delivered purchase.

## Formatting
- Use a descriptive title and small subtitle on every page.
- Use R$ in visual titles/subtitles if the locale does not offer Brazilian Real as a currency symbol.
- Set count measures to whole numbers; rate measures to percentage with 1–2 decimals.
- Set card display units to Auto or Thousands for revenue, and None for counts.
- Keep visual titles concise and axes labelled.
- Add page navigation only after all pages are created.

## Validation checklist

Compare the four KPI measures to the same refreshed database snapshot:
- Total Revenue = SUM(price + freight_value) for delivered order-item rows.
- Total Orders = DISTINCTCOUNT(order_id) for delivered rows.
- Total Customers = DISTINCTCOUNT(customer_unique_id) for delivered rows.
- Average Order Value = Total Revenue / Total Orders.

Then test:
- Select one category and confirm only its revenue changes.
- Select one state and confirm customer geography filters the fact rows.
- Check that one order with multiple item rows counts as one order.
- Confirm shipped/canceled orders are excluded from delivered KPIs.
- Confirm payments/reviews do not multiply revenue when used in visuals.

## Save and publish
Save the PBIX locally. Add genuine screenshots to `powerbi/screenshots/`. Do not commit credentials, raw generated data, or local database dumps.
