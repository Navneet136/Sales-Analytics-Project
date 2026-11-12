"""
Automated Verification Tests for Phase 6–9 Reporting & Export Deliverables.

Verifies:
- All 4 300-DPI PNG charts exist in reports/figures/ and are non-empty.
- reports/Executive_Sales_Report.xlsx opens cleanly with openpyxl and contains all 5 tabs.
- All 11 Power BI CSV extracts exist in powerbi/data_extracts/ and fact_sales.csv
  reconciles to 9,994 rows and $2,297,200.86 total sales.
"""

from pathlib import Path

import openpyxl
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"
EXCEL_REPORT_PATH = PROJECT_ROOT / "reports" / "Executive_Sales_Report.xlsx"
EXTRACTS_DIR = PROJECT_ROOT / "powerbi" / "data_extracts"

EXPECTED_CHARTS = (
    "01_monthly_sales_trend.png",
    "02_category_subcat_margins.png",
    "03_discount_vs_profit_scatter.png",
    "04_regional_performance.png",
)

EXPECTED_EXCEL_SHEETS = [
    "Executive_Summary",
    "Category_Performance",
    "Regional_Segments",
    "Top_Performers",
    "Loss_Leakage_Audit",
]

EXPECTED_POWERBI_CSVS = (
    "dim_date.csv",
    "dim_customer.csv",
    "dim_product.csv",
    "dim_location.csv",
    "fact_sales.csv",
    "vw_sales_summary.csv",
    "vw_monthly_sales.csv",
    "vw_category_performance.csv",
    "vw_region_performance.csv",
    "vw_product_performance.csv",
    "vw_customer_performance.csv",
)


def test_png_charts_exist_and_non_empty() -> None:
    """Verify all 4 generated matplotlib/seaborn charts exist and have content."""
    for chart_name in EXPECTED_CHARTS:
        chart_path = FIGURES_DIR / chart_name
        assert chart_path.exists(), f"Missing chart file: {chart_path}"
        assert chart_path.stat().st_size > 0, f"Chart file is empty: {chart_path}"


def test_excel_report_sheets_and_integrity() -> None:
    """Verify Executive_Sales_Report.xlsx opens cleanly and includes all 5 expected sheets."""
    assert EXCEL_REPORT_PATH.exists(), f"Missing Excel report: {EXCEL_REPORT_PATH}"
    assert EXCEL_REPORT_PATH.stat().st_size > 0

    wb = openpyxl.load_workbook(EXCEL_REPORT_PATH, read_only=True)
    try:
        assert wb.sheetnames == EXPECTED_EXCEL_SHEETS
        for sheet_name in EXPECTED_EXCEL_SHEETS:
            ws = wb[sheet_name]
            assert ws.max_row > 1, f"Worksheet '{sheet_name}' has no data rows"
    finally:
        wb.close()


def test_powerbi_csv_extracts_and_reconciliation() -> None:
    """Verify all 11 Power BI CSV extracts exist and fact_sales.csv reconciles accurately."""
    for csv_name in EXPECTED_POWERBI_CSVS:
        csv_path = EXTRACTS_DIR / csv_name
        assert csv_path.exists(), f"Missing Power BI CSV extract: {csv_path}"
        assert csv_path.stat().st_size > 0, f"Empty Power BI CSV extract: {csv_path}"

    fact_df = pd.read_csv(EXTRACTS_DIR / "fact_sales.csv")
    assert len(fact_df) == 9994
    assert round(float(fact_df["sales"].sum()), 2) == 2297200.86
    assert round(float(fact_df["profit"].sum()), 2) == 286397.02
    assert int(fact_df["quantity"].sum()) == 37873
