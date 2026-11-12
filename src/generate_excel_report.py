"""
Phase 8 Automated Executive Excel Reporting Script.

Reads the processed Superstore dataset (Parquet with CSV fallback) and builds
a formatted multi-sheet Excel workbook at reports/Executive_Sales_Report.xlsx
using pandas and openpyxl.

Usage:
    python src/generate_excel_report.py
"""

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = PROJECT_ROOT / "data" / "processed" / "clean_superstore.parquet"
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "clean_superstore.csv"
OUTPUT_PATH = PROJECT_ROOT / "reports" / "Executive_Sales_Report.xlsx"

# Shared styling palette
NAVY_FILL = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
SECTION_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
ZEBRA_FILL = PatternFill(start_color="F7F9FC", end_color="F7F9FC", fill_type="solid")
LOSS_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="1B365D")
SECTION_FONT = Font(name="Calibri", size=11, bold=True, color="1B365D")
BODY_FONT = Font(name="Calibri", size=10, color="1F2937")
LOSS_FONT = Font(name="Calibri", size=10, bold=True, color="9C0006")

THIN_GRAY = Side(border_style="thin", color="D1D5DB")
CELL_BORDER = Border(left=THIN_GRAY, right=THIN_GRAY, top=THIN_GRAY, bottom=THIN_GRAY)

FMT_CURRENCY = "$#,##0.00;($#,##0.00);\"-\""
FMT_PERCENT = "0.00%"
FMT_INTEGER = "#,##0"
FMT_DECIMAL = "#,##0.00"


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
    return df


def write_banner(ws: openpyxl.worksheet.worksheet.Worksheet, title: str, row: int = 1) -> int:
    """Write a styled sheet or section banner and return the next available row."""
    cell = ws.cell(row=row, column=1, value=title)
    cell.font = TITLE_FONT if row == 1 else SECTION_FONT
    cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[row].height = 24 if row == 1 else 20
    return row + 1


def write_styled_table(
    ws: openpyxl.worksheet.worksheet.Worksheet,
    df: pd.DataFrame,
    start_row: int,
    col_formats: Dict[str, str],
    highlight_loss_cols: Sequence[str] = (),
    highlight_status_col: Optional[str] = None,
) -> int:
    """Write a DataFrame to an openpyxl worksheet with header, number, and loss styling."""
    headers = list(df.columns)
    ws.row_dimensions[start_row].height = 24

    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=start_row, column=col_idx, value=header)
        cell.fill = NAVY_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = CELL_BORDER

    for row_offset, (_, row_series) in enumerate(df.iterrows(), start=1):
        excel_row = start_row + row_offset
        ws.row_dimensions[excel_row].height = 20

        is_loss_row = any(
            pd.notna(row_series[col]) and float(row_series[col]) < 0
            for col in highlight_loss_cols
            if col in df.columns
        )
        if highlight_status_col and highlight_status_col in df.columns:
            if str(row_series[highlight_status_col]).strip().lower() == "loss-making":
                is_loss_row = True

        for col_idx, col_name in enumerate(headers, start=1):
            val = row_series[col_name]
            if pd.isna(val):
                val = None
            elif hasattr(val, "item"):
                val = val.item()

            cell = ws.cell(row=excel_row, column=col_idx, value=val)
            cell.border = CELL_BORDER
            fmt = col_formats.get(col_name)
            if fmt:
                cell.number_format = fmt
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

            if is_loss_row:
                cell.fill = LOSS_FILL
                cell.font = LOSS_FONT
            else:
                if row_offset % 2 == 0:
                    cell.fill = ZEBRA_FILL
                cell.font = BODY_FONT

    return start_row + len(df) + 2


def auto_fit_columns(ws: openpyxl.worksheet.worksheet.Worksheet, min_width: int = 12, max_width: int = 44) -> None:
    """Auto-adjust column widths based on cell values, skipping wide banner rows."""
    for col_cells in ws.columns:
        col_letter = get_column_letter(col_cells[0].column)
        max_len = 0
        for cell in col_cells:
            if cell.row == 1 and cell.column == 1:
                continue
            val = cell.value
            if val is None:
                continue
            text = f"{val:,.2f}" if isinstance(val, float) else str(val)
            max_len = max(max_len, len(text))
        ws.column_dimensions[col_letter].width = max(min_width, min(max_len + 4, max_width))


def build_executive_summary(wb: openpyxl.Workbook, df: pd.DataFrame) -> None:
    """Create Sheet 1: Executive_Summary with KPI scorecard and YoY Annual Growth."""
    ws = wb.create_sheet(title="Executive_Summary")
    row = write_banner(ws, "Executive Sales Report — KPI Scorecard & Annual Trajectory", row=1)
    row += 1

    total_sales = float(df["sales"].sum())
    total_profit = float(df["profit"].sum())
    total_orders = int(df["order_id"].nunique())
    total_units = int(df["quantity"].sum())
    avg_order_value = total_sales / total_orders
    overall_margin = total_profit / total_sales
    avg_shipping_days = float(df["shipping_duration_days"].mean())

    kpi_rows = [
        ("Total Sales", total_sales, FMT_CURRENCY),
        ("Total Profit", total_profit, FMT_CURRENCY),
        ("Overall Margin %", overall_margin, FMT_PERCENT),
        ("Total Orders", total_orders, FMT_INTEGER),
        ("Total Units Sold", total_units, FMT_INTEGER),
        ("Average Order Value (AOV)", avg_order_value, FMT_CURRENCY),
        ("Average Shipping Days", avg_shipping_days, FMT_DECIMAL),
    ]

    row = write_banner(ws, "High-Level KPI Scorecard (2014–2017)", row=row)
    for col_idx, header in enumerate(["KPI Metric", "Value"], start=1):
        c = ws.cell(row=row, column=col_idx, value=header)
        c.fill = NAVY_FILL
        c.font = HEADER_FONT
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = CELL_BORDER
    ws.row_dimensions[row].height = 24
    row += 1

    for idx, (label, val, num_fmt) in enumerate(kpi_rows, start=1):
        ws.row_dimensions[row].height = 20
        c1 = ws.cell(row=row, column=1, value=label)
        c2 = ws.cell(row=row, column=2, value=val)
        c1.font = Font(name="Calibri", size=10, bold=True, color="1F2937")
        c2.font = BODY_FONT
        c2.number_format = num_fmt
        c1.alignment = Alignment(horizontal="left", vertical="center")
        c2.alignment = Alignment(horizontal="right", vertical="center")
        for c in (c1, c2):
            c.border = CELL_BORDER
            if idx % 2 == 0:
                c.fill = ZEBRA_FILL
        row += 1

    row += 1
    row = write_banner(ws, "Year-over-Year (YoY) Annual Growth Summary", row=row)

    yoy = (
        df.groupby("order_year", as_index=False)
        .agg(
            Orders=("order_id", "nunique"),
            Units=("quantity", "sum"),
            Sales=("sales", "sum"),
            Profit=("profit", "sum"),
        )
        .sort_values("order_year")
        .rename(columns={"order_year": "Year"})
    )
    yoy["Margin %"] = yoy["Profit"] / yoy["Sales"]
    yoy["YoY Sales Growth %"] = yoy["Sales"].pct_change()
    yoy["YoY Profit Growth %"] = yoy["Profit"].pct_change()

    write_styled_table(
        ws,
        yoy,
        start_row=row,
        col_formats={
            "Year": "0",
            "Orders": FMT_INTEGER,
            "Units": FMT_INTEGER,
            "Sales": FMT_CURRENCY,
            "Profit": FMT_CURRENCY,
            "Margin %": FMT_PERCENT,
            "YoY Sales Growth %": FMT_PERCENT,
            "YoY Profit Growth %": FMT_PERCENT,
        },
        highlight_loss_cols=("Profit",),
    )
    auto_fit_columns(ws)


def build_category_performance(wb: openpyxl.Workbook, df: pd.DataFrame) -> None:
    """Create Sheet 2: Category_Performance breakdown by Category and Sub-Category."""
    ws = wb.create_sheet(title="Category_Performance")
    row = write_banner(ws, "Category & Sub-Category Profitability Breakdown", row=1)
    row += 1

    cat_df = (
        df.groupby(["category", "sub_category"], as_index=False)
        .agg(
            Orders=("order_id", "nunique"),
            Units=("quantity", "sum"),
            Sales=("sales", "sum"),
            Profit=("profit", "sum"),
            Avg_Discount=("discount", "mean"),
        )
        .rename(columns={"category": "Category", "sub_category": "Sub-Category", "Avg_Discount": "Average Discount %"})
    )
    cat_df["Margin %"] = cat_df["Profit"] / cat_df["Sales"]
    cat_df["Status"] = cat_df["Profit"].apply(lambda p: "Loss-Making" if p < 0 else "Profitable")
    cat_df = cat_df[
        ["Category", "Sub-Category", "Orders", "Units", "Sales", "Profit", "Margin %", "Average Discount %", "Status"]
    ].sort_values(["Category", "Profit"], ascending=[True, False])

    write_styled_table(
        ws,
        cat_df,
        start_row=row,
        col_formats={
            "Orders": FMT_INTEGER,
            "Units": FMT_INTEGER,
            "Sales": FMT_CURRENCY,
            "Profit": FMT_CURRENCY,
            "Margin %": FMT_PERCENT,
            "Average Discount %": FMT_PERCENT,
        },
        highlight_loss_cols=("Profit",),
        highlight_status_col="Status",
    )
    auto_fit_columns(ws)


def build_regional_segments(wb: openpyxl.Workbook, df: pd.DataFrame) -> None:
    """Create Sheet 3: Regional_Segments profitability matrix."""
    ws = wb.create_sheet(title="Regional_Segments")
    row = write_banner(ws, "Regional & Customer Segment Profitability Matrix", row=1)
    row += 1

    reg_seg = (
        df.groupby(["region", "segment"], as_index=False)
        .agg(
            Customers=("customer_id", "nunique"),
            Orders=("order_id", "nunique"),
            Units=("quantity", "sum"),
            Sales=("sales", "sum"),
            Profit=("profit", "sum"),
            Avg_Discount=("discount", "mean"),
        )
        .rename(columns={"region": "Region", "segment": "Segment", "Avg_Discount": "Average Discount %"})
    )
    reg_seg["Margin %"] = reg_seg["Profit"] / reg_seg["Sales"]
    reg_seg = reg_seg[
        ["Region", "Segment", "Customers", "Orders", "Units", "Sales", "Profit", "Margin %", "Average Discount %"]
    ].sort_values(["Region", "Sales"], ascending=[True, False])

    row = write_banner(ws, "Region x Customer Segment Matrix", row=row)
    row = write_styled_table(
        ws,
        reg_seg,
        start_row=row,
        col_formats={
            "Customers": FMT_INTEGER,
            "Orders": FMT_INTEGER,
            "Units": FMT_INTEGER,
            "Sales": FMT_CURRENCY,
            "Profit": FMT_CURRENCY,
            "Margin %": FMT_PERCENT,
            "Average Discount %": FMT_PERCENT,
        },
        highlight_loss_cols=("Profit",),
    )

    reg_summary = (
        df.groupby("region", as_index=False)
        .agg(
            Orders=("order_id", "nunique"),
            Sales=("sales", "sum"),
            Profit=("profit", "sum"),
            Avg_Discount=("discount", "mean"),
        )
        .rename(columns={"region": "Region", "Avg_Discount": "Average Discount %"})
    )
    reg_summary["Margin %"] = reg_summary["Profit"] / reg_summary["Sales"]
    reg_summary = reg_summary[["Region", "Orders", "Sales", "Profit", "Margin %", "Average Discount %"]].sort_values(
        "Sales", ascending=False
    )

    row = write_banner(ws, "Regional Totals Summary", row=row)
    write_styled_table(
        ws,
        reg_summary,
        start_row=row,
        col_formats={
            "Orders": FMT_INTEGER,
            "Sales": FMT_CURRENCY,
            "Profit": FMT_CURRENCY,
            "Margin %": FMT_PERCENT,
            "Average Discount %": FMT_PERCENT,
        },
        highlight_loss_cols=("Profit",),
    )
    auto_fit_columns(ws)


def build_top_performers(wb: openpyxl.Workbook, df: pd.DataFrame) -> None:
    """Create Sheet 4: Top_Performers (Top 15 Products by Profit & Top 15 Customers by Revenue)."""
    ws = wb.create_sheet(title="Top_Performers")
    row = write_banner(ws, "Top 15 Most Profitable Products & Top 15 Highest-Revenue Customers", row=1)
    row += 1

    top_products = (
        df.groupby(["product_id", "product_name", "category", "sub_category"], as_index=False)
        .agg(
            Units=("quantity", "sum"),
            Sales=("sales", "sum"),
            Profit=("profit", "sum"),
        )
        .rename(
            columns={
                "product_id": "Product ID",
                "product_name": "Product Name",
                "category": "Category",
                "sub_category": "Sub-Category",
            }
        )
    )
    top_products["Margin %"] = top_products["Profit"] / top_products["Sales"]
    top_products = top_products.sort_values("Profit", ascending=False).head(15)

    row = write_banner(ws, "Top 15 Most Profitable Products", row=row)
    row = write_styled_table(
        ws,
        top_products,
        start_row=row,
        col_formats={
            "Units": FMT_INTEGER,
            "Sales": FMT_CURRENCY,
            "Profit": FMT_CURRENCY,
            "Margin %": FMT_PERCENT,
        },
        highlight_loss_cols=("Profit",),
    )

    top_customers = (
        df.groupby(["customer_id", "customer_name", "segment"], as_index=False)
        .agg(
            Orders=("order_id", "nunique"),
            Units=("quantity", "sum"),
            Sales=("sales", "sum"),
            Profit=("profit", "sum"),
        )
        .rename(
            columns={
                "customer_id": "Customer ID",
                "customer_name": "Customer Name",
                "segment": "Segment",
            }
        )
    )
    top_customers["Margin %"] = top_customers["Profit"] / top_customers["Sales"]
    top_customers = top_customers.sort_values("Sales", ascending=False).head(15)

    row = write_banner(ws, "Top 15 Highest-Revenue Customers", row=row)
    write_styled_table(
        ws,
        top_customers,
        start_row=row,
        col_formats={
            "Orders": FMT_INTEGER,
            "Units": FMT_INTEGER,
            "Sales": FMT_CURRENCY,
            "Profit": FMT_CURRENCY,
            "Margin %": FMT_PERCENT,
        },
        highlight_loss_cols=("Profit",),
    )
    auto_fit_columns(ws)


def build_loss_leakage_audit(wb: openpyxl.Workbook, df: pd.DataFrame) -> None:
    """Create Sheet 5: Loss_Leakage_Audit for Discount > 20% loss-making sub-categories and orders."""
    ws = wb.create_sheet(title="Loss_Leakage_Audit")
    row = write_banner(ws, "Margin Leakage Audit — Sub-Categories & Orders with Discount > 20% & Negative Profit", row=1)
    row += 1

    leakage_lines = df[(df["discount"] > 0.20) & (df["profit"] < 0)].copy()

    subcat_leakage = (
        leakage_lines.groupby(["category", "sub_category"], as_index=False)
        .agg(
            Loss_Line_Items=("row_id", "count"),
            Affected_Orders=("order_id", "nunique"),
            Sales=("sales", "sum"),
            Profit=("profit", "sum"),
            Avg_Discount=("discount", "mean"),
        )
        .rename(
            columns={
                "category": "Category",
                "sub_category": "Sub-Category",
                "Loss_Line_Items": "Loss Line Items",
                "Affected_Orders": "Affected Orders",
                "Avg_Discount": "Average Discount %",
            }
        )
        .sort_values("Profit", ascending=True)
    )
    subcat_leakage["Margin %"] = subcat_leakage["Profit"] / subcat_leakage["Sales"]

    row = write_banner(ws, "Sub-Category Loss Leakage Summary (Discount > 20% & Profit < $0)", row=row)
    row = write_styled_table(
        ws,
        subcat_leakage,
        start_row=row,
        col_formats={
            "Loss Line Items": FMT_INTEGER,
            "Affected Orders": FMT_INTEGER,
            "Sales": FMT_CURRENCY,
            "Profit": FMT_CURRENCY,
            "Average Discount %": FMT_PERCENT,
            "Margin %": FMT_PERCENT,
        },
        highlight_loss_cols=("Profit",),
    )

    order_leakage = (
        leakage_lines.groupby(["order_id", "order_date", "customer_name", "region", "state", "city"], as_index=False)
        .agg(
            Line_Items=("row_id", "count"),
            Sales=("sales", "sum"),
            Profit=("profit", "sum"),
            Max_Discount=("discount", "max"),
            Avg_Discount=("discount", "mean"),
        )
        .rename(
            columns={
                "order_id": "Order ID",
                "order_date": "Order Date",
                "customer_name": "Customer Name",
                "region": "Region",
                "state": "State",
                "city": "City",
                "Line_Items": "Loss Items",
                "Max_Discount": "Max Discount %",
                "Avg_Discount": "Avg Discount %",
            }
        )
        .sort_values("Profit", ascending=True)
    )
    order_leakage["Order Date"] = order_leakage["Order Date"].dt.strftime("%Y-%m-%d")
    order_leakage["Margin %"] = order_leakage["Profit"] / order_leakage["Sales"]

    row = write_banner(ws, f"Specific Loss-Making Orders with Discount > 20% ({len(order_leakage):,} Orders)", row=row)
    write_styled_table(
        ws,
        order_leakage,
        start_row=row,
        col_formats={
            "Loss Items": FMT_INTEGER,
            "Sales": FMT_CURRENCY,
            "Profit": FMT_CURRENCY,
            "Max Discount %": FMT_PERCENT,
            "Avg Discount %": FMT_PERCENT,
            "Margin %": FMT_PERCENT,
        },
        highlight_loss_cols=("Profit",),
    )
    auto_fit_columns(ws)


def main() -> None:
    """Generate formatted Executive_Sales_Report.xlsx."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = load_data()

    wb = openpyxl.Workbook()
    # Remove default blank sheet before adding named executive tabs
    wb.remove(wb.active)

    build_executive_summary(wb, df)
    build_category_performance(wb, df)
    build_regional_segments(wb, df)
    build_top_performers(wb, df)
    build_loss_leakage_audit(wb, df)

    wb.save(OUTPUT_PATH)
    print(f"Saved Excel report: {OUTPUT_PATH}")
    print(f"File size: {OUTPUT_PATH.stat().st_size:,} bytes")
    print(f"Sheets: {wb.sheetnames}")


if __name__ == "__main__":
    main()
