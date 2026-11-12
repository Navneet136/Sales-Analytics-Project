"""
Data Loader Module for Retail Sales Analytics ETL Pipeline.

This module is responsible for locating, validating, and safely ingesting the raw
Sample Superstore dataset without mutating the underlying file.
"""

from pathlib import Path
from typing import List, Optional, Union
import pandas as pd


# Default expected schema columns in raw Sample Superstore dataset
REQUIRED_RAW_COLUMNS: List[str] = [
    'Row ID',
    'Order ID',
    'Order Date',
    'Ship Date',
    'Ship Mode',
    'Customer ID',
    'Customer Name',
    'Segment',
    'Country',
    'City',
    'State',
    'Postal Code',
    'Region',
    'Product ID',
    'Category',
    'Sub-Category',
    'Product Name',
    'Sales',
    'Quantity',
    'Discount',
    'Profit'
]

# Primary encoding required for the Sample Superstore dataset
DEFAULT_ENCODING: str = 'windows-1252'


def get_default_data_path() -> Path:
    """
    Resolve the default path to the raw Sample Superstore CSV file,
    supporting execution from both project root and src/ directory.

    Returns:
        Path: Absolute path to the raw dataset file.
    """
    # Check relative to current working directory
    current_cwd_path = Path('data/raw/Sample - Superstore.csv').resolve()
    if current_cwd_path.exists():
        return current_cwd_path

    # Check relative to this module file location
    module_relative_path = (Path(__file__).resolve().parent.parent /
                            'data' / 'raw' / 'Sample - Superstore.csv')
    if module_relative_path.exists():
        return module_relative_path

    # Fallback default
    return current_cwd_path


def load_raw_data(
    file_path: Optional[Union[str, Path]] = None,
    encoding: str = DEFAULT_ENCODING,
    required_columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Load the raw Sample Superstore CSV dataset into a pandas DataFrame.

    Validates that:
    1. The target file exists on disk.
    2. All expected columns are present.
    3. The file is read using the appropriate character encoding.
    4. The raw dataset remains strictly unmodified (returns an isolated copy).

    Args:
        file_path (Optional[Union[str, Path]]): Custom path to the raw CSV file.
            If None, resolves to the default project path.
        encoding (str): Text encoding for decoding the CSV (default: windows-1252).
        required_columns (Optional[List[str]]): List of expected column names.
            If None, uses REQUIRED_RAW_COLUMNS.

    Returns:
        pd.DataFrame: Deep copy of the loaded raw DataFrame.

    Raises:
        FileNotFoundError: If the specified raw data file does not exist.
        ValueError: If required columns are missing from the loaded dataset.
        RuntimeError: If pandas fails to read or parse the CSV file.
    """
    resolved_path = Path(file_path).resolve() if file_path else get_default_data_path()

    if not resolved_path.exists():
        raise FileNotFoundError(
            f"Raw dataset file not found at: '{resolved_path}'. "
            "Please ensure 'Sample - Superstore.csv' is placed inside 'data/raw/'."
        )

    expected_cols = required_columns if required_columns is not None else REQUIRED_RAW_COLUMNS

    try:
        # Load CSV using pandas with isolated memory
        df = pd.read_csv(
            resolved_path,
            encoding=encoding,
            low_memory=False
        )
    except UnicodeDecodeError as err:
        raise RuntimeError(
            f"Encoding error loading '{resolved_path}' with '{encoding}': {err}. "
            "Superstore data requires 'windows-1252' or 'latin1' encoding."
        ) from err
    except Exception as err:
        raise RuntimeError(
            f"Failed to read CSV file at '{resolved_path}': {err}"
        ) from err

    # Validate schema completeness
    missing_cols = [col for col in expected_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Dataset at '{resolved_path}' is missing {len(missing_cols)} required columns: "
            f"{missing_cols}"
        )

    # Return a deep copy to ensure complete immutability of the source data
    return df.copy(deep=True)
