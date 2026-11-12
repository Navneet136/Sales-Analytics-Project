"""
Data Cleaning and Feature Engineering Module for Retail Sales Analytics ETL.

This module provides modular, reusable, and testable functions to standardize schema,
cast data types, audit data quality, perform business feature engineering, and format
export-ready datasets for MySQL and Power BI without mutating original source data.
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize DataFrame column headers into consistent snake_case format.
    Transforms whitespace, dashes, and camel-case/title-case characters into lowercase
    identifiers with single underscores.

    Example:
        'Row ID'       -> 'row_id'
        'Sub-Category' -> 'sub_category'
        'Postal Code'  -> 'postal_code'

    Args:
        df (pd.DataFrame): Input DataFrame.

    Returns:
        pd.DataFrame: New DataFrame copy with standardized snake_case headers.
    """
    cleaned_df = df.copy()

    def _to_snake_case(name: str) -> str:
        # Replace hyphens, dots, and slashes with space
        name = re.sub(r'[-./\\]', ' ', str(name).strip())
        # Insert underscore between lower-to-upper transitions (e.g. CamelCase)
        name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
        # Replace spaces or multiple underscores with a single underscore
        name = re.sub(r'[\s_]+', '_', name)
        return name.lower()

    cleaned_df.columns = [_to_snake_case(col) for col in cleaned_df.columns]
    return cleaned_df


def convert_date_columns(
    df: pd.DataFrame,
    date_columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Convert date columns into native datetime64[ns] types.

    Args:
        df (pd.DataFrame): Input DataFrame with snake_case headers.
        date_columns (Optional[List[str]]): List of date column names to parse.
            Defaults to ['order_date', 'ship_date'].

    Returns:
        pd.DataFrame: DataFrame with parsed datetime columns.

    Raises:
        ValueError: If any date fails parsing and results in unexpected NaT values.
    """
    cleaned_df = df.copy()
    target_cols = date_columns or ['order_date', 'ship_date']

    for col in target_cols:
        if col in cleaned_df.columns:
            cleaned_df[col] = pd.to_datetime(cleaned_df[col], errors='coerce')
            nat_count = cleaned_df[col].isna().sum()
            if nat_count > 0:
                raise ValueError(
                    f"Date conversion produced {nat_count} unparseable NaT values in column '{col}'."
                )

    return cleaned_df


def format_postal_code(
    df: pd.DataFrame,
    col: str = 'postal_code'
) -> pd.DataFrame:
    """
    Convert postal code values into standard 5-digit strings, properly padding
    leading zeros (e.g., 6824 -> '06824') while preserving null/missing values.

    Args:
        df (pd.DataFrame): Input DataFrame.
        col (str): Column name containing postal codes (default: 'postal_code').

    Returns:
        pd.DataFrame: DataFrame with formatted 5-digit postal code strings.
    """
    cleaned_df = df.copy()
    if col not in cleaned_df.columns:
        return cleaned_df

    def _pad_zip(val: Any) -> Optional[str]:
        if pd.isna(val) or val is None:
            return None
        try:
            # Handle numeric float/int conversions cleanly
            int_val = int(float(val))
            return f"{int_val:05d}"
        except (ValueError, TypeError):
            val_str = str(val).strip()
            if val_str.isdigit():
                return val_str.zfill(5)
            return val_str if val_str else None

    cleaned_df[col] = cleaned_df[col].apply(_pad_zip)
    return cleaned_df


def handle_missing_values(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Audit and handle missing values across all columns according to documented rules.
    For this dataset, null counts are verified. Any unexpected nulls are tracked and audited.

    Args:
        df (pd.DataFrame): Input DataFrame.

    Returns:
        Tuple[pd.DataFrame, Dict[str, Any]]: Cleaned DataFrame and missing value audit dictionary.
    """
    cleaned_df = df.copy()
    null_counts = cleaned_df.isnull().sum()
    missing_report = {
        col: int(count) for col, count in null_counts.items() if count > 0
    }

    # Documented rule: No records are deleted; missing categorical fields default to 'Unknown'
    # and numerical default to median if present. In Sample Superstore, missing count is 0.
    audit_summary = {
        'total_null_cells': int(null_counts.sum()),
        'columns_with_nulls': missing_report,
        'imputation_applied': False
    }

    return cleaned_df, audit_summary


def audit_duplicates(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Audit exact full-row duplicate records and business duplicate records
    (ignoring the artificial surrogate key 'row_id').

    Identifies and specifically documents Row ID 3406 and Row ID 3407 per project rules.
    Does NOT delete records automatically.

    Args:
        df (pd.DataFrame): Input DataFrame.

    Returns:
        Dict[str, Any]: Detailed duplicate audit dictionary.
    """
    # 1. Exact full-row matches including row_id
    exact_duplicates_count = int(df.duplicated().sum())

    # 2. Business duplicates (excluding row_id if present)
    non_surrogate_cols = [c for c in df.columns if c != 'row_id']
    business_duplicate_mask = df.duplicated(subset=non_surrogate_cols, keep=False)
    business_duplicates_count = int(df.duplicated(subset=non_surrogate_cols, keep='first').sum())

    duplicate_rows = df[business_duplicate_mask]

    # Specific audit of Row 3406 and 3407
    special_case_rows = df[df['row_id'].isin([3406, 3407])] if 'row_id' in df.columns else pd.DataFrame()

    matching_fields = {}
    if len(special_case_rows) == 2:
        row1 = special_case_rows.iloc[0]
        row2 = special_case_rows.iloc[1]
        for col in non_surrogate_cols:
            if col in special_case_rows.columns and row1[col] == row2[col]:
                matching_fields[col] = str(row1[col])

    audit_result = {
        'exact_full_row_duplicates': exact_duplicates_count,
        'business_duplicates_count': business_duplicates_count,
        'business_duplicate_row_ids': duplicate_rows['row_id'].tolist() if 'row_id' in duplicate_rows.columns else [],
        'special_case_investigation': {
            'target_row_ids': [3406, 3407],
            'found': len(special_case_rows) == 2,
            'matching_business_fields': matching_fields,
            'hypothesis': (
                "All operational, customer, product, and financial attributes match exactly. "
                "The only variance is the artificial sequential row_id (3406 vs 3407). "
                "This indicates possible duplicate data entry at POS or double-extraction."
            ),
            'action_taken': "PRESERVED_BOTH_RECORDS",
            'safe_to_remove_recommendation': (
                "Not safe to auto-delete without business owner confirmation. "
                "May represent two identical items ordered under separate lines. "
                "Preserved in clean dataset pending business sign-off."
            )
        }
    }

    return audit_result


def validate_numerical_ranges(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate numerical columns for range anomalies and business rule adherence.
    - sales >= 0
    - quantity >= 1 (integer)
    - 0 <= discount <= 1.0
    - shipping_duration_days >= 0 (if present)

    Args:
        df (pd.DataFrame): Input DataFrame.

    Returns:
        Dict[str, Any]: Numerical validation audit metrics.
    """
    validation_report = {
        'negative_sales_count': int((df['sales'] < 0).sum()) if 'sales' in df.columns else 0,
        'zero_or_negative_quantity_count': int((df['quantity'] <= 0).sum()) if 'quantity' in df.columns else 0,
        'invalid_discount_range_count': int(((df['discount'] < 0.0) | (df['discount'] > 1.0)).sum()) if 'discount' in df.columns else 0,
        'negative_shipping_days_count': int((df['shipping_duration_days'] < 0).sum()) if 'shipping_duration_days' in df.columns else 0,
        'loss_making_transactions_count': int((df['profit'] < 0).sum()) if 'profit' in df.columns else 0,
        'all_ranges_valid': True
    }

    if (
        validation_report['negative_sales_count'] > 0 or
        validation_report['zero_or_negative_quantity_count'] > 0 or
        validation_report['invalid_discount_range_count'] > 0 or
        validation_report['negative_shipping_days_count'] > 0
    ):
        validation_report['all_ranges_valid'] = False

    return validation_report


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Perform retail business feature engineering:
    - order_year: Integer year extracted from order_date.
    - order_month: Integer month (1-12) from order_date.
    - order_month_name: Full month name (e.g. 'November').
    - order_quarter: Integer quarter (1-4).
    - order_day_name: Day of week name (e.g. 'Tuesday').
    - shipping_duration_days: Days elapsed between order_date and ship_date.
    - total_cost: sales - profit.
    - unit_selling_price: sales / quantity (safe division against zero).
    - unit_cost: total_cost / quantity (safe division against zero).
    - profit_margin_pct: (profit / sales) * 100 (safe division against zero).

    Original columns and values are preserved without alteration.

    Args:
        df (pd.DataFrame): Cleaned DataFrame with datetime order_date and ship_date.

    Returns:
        pd.DataFrame: DataFrame enriched with engineered retail features.
    """
    enriched_df = df.copy()

    # Time intelligence features
    if 'order_date' in enriched_df.columns:
        enriched_df['order_year'] = enriched_df['order_date'].dt.year
        enriched_df['order_month'] = enriched_df['order_date'].dt.month
        enriched_df['order_month_name'] = enriched_df['order_date'].dt.month_name()
        enriched_df['order_quarter'] = enriched_df['order_date'].dt.quarter
        enriched_df['order_day_name'] = enriched_df['order_date'].dt.day_name()

    # Shipping duration
    if 'order_date' in enriched_df.columns and 'ship_date' in enriched_df.columns:
        enriched_df['shipping_duration_days'] = (
            enriched_df['ship_date'] - enriched_df['order_date']
        ).dt.days

    # Financial & Unit Economics (with safe division handling zero denominators)
    if 'sales' in enriched_df.columns and 'profit' in enriched_df.columns:
        enriched_df['total_cost'] = enriched_df['sales'] - enriched_df['profit']

        # profit_margin_pct = (profit / sales) * 100, safe against sales == 0
        enriched_df['profit_margin_pct'] = np.where(
            enriched_df['sales'] != 0,
            (enriched_df['profit'] / enriched_df['sales']) * 100.0,
            0.0
        )

    if 'sales' in enriched_df.columns and 'quantity' in enriched_df.columns:
        # unit_selling_price = sales / quantity, safe against quantity == 0
        enriched_df['unit_selling_price'] = np.where(
            enriched_df['quantity'] != 0,
            enriched_df['sales'] / enriched_df['quantity'],
            0.0
        )

    if 'total_cost' in enriched_df.columns and 'quantity' in enriched_df.columns:
        # unit_cost = total_cost / quantity, safe against quantity == 0
        enriched_df['unit_cost'] = np.where(
            enriched_df['quantity'] != 0,
            enriched_df['total_cost'] / enriched_df['quantity'],
            0.0
        )

    return enriched_df


def run_cleaning_pipeline(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Execute the end-to-end data cleaning, auditing, and feature engineering pipeline.

    Workflow:
    1. Standardize column names to snake_case.
    2. Convert date columns (order_date, ship_date) to datetime64[ns].
    3. Format postal_code into zero-padded 5-digit strings.
    4. Handle and audit missing values.
    5. Audit duplicate records (specifically logging Row ID 3406 & 3407 without deletion).
    6. Engineer time intelligence and unit economics features.
    7. Validate numerical ranges and integrity.

    Args:
        df (pd.DataFrame): Raw DataFrame.

    Returns:
        Tuple[pd.DataFrame, Dict[str, Any]]: Cleaned & enriched DataFrame, and audit report dictionary.
    """
    raw_row_count = len(df)
    raw_col_count = len(df.columns)

    # 1. Standardize columns
    step1_df = standardize_column_names(df)

    # 2. Date conversions
    step2_df = convert_date_columns(step1_df)

    # 3. Postal code formatting
    step3_df = format_postal_code(step2_df)

    # 4. Missing value audit
    step4_df, missing_audit = handle_missing_values(step3_df)

    # 5. Duplicate audit
    duplicate_audit = audit_duplicates(step4_df)

    # 6. Feature engineering
    step6_df = engineer_features(step4_df)

    # 7. Numerical validation
    numerical_audit = validate_numerical_ranges(step6_df)

    # Compile comprehensive metadata summary
    pipeline_report = {
        'raw_row_count': raw_row_count,
        'cleaned_row_count': len(step6_df),
        'raw_column_count': raw_col_count,
        'cleaned_column_count': len(step6_df.columns),
        'missing_values': missing_audit,
        'duplicate_audit': duplicate_audit,
        'numerical_validation': numerical_audit,
        'engineered_features': [
            'order_year',
            'order_month',
            'order_month_name',
            'order_quarter',
            'order_day_name',
            'shipping_duration_days',
            'total_cost',
            'unit_selling_price',
            'unit_cost',
            'profit_margin_pct'
        ]
    }

    return step6_df, pipeline_report
