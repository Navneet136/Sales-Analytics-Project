"""
Phase 5 MySQL Analytical Verification Script.

Executes key analytical queries from sql/03_analytical_queries.sql against
`sales_analytics_db` using pymysql and prints formatted result tables.

Usage:
    python src/verify_phase5.py --user root --password <PASSWORD>
    Or set environment variables: MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT
"""

import argparse
import getpass
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pymysql


def parse_arguments() -> argparse.Namespace:
    """Parse MySQL connection parameters."""
    parser = argparse.ArgumentParser(
        description="Execute Phase 5 analytical verification queries against sales_analytics_db."
    )
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST", "localhost"), help="MySQL host (default: localhost)")
    parser.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT", 3306)), help="MySQL port (default: 3306)")
    parser.add_argument("--user", default=os.getenv("MYSQL_USER", "root"), help="MySQL user (default: root)")
    parser.add_argument(
        "--password",
        default=os.getenv("MYSQL_PASSWORD"),
        help="MySQL password (if omitted, prompts securely)",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("MYSQL_DATABASE", "sales_analytics_db"),
        help="Target MySQL database (default: sales_analytics_db)",
    )
    return parser.parse_args()


def get_connection(host: str, port: int, user: str, password: Optional[str], database: str) -> pymysql.Connection:
    """Create a pymysql connection using DictCursor."""
    if password is None:
        password = getpass.getpass(f"Enter MySQL password for user '{user}': ")

    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def format_value(val: Any) -> str:
    """Format numeric and nullable values consistently for terminal tables."""
    if val is None:
        return "NULL"
    return str(val)


def print_table(title: str, rows: List[Dict[str, Any]]) -> None:
    """Print query results as an ASCII table."""
    print(f"\n=== {title} ===")
    if not rows:
        print("(0 rows)")
        return

    headers = list(rows[0].keys())
    str_rows = [[format_value(row[h]) for h in headers] for row in rows]
    widths = [
        max(len(h), *(len(r[idx]) for r in str_rows))
        for idx, h in enumerate(headers)
    ]

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    header_line = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"

    print(sep)
    print(header_line)
    print(sep)
    for row in str_rows:
        print("| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(headers))) + " |")
    print(sep)


QUERIES: Sequence[Tuple[str, str]] = (
    (
        "1. Top 5 Products by Profit (from Query 9)",
        """
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            p.sub_category,
            SUM(f.quantity) AS units_sold,
            ROUND(SUM(f.sales), 2) AS total_sales,
            ROUND(SUM(f.profit), 2) AS total_profit,
            ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS profit_margin_pct
        FROM fact_sales f
        INNER JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.product_id, p.product_name, p.category, p.sub_category
        ORDER BY total_profit DESC
        LIMIT 5
        """,
    ),
    (
        "2. Top 5 Customers by Revenue (from Query 11)",
        """
        SELECT
            c.customer_id,
            c.customer_name,
            c.segment,
            COUNT(DISTINCT f.order_id) AS total_orders_placed,
            SUM(f.quantity) AS total_items_bought,
            ROUND(SUM(f.sales), 2) AS lifetime_sales,
            ROUND(SUM(f.profit), 2) AS lifetime_profit,
            ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS lifetime_margin_pct
        FROM fact_sales f
        INNER JOIN dim_customer c ON f.customer_key = c.customer_key
        GROUP BY c.customer_id, c.customer_name, c.segment
        ORDER BY lifetime_sales DESC
        LIMIT 5
        """,
    ),
    (
        "3. Year-over-Year (YoY) Sales & Profit Growth (based on Query 4)",
        """
        WITH annual AS (
            SELECT
                d.year,
                COUNT(DISTINCT f.order_id) AS total_orders,
                SUM(f.quantity) AS total_units_sold,
                ROUND(SUM(f.sales), 2) AS annual_sales,
                ROUND(SUM(f.profit), 2) AS annual_profit,
                ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS annual_margin_pct
            FROM fact_sales f
            INNER JOIN dim_date d ON f.order_date_key = d.date_key
            GROUP BY d.year
        )
        SELECT
            year,
            total_orders,
            total_units_sold,
            annual_sales,
            ROUND(
                (annual_sales - LAG(annual_sales) OVER (ORDER BY year)) * 100.0 /
                NULLIF(LAG(annual_sales) OVER (ORDER BY year), 0),
                2
            ) AS yoy_sales_growth_pct,
            annual_profit,
            ROUND(
                (annual_profit - LAG(annual_profit) OVER (ORDER BY year)) * 100.0 /
                NULLIF(LAG(annual_profit) OVER (ORDER BY year), 0),
                2
            ) AS yoy_profit_growth_pct,
            annual_margin_pct
        FROM annual
        ORDER BY year
        """,
    ),
    (
        "4a. Category Margin Analysis (Query 5)",
        """
        SELECT
            p.category,
            COUNT(DISTINCT f.order_id) AS total_orders,
            SUM(f.quantity) AS total_units_sold,
            ROUND(SUM(f.sales), 2) AS total_sales,
            ROUND(SUM(f.profit), 2) AS total_profit,
            ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS profit_margin_pct,
            ROUND((SUM(f.sales) * 100.0 / (SELECT SUM(sales) FROM fact_sales)), 2) AS sales_contribution_pct
        FROM fact_sales f
        INNER JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.category
        ORDER BY total_sales DESC
        """,
    ),
    (
        "4b. Sub-Category Margin Analysis (Query 6)",
        """
        SELECT
            p.category,
            p.sub_category,
            COUNT(*) AS total_transactions,
            ROUND(SUM(f.sales), 2) AS total_sales,
            ROUND(SUM(f.profit), 2) AS total_profit,
            ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS profit_margin_pct,
            ROUND(AVG(f.discount) * 100, 2) AS avg_discount_pct,
            CASE WHEN SUM(f.profit) < 0 THEN 'LOSS-MAKING' ELSE 'PROFITABLE' END AS commercial_health
        FROM fact_sales f
        INNER JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.category, p.sub_category
        ORDER BY total_profit ASC
        """,
    ),
)


def main() -> None:
    """Connect to MySQL and print all Phase 5 verification tables."""
    args = parse_arguments()
    conn = get_connection(args.host, args.port, args.user, args.password, args.database)
    try:
        with conn.cursor() as cursor:
            for title, sql in QUERIES:
                cursor.execute(sql)
                rows = cursor.fetchall()
                print_table(title, rows)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
