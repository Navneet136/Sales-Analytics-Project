"""
Phase 9 Power BI Offline Data Extract & View Verification Script.

Validates the view definitions in sql/04_views_for_powerbi.sql and exports the
Star Schema dimension/fact tables plus all 6 analytical views to CSV files in
powerbi/data_extracts/ so Power BI Desktop can load the model without requiring
live MySQL credentials on another machine.

Usage:
    python src/export_powerbi_views.py
"""

from pathlib import Path
import re
from typing import Dict, Tuple

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = PROJECT_ROOT / "data" / "processed" / "clean_superstore.parquet"
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "clean_superstore.csv"
VIEWS_SQL_PATH = PROJECT_ROOT / "sql" / "04_views_for_powerbi.sql"
EXTRACTS_DIR = PROJECT_ROOT / "powerbi" / "data_extracts"

EXPECTED_VIEWS = (
    "vw_sales_summary",
    "vw_monthly_sales",
    "vw_category_performance",
    "vw_region_performance",
    "vw_product_performance",
    "vw_customer_performance",
)


def load_data() -> pd.DataFrame:
    """Load processed Superstore dataset from Parquet, falling back to CSV."""
    if PARQUET_PATH.exists():
        df = pd.read_parquet(PARQUET_PATH)
    elif CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH)
    else:
        raise FileNotFoundError(f"Dataset not found at {PARQUET_PATH} or {CSV_PATH}.")
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["ship_date"] = pd.to_datetime(df["ship_date"])
    df["postal_code"] = df["postal_code"].astype(str).str.zfill(5)
    return df


def verify_views_sql(sql_path: Path) -> Tuple[str, ...]:
    """Verify that sql/04_views_for_powerbi.sql defines all expected analytical views."""
    if not sql_path.exists():
        raise FileNotFoundError(f"Missing SQL views file: {sql_path}")
    sql_text = sql_path.read_text(encoding="utf-8")
    found_views = tuple(re.findall(r"CREATE\s+VIEW\s+(\w+)\s+AS", sql_text, flags=re.IGNORECASE))
    missing = set(EXPECTED_VIEWS) - set(found_views)
    if missing:
        raise ValueError(f"Missing expected views in {sql_path.name}: {sorted(missing)}")
    return found_views


def build_star_schema(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Build Star Schema dimension and fact DataFrames matching sql/01_create_database_and_tables.sql."""
    all_dates = pd.concat([df["order_date"], df["ship_date"]]).drop_duplicates().sort_values()
    dim_date = pd.DataFrame({
        "date_key": all_dates.dt.strftime("%Y%m%d").astype(int),
        "full_date": all_dates.dt.strftime("%Y-%m-%d"),
        "year": all_dates.dt.year,
        "month": all_dates.dt.month,
        "month_name": all_dates.dt.strftime("%B"),
        "quarter": all_dates.dt.quarter,
        "day_name": all_dates.dt.strftime("%A"),
    }).reset_index(drop=True)

    dim_customer = (
        df[["customer_id", "customer_name", "segment"]]
        .drop_duplicates()
        .sort_values("customer_id")
        .reset_index(drop=True)
    )
    dim_customer.insert(0, "customer_key", range(1, len(dim_customer) + 1))

    dim_product = (
        df[["product_id", "product_name", "category", "sub_category"]]
        .drop_duplicates()
        .sort_values(["product_id", "product_name"])
        .reset_index(drop=True)
    )
    dim_product.insert(0, "product_key", range(1, len(dim_product) + 1))

    dim_location = (
        df[["country", "city", "state", "postal_code", "region"]]
        .drop_duplicates()
        .sort_values(["state", "city"])
        .reset_index(drop=True)
    )
    dim_location.insert(0, "location_key", range(1, len(dim_location) + 1))

    fact_merged = (
        df.merge(dim_customer[["customer_key", "customer_id"]], on="customer_id", how="left")
        .merge(dim_product[["product_key", "product_id", "product_name"]], on=["product_id", "product_name"], how="left")
        .merge(
            dim_location[["location_key", "country", "city", "state", "postal_code", "region"]],
            on=["country", "city", "state", "postal_code", "region"],
            how="left",
        )
    )

    fact_sales = pd.DataFrame({
        "row_id": fact_merged["row_id"].astype(int),
        "order_id": fact_merged["order_id"],
        "order_date_key": fact_merged["order_date"].dt.strftime("%Y%m%d").astype(int),
        "ship_date_key": fact_merged["ship_date"].dt.strftime("%Y%m%d").astype(int),
        "customer_key": fact_merged["customer_key"].astype(int),
        "product_key": fact_merged["product_key"].astype(int),
        "location_key": fact_merged["location_key"].astype(int),
        "ship_mode": fact_merged["ship_mode"],
        "sales": fact_merged["sales"].round(4),
        "quantity": fact_merged["quantity"].astype(int),
        "discount": fact_merged["discount"].round(4),
        "profit": fact_merged["profit"].round(4),
        "total_cost": fact_merged["total_cost"].round(4),
        "unit_selling_price": fact_merged["unit_selling_price"].round(4),
        "unit_cost": fact_merged["unit_cost"].round(4),
        "profit_margin_pct": fact_merged["profit_margin_pct"].round(4),
        "shipping_duration_days": fact_merged["shipping_duration_days"].astype(int),
    })

    return {
        "dim_date": dim_date,
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_location": dim_location,
        "fact_sales": fact_sales,
    }


def build_analytical_views(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Replicate all 6 analytical views from sql/04_views_for_powerbi.sql."""
    vw_sales_summary = pd.DataFrame({
        "row_id": df["row_id"].astype(int),
        "order_id": df["order_id"],
        "order_date": df["order_date"].dt.strftime("%Y-%m-%d"),
        "order_year": df["order_year"],
        "order_quarter": df["order_quarter"],
        "order_month": df["order_month"],
        "order_month_name": df["order_month_name"],
        "order_day_name": df["order_day_name"],
        "ship_date": df["ship_date"].dt.strftime("%Y-%m-%d"),
        "shipping_duration_days": df["shipping_duration_days"].astype(int),
        "ship_mode": df["ship_mode"],
        "customer_id": df["customer_id"],
        "customer_name": df["customer_name"],
        "customer_segment": df["segment"],
        "product_id": df["product_id"],
        "product_name": df["product_name"],
        "product_category": df["category"],
        "product_sub_category": df["sub_category"],
        "country": df["country"],
        "city": df["city"],
        "state": df["state"],
        "postal_code": df["postal_code"],
        "region": df["region"],
        "sales": df["sales"],
        "quantity": df["quantity"],
        "discount": df["discount"],
        "profit": df["profit"],
        "total_cost": df["total_cost"],
        "unit_selling_price": df["unit_selling_price"],
        "unit_cost": df["unit_cost"],
        "profit_margin_pct": df["profit_margin_pct"],
        "is_loss_order": (df["profit"] < 0).astype(int),
    })

    vw_monthly_sales = (
        df.groupby(["order_year", "order_month", "order_month_name"], as_index=False)
        .agg(
            total_sales=("sales", "sum"),
            total_profit=("profit", "sum"),
            total_cogs=("total_cost", "sum"),
            total_units_sold=("quantity", "sum"),
            total_orders=("order_id", "nunique"),
            active_customers=("customer_id", "nunique"),
            avg_discount_pct=("discount", "mean"),
        )
        .sort_values(["order_year", "order_month"])
    )
    vw_monthly_sales["year_month_label"] = (
        vw_monthly_sales["order_year"].astype(str) + "-" + vw_monthly_sales["order_month"].astype(str).str.zfill(2)
    )
    vw_monthly_sales["profit_margin_pct"] = ((vw_monthly_sales["total_profit"] / vw_monthly_sales["total_sales"]) * 100).round(2)
    vw_monthly_sales["avg_discount_pct"] = (vw_monthly_sales["avg_discount_pct"] * 100).round(2)
    for col in ("total_sales", "total_profit", "total_cogs"):
        vw_monthly_sales[col] = vw_monthly_sales[col].round(2)
    vw_monthly_sales = vw_monthly_sales[
        [
            "order_year", "order_month", "order_month_name", "year_month_label",
            "total_sales", "total_profit", "total_cogs", "total_units_sold",
            "total_orders", "active_customers", "profit_margin_pct", "avg_discount_pct",
        ]
    ]

    vw_category_performance = (
        df.groupby(["category", "sub_category"], as_index=False)
        .agg(
            total_transactions=("row_id", "count"),
            total_orders=("order_id", "nunique"),
            total_units_sold=("quantity", "sum"),
            total_sales=("sales", "sum"),
            total_profit=("profit", "sum"),
            total_cost=("total_cost", "sum"),
            avg_discount_pct=("discount", "mean"),
            loss_transactions_count=("profit", lambda s: int((s < 0).sum())),
        )
    )
    vw_category_performance["profit_margin_pct"] = ((vw_category_performance["total_profit"] / vw_category_performance["total_sales"]) * 100).round(2)
    vw_category_performance["avg_discount_pct"] = (vw_category_performance["avg_discount_pct"] * 100).round(2)
    vw_category_performance["loss_rate_pct"] = (
        vw_category_performance["loss_transactions_count"] * 100.0 / vw_category_performance["total_transactions"]
    ).round(2)
    for col in ("total_sales", "total_profit", "total_cost"):
        vw_category_performance[col] = vw_category_performance[col].round(2)

    vw_region_performance = (
        df.groupby(["region", "state", "city"], as_index=False)
        .agg(
            total_orders=("order_id", "nunique"),
            unique_customers=("customer_id", "nunique"),
            total_units=("quantity", "sum"),
            total_sales=("sales", "sum"),
            total_profit=("profit", "sum"),
            avg_discount_pct=("discount", "mean"),
        )
    )
    vw_region_performance["profit_margin_pct"] = ((vw_region_performance["total_profit"] / vw_region_performance["total_sales"]) * 100).round(2)
    vw_region_performance["avg_discount_pct"] = (vw_region_performance["avg_discount_pct"] * 100).round(2)
    for col in ("total_sales", "total_profit"):
        vw_region_performance[col] = vw_region_performance[col].round(2)

    vw_product_performance = (
        df.groupby(["product_id", "product_name", "category", "sub_category"], as_index=False)
        .agg(
            total_orders_count=("row_id", "count"),
            total_units_sold=("quantity", "sum"),
            total_sales=("sales", "sum"),
            total_profit=("profit", "sum"),
            avg_discount_pct=("discount", "mean"),
        )
    )
    vw_product_performance["profit_margin_pct"] = ((vw_product_performance["total_profit"] / vw_product_performance["total_sales"]) * 100).round(2)
    vw_product_performance["avg_discount_pct"] = (vw_product_performance["avg_discount_pct"] * 100).round(2)
    vw_product_performance["profitability_tier"] = vw_product_performance["total_profit"].apply(
        lambda p: "Loss Maker" if p < 0 else "Profitable"
    )
    for col in ("total_sales", "total_profit"):
        vw_product_performance[col] = vw_product_performance[col].round(2)

    ref_date = pd.Timestamp("2017-12-31")
    vw_customer_performance = (
        df.groupby(["customer_id", "customer_name", "segment"], as_index=False)
        .agg(
            total_orders_placed=("order_id", "nunique"),
            total_units_purchased=("quantity", "sum"),
            lifetime_sales=("sales", "sum"),
            lifetime_profit=("profit", "sum"),
            first_order_date=("order_date", "min"),
            last_order_date=("order_date", "max"),
        )
    )
    vw_customer_performance["lifetime_margin_pct"] = (
        (vw_customer_performance["lifetime_profit"] / vw_customer_performance["lifetime_sales"]) * 100
    ).round(2)
    vw_customer_performance["avg_order_value_usd"] = (
        vw_customer_performance["lifetime_sales"] / vw_customer_performance["total_orders_placed"]
    ).round(2)
    vw_customer_performance["recency_days"] = (ref_date - vw_customer_performance["last_order_date"]).dt.days
    vw_customer_performance["first_order_date"] = vw_customer_performance["first_order_date"].dt.strftime("%Y-%m-%d")
    vw_customer_performance["last_order_date"] = vw_customer_performance["last_order_date"].dt.strftime("%Y-%m-%d")
    for col in ("lifetime_sales", "lifetime_profit"):
        vw_customer_performance[col] = vw_customer_performance[col].round(2)

    return {
        "vw_sales_summary": vw_sales_summary,
        "vw_monthly_sales": vw_monthly_sales,
        "vw_category_performance": vw_category_performance,
        "vw_region_performance": vw_region_performance,
        "vw_product_performance": vw_product_performance,
        "vw_customer_performance": vw_customer_performance,
    }


def main() -> None:
    """Validate SQL view definitions and export Star Schema & view CSVs for Power BI."""
    EXTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    verified_views = verify_views_sql(VIEWS_SQL_PATH)
    print(f"Verified SQL views in {VIEWS_SQL_PATH.name}: {list(verified_views)}")

    df = load_data()
    tables = {}
    tables.update(build_star_schema(df))
    tables.update(build_analytical_views(df))

    for name, table_df in tables.items():
        out_path = EXTRACTS_DIR / f"{name}.csv"
        table_df.to_csv(out_path, index=False, encoding="utf-8")
        print(f"Exported {name}.csv: {len(table_df):,} rows x {len(table_df.columns)} cols ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
