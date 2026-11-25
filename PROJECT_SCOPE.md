# Project Scope & Enhancements

## What is implemented
- Source-file validation and repeatable Python cleaning pipeline
- Deduplication and basic data-quality handling
- Order-level and order-item-level analytical tables
- Executive KPIs, monthly trends, category and state analysis
- RFM scoring and customer segments
- Customer cohort retention matrix
- PostgreSQL loading script and SQL analysis examples
- Power BI dashboard design, model guidance and DAX measures
- Notebook for exploration and business-insight prompts

## Deliberate design decisions
1. Olist is the primary dataset. Combining Olist with UCI Online Retail II would create incompatible business contexts and customer identifiers, so the datasets are not merged.
2. Gross value is defined as item price plus freight. It is not represented as audited accounting revenue.
3. Historical customer value is used as a simple CLV proxy. A predictive CLV model would require additional assumptions and validation.
4. The project does not claim automated email/report delivery or a published Power BI Service report. Those depend on credentials, licensing and deployment configuration.
5. The Power BI `.pbix` is a manual deliverable created in Power BI Desktop using the included blueprint and DAX.

## Suggested next enhancements
- Add dbt models and tests after the PostgreSQL layer is stable.
- Add anomaly detection for sudden revenue/category drops.
- Add a scheduled workflow with GitHub Actions or Airflow.
- Add a validated customer churn model only after defining a label and time-based train/test split.
