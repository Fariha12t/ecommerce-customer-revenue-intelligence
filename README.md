# Enterprise E-Commerce Customer & Revenue Intelligence Platform

An end-to-end analytics project that turns e-commerce transactions into business-ready insights. It covers data quality, Python ETL, PostgreSQL analytics, customer segmentation, retention, revenue KPIs, and a Power BI dashboard blueprint.

## Business questions
- Which products and categories contribute most to revenue?
- How are revenue, orders, and average order value changing over time?
- Which customers are repeat buyers, and which may be at risk?
- Which states and cities contribute most to sales?
- How does customer retention change by acquisition month?
- Which customers have the strongest historical value?

## Technology
Python (Pandas, NumPy), PostgreSQL, SQL, Plotly, Power BI and DAX.

## Project structure
```text
├── data/
│   ├── raw/                 # Put the original Olist CSV files here (not committed)
│   └── processed/           # Generated clean tables (not committed)
├── notebooks/
│   └── exploratory_analysis.ipynb
├── powerbi/
│   ├── dashboard_blueprint.md
│   └── measures.dax
├── reports/
│   └── business_insights_template.md
├── sql/
│   ├── schema.sql
│   └── analysis_queries.sql
├── src/
│   ├── config.py
│   ├── etl.py
│   ├── analytics.py
│   └── load_postgres.py
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

## 1. Get the dataset
Use the **Brazilian E-Commerce Public Dataset by Olist** from Kaggle:
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Download and extract the CSV files into `data/raw/`. The project expects these standard Olist filenames:
- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_order_payments_dataset.csv`
- `olist_order_reviews_dataset.csv`
- `olist_customers_dataset.csv`
- `olist_products_dataset.csv`
- `olist_sellers_dataset.csv`
- `product_category_name_translation.csv`

The raw dataset is not included in this repository. Follow the dataset's licence and terms, and do not commit the raw files to GitHub.

## 2. Set up Python
Python 3.10+ is recommended.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## 3. Run the pipeline
From the repository root:

```bash
python -m src.etl
python -m src.analytics
```

Cleaned CSV tables and analysis outputs will be written to `data/processed/` and `reports/generated/`.

## 4. Optional: load into PostgreSQL
Create a database, for example `ecommerce_intelligence`, then copy `.env.example` to `.env` and update the credentials.

```bash
psql -U postgres -d ecommerce_intelligence -f sql/schema.sql
python -m src.load_postgres
```

The loader creates/replaces the project tables from processed CSVs. Keep `.env` private.

## 5. Explore the notebook
Open `notebooks/exploratory_analysis.ipynb` in Jupyter or VS Code after running the ETL. The notebook reads the processed tables.

## 6. Build the Power BI report
Follow `powerbi/dashboard_blueprint.md` and use the DAX measures in `powerbi/measures.dax`. Connect Power BI Desktop to PostgreSQL or import the processed CSVs.

**Note:** A `.pbix` file is not generated automatically because it must be authored and validated in Power BI Desktop. The repository includes the model plan, report layout and measures to build it.

## Data model
The recommended reporting model is a star schema:
- `fact_order_items` — one row per order item
- `dim_customers` — one row per customer
- `dim_products` — one row per product
- `dim_sellers` — one row per seller
- `dim_date` — calendar table created in Power BI
- `fact_orders` — one row per order
- `fact_payments` — one row per payment record

Use `order_id`, `customer_id`, `product_id`, and `seller_id` as keys. The SQL schema retains the source entities as well as analytics-ready views.

## Important metric definitions
- **Revenue:** sum of item price plus freight value. This is gross merchandise value represented by order items, not accounting revenue.
- **Orders:** distinct delivered orders unless a query explicitly states otherwise.
- **AOV:** item revenue plus freight divided by distinct delivered orders.
- **Repeat customer:** customer with at least two delivered orders.
- **RFM:** recency, frequency and monetary scores based on delivered orders; monetary value uses item price plus freight.
- **Cohort:** month of a customer's first delivered order.

Metrics are explicitly defined so that the same KPI is not calculated differently across visuals.

## Quality checks and limitations
- Cancelled and unavailable orders are excluded from delivered-order customer and revenue metrics.
- The source has multiple rows per order in items, payments and reviews. Do not join all raw tables together before aggregation; this can multiply values.
- Olist is a historical Brazilian marketplace dataset. Results describe this dataset and should not be presented as current market trends.
- CLV in this project is a transparent historical-value proxy, not a predictive lifetime-value model.
- Missing product categories are labelled `Unknown`; missing timestamps remain null and are excluded from time-based calculations.

## GitHub publishing checklist
1. Review `.gitignore` and keep `.env` and raw data out of Git.
2. Add your own screenshots to `powerbi/screenshots/`.
3. Run the ETL and analytics scripts.
4. Build and validate the Power BI report.
5. Update the business insights report with actual findings from your run.
6. Commit the project and push it to your GitHub repository.

## Suggested resume description
**E-Commerce Customer & Revenue Intelligence Platform** — Built an end-to-end analytics workflow using Python, PostgreSQL and Power BI to clean marketplace data, calculate sales KPIs, segment customers using RFM, and analyse repeat purchasing and cohort retention. Developed SQL analysis queries and an executive dashboard specification to translate transaction data into business recommendations.

Only claim dashboard implementation after you have built and validated the `.pbix` report.
