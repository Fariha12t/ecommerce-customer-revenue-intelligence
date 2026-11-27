HOW TO OPEN
1. Keep EcommerceIntelligence.pbip, EcommerceIntelligence.Report and EcommerceIntelligence.SemanticModel together.
2. Double-click EcommerceIntelligence.pbip (opens in Power BI Desktop).
3. Home -> Refresh. Data loads from your CSV files via the DataFolder parameter, already set to:
   D:\Downloads D-Drive\ecommerce-customer-revenue-intelligence\ecommerce-customer-revenue-intelligence\
   (Change: Home -> Transform data -> Manage parameters -> DataFolder. Keep the trailing backslash.)
4. File -> Save as .pbix if you want a single file.

FILES USED (must exist under DataFolder)
  data\processed\fact_orders.csv, data\processed\fact_order_items.csv
  reports\generated\customer_rfm.csv, reports\generated\cohort_retention_long.csv
  reports\generated\ml\customer_scores.csv, reports\generated\ml_late\order_risk_scores.csv
