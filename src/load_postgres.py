
"""Load processed CSV files into PostgreSQL."""
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from src.config import PROCESSED_DIR


def main():
    load_dotenv()

    required = ["PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD"]
    missing = [key for key in required if not os.getenv(key)]

    if missing:
        raise EnvironmentError(
            f"Missing environment variables: {', '.join(missing)}"
        )

    # URL.create safely handles special characters in passwords.
    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        host=os.getenv("PGHOST"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE"),
    )

    engine = create_engine(database_url)

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

    try:
        # Verify database connectivity first.
        with engine.connect():
            print("PostgreSQL connection successful!")

        for csv_name, table_name in tables.items():
            path = PROCESSED_DIR / f"{csv_name}.csv"

            if not path.exists():
                raise FileNotFoundError(
                    f"{path} not found. Run python -m src.etl first."
                )

            df = pd.read_csv(path)

            df.to_sql(
                table_name,
                engine,
                if_exists="replace",
                index=False,
                chunksize=1000,
                method="multi"
            )

            print(f"Loaded {table_name}: {len(df):,} rows")

        print("\nAll PostgreSQL tables loaded successfully!")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
