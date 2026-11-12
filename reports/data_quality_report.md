# Retail Sales ETL Data Quality & Audit Report

**Generated Date:** 2026-11-12 10:50:43  
**Pipeline Author:** Senior Data Engineer & Python Developer  
**Source Dataset:** `Sample - Superstore.csv`  
**Pipeline Status:** SUCCESS (All validations passed)

---

## 1. Executive Summary & Reconciliation

| Metric | Raw Dataset | Cleaned Dataset | Variance | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Total Record Count (Rows)** | **9,994** | **9,994** | **0** | Reconciled (100% Retained) |
| **Total Features (Columns)** | **21** | **31** | **+10** | 10 New Engineered Features |
| **Missing / Null Cells** | 0 | 0 | 0 | 100% Complete |
| **Exact Full Duplicates** | 0 | 0 | 0 | None Present |
| **Business Duplicates** | 1 pair (2 rows) | 1 pair (2 rows) | 0 | Preserved for Business Audit |
| **Invalid Records** | 0 | 0 | 0 | 100% Valid |

---

## 2. Duplicate Records Audit & Special Investigation

### Overview
- **Exact Full-Row Duplicates:** 0 (No rows share identical `row_id` alongside all fields).
- **Business Field Duplicates:** 1 duplicate pair detected (2 rows affected).

### Special Investigation: Row ID 3406 vs. Row ID 3407
- **Investigated Row IDs:** `[3406, 3407]`
- **Matching Business Attributes:**
  - **`order_id`**: `US-2014-150119`
  - **`order_date`**: `2014-04-23 00:00:00`
  - **`ship_date`**: `2014-04-27 00:00:00`
  - **`ship_mode`**: `Standard Class`
  - **`customer_id`**: `LB-16795`
  - **`customer_name`**: `Laurel Beltran`
  - **`segment`**: `Home Office`
  - **`country`**: `United States`
  - **`city`**: `Columbus`
  - **`state`**: `Ohio`
  - **`postal_code`**: `43229`
  - **`region`**: `East`
  - **`product_id`**: `FUR-CH-10002965`
  - **`category`**: `Furniture`
  - **`sub_category`**: `Chairs`
  - **`product_name`**: `Global Leather Highback Executive Chair with Pneumatic Height Adjustment, Black`
  - **`sales`**: `281.372`
  - **`quantity`**: `2`
  - **`discount`**: `0.3`
  - **`profit`**: `-12.0588`
- **Root-Cause Analysis:**
  All operational, customer, product, and financial attributes match exactly. The only variance is the artificial sequential row_id (3406 vs 3407). This indicates possible duplicate data entry at POS or double-extraction.
- **Action Taken in ETL Pipeline:**
  `PRESERVED_BOTH_RECORDS` — Neither record was silently dropped or modified. Both rows are preserved in `clean_superstore.csv` and `clean_superstore.parquet`.
- **Recommendation for Business Stakeholders:**
  Not safe to auto-delete without business owner confirmation. May represent two identical items ordered under separate lines. Preserved in clean dataset pending business sign-off.

---

## 3. Data Schema & Type Castings

Standardized all 21 raw column names into PEP 8 / SQL-friendly `snake_case`.

| Original Raw Column | Standardized Clean Column | Raw Type | Clean Type | Modified? |
| :--- | :--- | :--- | :--- | :--- |
| `Row ID` | `row_id` | `int64` | `int64` | No |
| `Order ID` | `order_id` | `str` | `str` | No |
| `Order Date` | `order_date` | `str` | `datetime64[us]` | Yes |
| `Ship Date` | `ship_date` | `str` | `datetime64[us]` | Yes |
| `Ship Mode` | `ship_mode` | `str` | `str` | No |
| `Customer ID` | `customer_id` | `str` | `str` | No |
| `Customer Name` | `customer_name` | `str` | `str` | No |
| `Segment` | `segment` | `str` | `str` | No |
| `Country` | `country` | `str` | `str` | No |
| `City` | `city` | `str` | `str` | No |
| `State` | `state` | `str` | `str` | No |
| `Postal Code` | `postal_code` | `int64` | `str` | Yes |
| `Region` | `region` | `str` | `str` | No |
| `Product ID` | `product_id` | `str` | `str` | No |
| `Category` | `category` | `str` | `str` | No |
| `Sub-Category` | `sub_category` | `str` | `str` | No |
| `Product Name` | `product_name` | `str` | `str` | No |
| `Sales` | `sales` | `float64` | `float64` | No |
| `Quantity` | `quantity` | `int64` | `int64` | No |
| `Discount` | `discount` | `float64` | `float64` | No |
| `Profit` | `profit` | `float64` | `float64` | No |

### Key Schema Enhancements:
1. **`order_date` & `ship_date`:** Converted from raw string (`object`) to native `datetime64[ns]`, enabling date arithmetic and time-series querying.
2. **`postal_code`:** Formatted into a standardized 5-digit string zero-padded from the left (e.g., integer `6824` became `'06824'`, preserving East Coast US ZIP codes).
3. **Financials & Keys:** Preserved raw `row_id`, `sales`, `quantity`, `discount`, and `profit` values with zero floating-point degradation.

---

## 4. Feature Engineering Inventory

A total of **10 new analytical features** were engineered to accelerate downstream MySQL aggregations and Power BI reporting:

| Feature Name | Target Data Type | Calculation / Logic | Business Objective |
| :--- | :--- | :--- | :--- |
| `order_year` | `int32/int64` | `order_date.dt.year` | Calendar year of order (e.g. 2016) |
| `order_month` | `int32/int64` | `order_date.dt.month` | Month index (1 to 12) |
| `order_month_name` | `object` | `order_date.dt.month_name()` | Full name of month (e.g. November) |
| `order_quarter` | `int32/int64` | `order_date.dt.quarter` | Calendar quarter (1 to 4) |
| `order_day_name` | `object` | `order_date.dt.day_name()` | Day of week (e.g. Tuesday) |
| `shipping_duration_days` | `int64` | `(ship_date - order_date).dt.days` | Transit duration in calendar days |
| `total_cost` | `float64` | `sales - profit` | Cost of goods sold (COGS) |
| `unit_selling_price` | `float64` | `sales / quantity` (safe division) | Average revenue per item unit |
| `unit_cost` | `float64` | `total_cost / quantity` (safe division) | Unit cost of goods sold |
| `profit_margin_pct` | `float64` | `(profit / sales) * 100` (safe division) | Operating profit percentage |

---

## 5. Numerical Range & Integrity Validations

Every row was evaluated against business rules:
- **Negative Sales Count:** 0 (Rule: `sales >= 0` — Passed)
- **Zero or Negative Quantity Count:** 0 (Rule: `quantity >= 1` — Passed)
- **Invalid Discount Count:** 0 (Rule: `0.0 <= discount <= 1.0` — Passed)
- **Negative Shipping Duration Days:** 0 (Rule: `ship_date >= order_date` — Passed)
- **Loss-Making Transactions Count:** 1,871 (18.72% of orders) — Expected retail operational behavior.
- **Overall Validation Status:** **PASSED (Zero anomalies detected)**

---

## 6. Export Artifacts & Storage Specifications

| Target Artifact | File Format | Record Count | File Size | Path |
| :--- | :--- | :--- | :--- | :--- |
| Cleaned CSV | CSV (UTF-8, comma-delimited) | 9,994 | 2,997,537 bytes (~2.86 MB) | `D:\one drive\OneDrive\Desktop\Sales-Analytics-Project\data\processed\clean_superstore.csv` |
| Cleaned Parquet | Apache Parquet (Snappy compressed, PyArrow) | 9,994 | 633,622 bytes (~0.60 MB) | `D:\one drive\OneDrive\Desktop\Sales-Analytics-Project\data\processed\clean_superstore.parquet` |

---

## 7. Conclusions & Readiness for Phase 4 (MySQL Database Modeling)

1. The data engineering pipeline is **100% reproducible**, modular, and fully covered by unit tests.
2. No data loss occurred: all 9,994 transactions are retained and enriched.
3. Clean datasets are primed for direct dimensional modeling into a Star Schema (Fact_Sales, Dim_Customer, Dim_Product, Dim_Date, Dim_Location) in MySQL.
