"""Load processed CSVs into PostgreSQL using SQLAlchemy."""
import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from src.config import PROCESSED_DIR

def main():
    load_dotenv()
    required = ["PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise EnvironmentError(f"Missing environment variables: {', '.join(missing)}. Copy .env.example to .env.")
    url = (
        f"postgresql+psycopg2://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}"
        f"@{os.getenv('PGHOST')}:{os.getenv('PGPORT', '5432')}/{os.getenv('PGDATABASE')}"
    )
    engine = create_engine(url)
    tables = {
        "orders": "orders",
        "order_items": "order_items",
        "payments": "payments",
        "reviews": "reviews",
        "customers": "customers",
        "products": "products",
        "sellers": "sellers",
        "fact_orders": "fact_orders",
        "fact_order_items": "fact_order_items",
    }
    for csv_name, table_name in tables.items():
        path = PROCESSED_DIR / f"{csv_name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"{path} not found. Run python -m src.etl first.")
        df = pd.read_csv(path)
        df.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=5000, method="multi")
        print(f"Loaded {table_name}: {len(df):,} rows")
    print("PostgreSQL load complete.")

if __name__ == "__main__":
    main()
