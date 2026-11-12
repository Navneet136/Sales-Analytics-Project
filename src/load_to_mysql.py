"""
Automated MySQL Database Ingestion and Validation Script.

This standalone utility executes Phase 4 database ingestion from Python without modifying
existing Phase 3 ETL files. It connects to MySQL, initializes the schema from
sql/01_create_database_and_tables.sql, populates all dimension and fact tables from
data/processed/clean_superstore.csv, and executes the reconciliation test suite.

Usage:
    python src/load_to_mysql.py --user root --password <PASSWORD> --host localhost --port 3306
    Or set environment variables: MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT
"""

import argparse
import getpass
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_arguments() -> argparse.Namespace:
    """Parse command line connection parameters."""
    parser = argparse.ArgumentParser(description="Ingest Clean Superstore Data into MySQL Star Schema.")
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST", "localhost"), help="MySQL host (default: localhost)")
    parser.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT", 3306)), help="MySQL port (default: 3306)")
    parser.add_argument("--user", default=os.getenv("MYSQL_USER", "root"), help="MySQL user (default: root)")
    parser.add_argument("--password", default=os.getenv("MYSQL_PASSWORD"), help="MySQL password (if omitted, will prompt securely)")
    parser.add_argument("--database", default=os.getenv("MYSQL_DATABASE", "sales_analytics_db"), help="Database name")
    return parser.parse_args()


def get_db_connection(host: str, port: int, user: str, password: Optional[str]):
    """Attempt connection using available Python MySQL drivers."""
    if password is None:
        password = getpass.getpass(f"Enter MySQL password for user '{user}': ")

    try:
        import pymysql
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        return conn, 'pymysql'
    except ImportError:
        pass

    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4',
            autocommit=True
        )
        return conn, 'mysql.connector'
    except ImportError:
        pass

    raise RuntimeError(
        "Neither 'pymysql' nor 'mysql-connector-python' is installed.\n"
        "Please run: pip install pymysql mysql-connector-python"
    )


def execute_sql_file(cursor, file_path: Path) -> None:
    """Execute multi-statement SQL script with proper comment stripping."""
    print(f"-> Executing SQL script: {file_path.name}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Split by semicolon
    statements = sql_content.split(';')
    for raw_stmt in statements:
        # Strip single-line comments and clean up whitespace
        lines = [line.strip() for line in raw_stmt.splitlines()]
        cleaned_lines = [line for line in lines if line and not line.startswith('--')]
        clean_stmt = ' '.join(cleaned_lines).strip()

        if clean_stmt:
            cursor.execute(clean_stmt)


def load_data_to_mysql(args: argparse.Namespace) -> None:
    """Main execution workflow for Phase 4 database ingestion."""
    print("=" * 70)
    print("     PHASE 4: MYSQL STAR SCHEMA INGESTION & VALIDATION        ")
    print("=" * 70)

    # 1. Connect
    print(f"\n[Step 1/5] Connecting to MySQL Server at {args.host}:{args.port} as '{args.user}'...")
    conn, driver_name = get_db_connection(args.host, args.port, args.user, args.password)
    print(f"-> Connected successfully using '{driver_name}'.")

    cursor = conn.cursor()

    # 2. Schema Creation
    schema_sql_path = PROJECT_ROOT / 'sql' / '01_create_database_and_tables.sql'
    print(f"\n[Step 2/5] Initializing database and tables from: {schema_sql_path.name}...")
    execute_sql_file(cursor, schema_sql_path)
    cursor.execute(f"USE {args.database};")
    print("-> Schema initialized: dim_date, dim_customer, dim_product, dim_location, fact_sales.")

    # 3. Read processed dataset
    clean_csv_path = PROJECT_ROOT / 'data' / 'processed' / 'clean_superstore.csv'
    print(f"\n[Step 3/5] Loading processed dataset: {clean_csv_path.name}...")
    df = pd.read_csv(clean_csv_path)
    print(f"-> Loaded {len(df):,} records with {len(df.columns)} columns.")

    # 4. Populate Dimensions
    print("\n[Step 4/5] Populating Dimensions & Fact Table...")

    # A. dim_date
    print("  a) Populating dim_date...")
    dates = pd.concat([pd.to_datetime(df['order_date']), pd.to_datetime(df['ship_date'])]).drop_duplicates().sort_values()
    date_records = []
    for d in dates:
        date_records.append((
            int(d.strftime('%Y%m%d')),
            d.strftime('%Y-%m-%d'),
            d.year,
            d.month,
            d.strftime('%B'),
            d.quarter,
            d.strftime('%A')
        ))
    cursor.executemany(
        """
        INSERT INTO dim_date (date_key, full_date, year, month, month_name, quarter, day_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        date_records
    )
    print(f"     -> Inserted {len(date_records):,} calendar records.")

    # B. dim_customer
    print("  b) Populating dim_customer...")
    customers = df[['customer_id', 'customer_name', 'segment']].drop_duplicates().sort_values('customer_id')
    cust_records = [tuple(x) for x in customers.to_numpy()]
    cursor.executemany(
        """
        INSERT INTO dim_customer (customer_id, customer_name, segment)
        VALUES (%s, %s, %s)
        """,
        cust_records
    )
    print(f"     -> Inserted {len(cust_records):,} customer records.")

    # Fetch customer surrogate mapping
    cursor.execute("SELECT customer_id, customer_key FROM dim_customer")
    cust_map = {row['customer_id']: row['customer_key'] for row in cursor.fetchall()}

    # C. dim_product
    print("  c) Populating dim_product...")
    products = df[['product_id', 'product_name', 'category', 'sub_category']].drop_duplicates().sort_values(['product_id', 'product_name'])
    prod_records = [tuple(x) for x in products.to_numpy()]
    cursor.executemany(
        """
        INSERT INTO dim_product (product_id, product_name, category, sub_category)
        VALUES (%s, %s, %s, %s)
        """,
        prod_records
    )
    print(f"     -> Inserted {len(prod_records):,} product records.")

    # Fetch product surrogate mapping
    cursor.execute("SELECT product_id, product_name, product_key FROM dim_product")
    prod_map = {(row['product_id'], row['product_name']): row['product_key'] for row in cursor.fetchall()}

    # D. dim_location
    print("  d) Populating dim_location...")
    locations = df[['country', 'city', 'state', 'postal_code', 'region']].drop_duplicates().sort_values(['state', 'city'])
    loc_records = [tuple(x) for x in locations.to_numpy()]
    cursor.executemany(
        """
        INSERT INTO dim_location (country, city, state, postal_code, region)
        VALUES (%s, %s, %s, %s, %s)
        """,
        loc_records
    )
    print(f"     -> Inserted {len(loc_records):,} location records.")

    # Fetch location surrogate mapping
    cursor.execute("SELECT country, city, state, postal_code, region, location_key FROM dim_location")
    loc_map = {(row['country'], row['city'], row['state'], str(row['postal_code']), row['region']): row['location_key'] for row in cursor.fetchall()}

    # E. fact_sales
    print("  e) Populating fact_sales (preserving all 9,994 rows & row_id 3406 / 3407)...")
    fact_records = []
    for _, r in df.iterrows():
        o_key = int(pd.to_datetime(r['order_date']).strftime('%Y%m%d'))
        s_key = int(pd.to_datetime(r['ship_date']).strftime('%Y%m%d'))
        c_key = cust_map[r['customer_id']]
        p_key = prod_map[(r['product_id'], r['product_name'])]
        l_key = loc_map[(r['country'], r['city'], r['state'], str(r['postal_code']), r['region'])]

        fact_records.append((
            int(r['row_id']),
            str(r['order_id']),
            o_key,
            s_key,
            c_key,
            p_key,
            l_key,
            str(r['ship_mode']),
            float(r['sales']),
            int(r['quantity']),
            float(r['discount']),
            float(r['profit']),
            float(r['total_cost']),
            float(r['unit_selling_price']),
            float(r['unit_cost']),
            float(r['profit_margin_pct']),
            int(r['shipping_duration_days'])
        ))

    cursor.executemany(
        """
        INSERT INTO fact_sales (
            row_id, order_id, order_date_key, ship_date_key,
            customer_key, product_key, location_key, ship_mode,
            sales, quantity, discount, profit, total_cost,
            unit_selling_price, unit_cost, profit_margin_pct,
            shipping_duration_days
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """,
        fact_records
    )
    print(f"     -> Inserted {len(fact_records):,} fact rows.")

    # 5. Create Views
    views_sql_path = PROJECT_ROOT / 'sql' / '04_views_for_powerbi.sql'
    print(f"\n[Step 5/5] Deploying analytical views from: {views_sql_path.name}...")
    execute_sql_file(cursor, views_sql_path)
    print("-> Views deployed: vw_sales_summary, vw_monthly_sales, vw_category_performance, "
          "vw_region_performance, vw_product_performance, vw_customer_performance.")

    # 6. Reconciliation Assertions
    print("\n" + "=" * 70)
    print("                   RECONCILIATION AUDIT RESULTS               ")
    print("=" * 70)

    cursor.execute("SELECT COUNT(*) AS c, COUNT(DISTINCT row_id) AS u FROM fact_sales")
    res = cursor.fetchone()
    print(f"fact_sales Total Rows:        {res['c']:,} (Expected: 9,994) -> {'PASS' if res['c'] == 9994 else 'FAIL'}")
    print(f"fact_sales Unique row_id:     {res['u']:,} (Expected: 9,994) -> {'PASS' if res['u'] == 9994 else 'FAIL'}")

    cursor.execute("SELECT COUNT(*) AS c FROM fact_sales WHERE row_id IN (3406, 3407)")
    r_3406 = cursor.fetchone()
    print(f"Row IDs 3406 & 3407 Retained: {r_3406['c']} (Expected: 2)     -> {'PASS' if r_3406['c'] == 2 else 'FAIL'}")

    cursor.execute("SELECT ROUND(SUM(sales), 2) AS s, ROUND(SUM(profit), 2) AS p, SUM(quantity) AS q FROM fact_sales")
    fin = cursor.fetchone()
    print(f"Total Sales ($):              {float(fin['s']):,.2f} (Expected: 2,297,200.86) -> {'PASS' if abs(float(fin['s']) - 2297200.86) < 0.01 else 'FAIL'}")
    print(f"Total Profit ($):             {float(fin['p']):,.2f} (Expected: 286,397.02)   -> {'PASS' if abs(float(fin['p']) - 286397.02) < 0.01 else 'FAIL'}")
    print(f"Total Units Sold:             {int(fin['q']):,} (Expected: 37,873)       -> {'PASS' if int(fin['q']) == 37873 else 'FAIL'}")

    conn.close()
    print("=" * 70)
    print("Phase 4 MySQL Database Ingestion Completed Successfully!\n")


if __name__ == '__main__':
    args = parse_arguments()
    load_data_to_mysql(args)
