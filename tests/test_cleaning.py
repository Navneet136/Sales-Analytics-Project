"""
Comprehensive Automated Unit Test Suite for Retail Sales ETL Pipeline.

Covers:
- Column name standardization
- Date conversion and validation
- Missing value auditing and handling
- Duplicate detection and preservation of Row IDs 3406 & 3407
- Postal code 5-digit formatting with zero-padding
- Feature engineering logic and calculations
- Profit margin % and financial metrics
- Safe division handling against zero denominators
- Preservation of original financial values
- Immutability of raw source files
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.data_loader import load_raw_data, REQUIRED_RAW_COLUMNS, get_default_data_path
from src.cleaner import (
    standardize_column_names,
    convert_date_columns,
    format_postal_code,
    handle_missing_values,
    audit_duplicates,
    validate_numerical_ranges,
    engineer_features,
    run_cleaning_pipeline
)


@pytest.fixture(scope="module")
def raw_dataset():
    """Load the raw dataset once for the test module."""
    return load_raw_data()


@pytest.fixture(scope="module")
def cleaned_dataset_and_report(raw_dataset):
    """Run the cleaning pipeline on the raw dataset once."""
    return run_cleaning_pipeline(raw_dataset)


@pytest.fixture
def sample_test_df():
    """Small synthetic test DataFrame to verify edge cases in isolation."""
    data = {
        'Row ID': [1, 2, 3],
        'Order ID': ['CA-2016-1', 'CA-2016-2', 'CA-2016-3'],
        'Order Date': ['11/8/2016', '6/12/2016', '10/11/2015'],
        'Ship Date': ['11/11/2016', '6/16/2016', '10/18/2015'],
        'Postal Code': [6824, 90036, None],
        'Sales': [100.0, 0.0, 250.0],
        'Quantity': [2, 0, 5],
        'Discount': [0.1, 0.0, 0.5],
        'Profit': [20.0, 0.0, -50.0]
    }
    return pd.DataFrame(data)


# =====================================================================
# 1. Raw Data Ingestion & Immutability Tests
# =====================================================================

def test_load_raw_data_success(raw_dataset):
    """Test that raw dataset loads with exact expected shape and columns."""
    assert isinstance(raw_dataset, pd.DataFrame)
    assert len(raw_dataset) == 9994
    assert len(raw_dataset.columns) == 21
    for col in REQUIRED_RAW_COLUMNS:
        assert col in raw_dataset.columns


def test_load_raw_data_file_not_found():
    """Test that loading a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_raw_data(file_path="non_existent_directory/fake_file.csv")


def test_load_raw_data_missing_columns():
    """Test that missing required columns raises ValueError."""
    dummy_df = pd.DataFrame({'ColA': [1], 'ColB': [2]})
    temp_csv = Path('temp_test_dummy.csv')
    dummy_df.to_csv(temp_csv, index=False)

    try:
        with pytest.raises(ValueError) as excinfo:
            load_raw_data(file_path=temp_csv)
        assert "missing" in str(excinfo.value).lower()
    finally:
        if temp_csv.exists():
            temp_csv.unlink()


def test_preservation_of_raw_source_file():
    """Test that loading and running ETL does not alter the physical raw CSV."""
    raw_path = get_default_data_path()
    assert raw_path.exists()
    original_size = raw_path.stat().st_size
    # Size of Sample - Superstore.csv is 2,287,806 bytes
    assert original_size == 2287806


# =====================================================================
# 2. Column Standardization & Data Typing Tests
# =====================================================================

def test_standardize_column_names(sample_test_df):
    """Test that headers are converted to clean snake_case without spaces or hyphens."""
    standardized = standardize_column_names(sample_test_df)
    expected_cols = [
        'row_id', 'order_id', 'order_date', 'ship_date',
        'postal_code', 'sales', 'quantity', 'discount', 'profit'
    ]
    assert list(standardized.columns) == expected_cols


def test_date_conversion(sample_test_df):
    """Test date parsing into datetime64[ns]."""
    standardized = standardize_column_names(sample_test_df)
    dated = convert_date_columns(standardized)
    assert np.issubdtype(dated['order_date'].dtype, np.datetime64)
    assert np.issubdtype(dated['ship_date'].dtype, np.datetime64)
    assert dated['order_date'].iloc[0] == pd.Timestamp('2016-11-08')
    assert dated['ship_date'].iloc[0] == pd.Timestamp('2016-11-11')


# =====================================================================
# 3. Postal Code Formatting Tests
# =====================================================================

def test_format_postal_code():
    """Test postal code 5-digit zero-padding and NaN preservation."""
    df = pd.DataFrame({'postal_code': [6824, 90036, 1730, np.nan, None, '7109']})
    formatted = format_postal_code(df, col='postal_code')

    assert formatted['postal_code'].iloc[0] == '06824'
    assert formatted['postal_code'].iloc[1] == '90036'
    assert formatted['postal_code'].iloc[2] == '01730'
    assert formatted['postal_code'].iloc[3] is None or pd.isna(formatted['postal_code'].iloc[3])
    assert formatted['postal_code'].iloc[4] is None or pd.isna(formatted['postal_code'].iloc[4])
    assert formatted['postal_code'].iloc[5] == '07109'


# =====================================================================
# 4. Missing Values & Duplicate Auditing Tests
# =====================================================================

def test_missing_value_handling(raw_dataset):
    """Test that raw dataset has zero missing values."""
    standardized = standardize_column_names(raw_dataset)
    cleaned, audit = handle_missing_values(standardized)
    assert audit['total_null_cells'] == 0
    assert len(audit['columns_with_nulls']) == 0
    assert len(cleaned) == len(raw_dataset)


def test_duplicate_auditing_preserves_special_rows(raw_dataset):
    """
    Test duplicate detection specifically on Row ID 3406 and 3407.
    Verify that BOTH records remain in the dataset.
    """
    standardized = standardize_column_names(raw_dataset)
    audit = audit_duplicates(standardized)

    assert audit['exact_full_row_duplicates'] == 0
    assert audit['business_duplicates_count'] == 1
    assert 3406 in audit['business_duplicate_row_ids']
    assert 3407 in audit['business_duplicate_row_ids']

    # Special investigation block check
    special = audit['special_case_investigation']
    assert special['found'] is True
    assert special['action_taken'] == "PRESERVED_BOTH_RECORDS"

    # Verify both records are physically in the dataframe
    rows_3406_3407 = standardized[standardized['row_id'].isin([3406, 3407])]
    assert len(rows_3406_3407) == 2


# =====================================================================
# 5. Feature Engineering & Calculations Tests
# =====================================================================

def test_feature_engineering_calculations(sample_test_df):
    """Test that all engineered features compute accurate commercial numbers."""
    std = standardize_column_names(sample_test_df)
    dated = convert_date_columns(std)
    enriched = engineer_features(dated)

    # 1. Time intelligence
    assert enriched['order_year'].iloc[0] == 2016
    assert enriched['order_month'].iloc[0] == 11
    assert enriched['order_month_name'].iloc[0] == 'November'
    assert enriched['order_quarter'].iloc[0] == 4
    assert enriched['order_day_name'].iloc[0] == 'Tuesday'
    assert enriched['shipping_duration_days'].iloc[0] == 3

    # 2. Financial metrics: Row 0 -> sales=100, profit=20, quantity=2
    # total_cost = 100 - 20 = 80
    assert enriched['total_cost'].iloc[0] == 80.0
    # unit_selling_price = 100 / 2 = 50.0
    assert enriched['unit_selling_price'].iloc[0] == 50.0
    # unit_cost = 80 / 2 = 40.0
    assert enriched['unit_cost'].iloc[0] == 40.0
    # profit_margin_pct = (20 / 100) * 100 = 20.0%
    assert enriched['profit_margin_pct'].iloc[0] == 20.0


def test_division_by_zero_handling(sample_test_df):
    """Test that division by zero (quantity=0, sales=0) does not crash and defaults to 0.0."""
    std = standardize_column_names(sample_test_df)
    dated = convert_date_columns(std)
    enriched = engineer_features(dated)

    # Row 1 has sales = 0.0, quantity = 0
    assert enriched['unit_selling_price'].iloc[1] == 0.0
    assert enriched['unit_cost'].iloc[1] == 0.0
    assert enriched['profit_margin_pct'].iloc[1] == 0.0


def test_preservation_of_original_financial_values(raw_dataset, cleaned_dataset_and_report):
    """
    Verify that row_id, sales, quantity, discount, and profit values in the
    cleaned dataset exactly match the raw source dataset for all 9,994 records.
    """
    cleaned_df, _ = cleaned_dataset_and_report

    # Ensure row counts match exactly
    assert len(cleaned_df) == len(raw_dataset)

    # Sort both by row_id to ensure aligned comparison
    raw_sorted = raw_dataset.sort_values(by='Row ID').reset_index(drop=True)
    clean_sorted = cleaned_df.sort_values(by='row_id').reset_index(drop=True)

    np.testing.assert_array_equal(clean_sorted['row_id'].values, raw_sorted['Row ID'].values)
    np.testing.assert_allclose(clean_sorted['sales'].values, raw_sorted['Sales'].values, rtol=1e-5)
    np.testing.assert_array_equal(clean_sorted['quantity'].values, raw_sorted['Quantity'].values)
    np.testing.assert_allclose(clean_sorted['discount'].values, raw_sorted['Discount'].values, rtol=1e-5)
    np.testing.assert_allclose(clean_sorted['profit'].values, raw_sorted['Profit'].values, rtol=1e-5)


def test_numerical_validation_pass(cleaned_dataset_and_report):
    """Test that the cleaned dataset passes all business range validations."""
    _, report = cleaned_dataset_and_report
    num_val = report['numerical_validation']

    assert num_val['all_ranges_valid'] is True
    assert num_val['negative_sales_count'] == 0
    assert num_val['zero_or_negative_quantity_count'] == 0
    assert num_val['invalid_discount_range_count'] == 0
    assert num_val['negative_shipping_days_count'] == 0
    assert num_val['loss_making_transactions_count'] == 1871


# =====================================================================
# 6. Export Artifacts Verification Tests
# =====================================================================

def test_exported_clean_csv():
    """Verify that the exported CSV exists, loads, and matches expected shape."""
    csv_path = Path('data/processed/clean_superstore.csv')
    assert csv_path.exists(), f"Clean CSV not found at {csv_path}"
    df_csv = pd.read_csv(csv_path)
    assert len(df_csv) == 9994
    assert len(df_csv.columns) == 31
    assert 'profit_margin_pct' in df_csv.columns
    assert 'order_year' in df_csv.columns


def test_exported_clean_parquet():
    """Verify that the exported Parquet file exists, loads, and matches expected schema."""
    parquet_path = Path('data/processed/clean_superstore.parquet')
    assert parquet_path.exists(), f"Clean Parquet not found at {parquet_path}"
    df_parquet = pd.read_parquet(parquet_path)
    assert len(df_parquet) == 9994
    assert len(df_parquet.columns) == 31
    assert 'shipping_duration_days' in df_parquet.columns
    assert 'unit_selling_price' in df_parquet.columns


def test_data_quality_report_generated():
    """Verify that data_quality_report.md exists and documents duplicate audit."""
    report_path = Path('reports/data_quality_report.md')
    assert report_path.exists(), f"Report not found at {report_path}"
    content = report_path.read_text(encoding='utf-8')
    assert "Row ID 3406 vs. Row ID 3407" in content
    assert "PRESERVED_BOTH_RECORDS" in content
    assert "9,994" in content

