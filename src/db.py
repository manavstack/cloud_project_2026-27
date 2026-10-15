import os

import pandas as pd
import psycopg2
from dotenv import load_dotenv


# ============================================================
# Load environment variables
# ============================================================

load_dotenv()


# ============================================================
# PostgreSQL configuration
# ============================================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv(
        "DB_NAME",
        "cloud_uni_project_fedra"
    ),
    "user": os.getenv(
        "DB_USER",
        "postgres"
    ),
    "password": os.getenv(
        "DB_PASSWORD"
    )
}


# ============================================================
# Load category data
# ============================================================

def load_category_data(table_name):
    """
    Load energy consumption data from PostgreSQL.

    Allowed tables:
        academic
        residential
        others
    """

    allowed_tables = {
        "academic",
        "residential",
        "others"
    }

    if table_name not in allowed_tables:
        raise ValueError(
            f"Invalid table name: {table_name}"
        )

    connection = psycopg2.connect(
        **DB_CONFIG
    )

    query = f"""
        SELECT
            building,
            reading_time,
            consumption_kwh
        FROM {table_name}
        ORDER BY
            reading_time,
            building;
    """

    try:
        df = pd.read_sql_query(
            query,
            connection
        )

    finally:
        connection.close()

    return df


# ============================================================
# Database connection test
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("TESTING POSTGRESQL CONNECTION")
    print("=" * 60)

    for category in [
        "academic",
        "residential",
        "others"
    ]:

        df = load_category_data(
            category
        )

        print(
            f"{category}: {len(df)} rows"
        )

    print()
    print("Database connection successful.")
