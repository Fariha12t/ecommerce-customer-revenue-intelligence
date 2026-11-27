HOW TO OPEN
1. Unzip this folder anywhere (keep the three items together).
2. Double-click EcommerceIntelligence.pbip  (opens in Power BI Desktop).
3. Home -> Refresh. Data loads from your CSV files using the DataFolder parameter,
   which is already set to:
   D:\Downloads D-Drive\ecommerce-customer-revenue-intelligence\ecommerce-customer-revenue-intelligence\
   (To change it: Home -> Transform data -> Manage parameters -> DataFolder. Keep the trailing backslash.)
4. File -> Save as .pbix if you want a single file.

FILES USED (must exist under DataFolder)
  data\processed\fact_orders.csv, data\processed\fact_order_items.csv
  reports\generated\customer_rfm.csv, reports\generated\cohort_retention_long.csv
  reports\generated\ml\customer_scores.csv, reports\generated\ml_late\order_risk_scores.csv

OPTIONAL POLISH
  Retention page: click the matrix -> Format -> Cell elements -> Background color -> fx -> gradient on Avg Retention.
