-- ==============================================================================
-- PROJECT: Sales Data Analysis & Business Intelligence Dashboard
-- MODULE: Phase 4 - MySQL Database Modeling
-- FILE: sql/02_data_ingestion.sql
-- DESCRIPTION: End-to-end data loading script. Employs a robust staging table
--              strategy, populates conformed dimensions, populates fact_sales
--              via surrogate key lookups, and runs data reconciliation queries.
-- ==============================================================================

USE sales_analytics_db;

-- ------------------------------------------------------------------------------
-- 1. Configuration & Prerequisites
-- ------------------------------------------------------------------------------
-- Ensure MySQL server allows loading local data files:
SET GLOBAL local_infile = 1;

-- Note for CLI / Workbench Execution:
-- When connecting via MySQL CLI, enable the local infile flag:
--   mysql --local-infile=1 -u root -p sales_analytics_db
-- If using MySQL Workbench: In the connection properties > Advanced > 
-- check "Enable Local Infile" or add 'OPT_LOCAL_INFILE=1' to Others.

-- ------------------------------------------------------------------------------
-- 2. Create Staging Table: stg_clean_superstore
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS stg_clean_superstore;

CREATE TABLE stg_clean_superstore (
    row_id INT,
    order_id VARCHAR(50),
    order_date DATE,
    ship_date DATE,
    ship_mode VARCHAR(50),
    customer_id VARCHAR(50),
    customer_name VARCHAR(150),
    segment VARCHAR(50),
    country VARCHAR(50),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    region VARCHAR(50),
    product_id VARCHAR(50),
    category VARCHAR(50),
    sub_category VARCHAR(50),
    product_name VARCHAR(255),
    sales DECIMAL(12, 4),
    quantity INT,
    discount DECIMAL(5, 4),
    profit DECIMAL(12, 4),
    order_year INT,
    order_month INT,
    order_month_name VARCHAR(20),
    order_quarter INT,
    order_day_name VARCHAR(20),
    shipping_duration_days INT,
    total_cost DECIMAL(12, 4),
    profit_margin_pct DECIMAL(9, 4),
    unit_selling_price DECIMAL(12, 4),
    unit_cost DECIMAL(12, 4)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Temporary staging table for ingesting clean_superstore.csv';

-- ------------------------------------------------------------------------------
-- 3. Load Processed CSV into Staging Table
-- ------------------------------------------------------------------------------
-- Adjust path below to match your local absolute path if executing from MySQL Workbench:
-- Example Windows Path: 'D:/one drive/OneDrive/Desktop/Sales-Analytics-Project/data/processed/clean_superstore.csv'

LOAD DATA LOCAL INFILE 'D:/one drive/OneDrive/Desktop/Sales-Analytics-Project/data/processed/clean_superstore.csv'
INTO TABLE stg_clean_superstore
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' 
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\r\n'
IGNORE 1 ROWS
(
    row_id, order_id, order_date, ship_date, ship_mode,
    customer_id, customer_name, segment, country, city,
    state, postal_code, region, product_id, category,
    sub_category, product_name, sales, quantity, discount,
    profit, order_year, order_month, order_month_name,
    order_quarter, order_day_name, shipping_duration_days,
    total_cost, profit_margin_pct, unit_selling_price, unit_cost
);

-- Fallback for Linux or Unix-style line endings:
-- If row count is 0 after running above, change LINES TERMINATED BY to '\n'.

-- ------------------------------------------------------------------------------
-- 4. Populate Dimension Tables from Staging
-- ------------------------------------------------------------------------------

-- A. Populate dim_date (Union of all unique order dates and ship dates)
INSERT INTO dim_date (date_key, full_date, year, month, month_name, quarter, day_name)
SELECT DISTINCT
    CAST(DATE_FORMAT(calendar_date, '%Y%m%d') AS UNSIGNED) AS date_key,
    calendar_date AS full_date,
    YEAR(calendar_date) AS year,
    MONTH(calendar_date) AS month,
    MONTHNAME(calendar_date) AS month_name,
    QUARTER(calendar_date) AS quarter,
    DAYNAME(calendar_date) AS day_name
FROM (
    SELECT order_date AS calendar_date FROM stg_clean_superstore
    UNION
    SELECT ship_date AS calendar_date FROM stg_clean_superstore
) AS combined_dates
WHERE calendar_date IS NOT NULL
ORDER BY calendar_date;

-- B. Populate dim_customer (Distinct customer records, 793 expected)
INSERT INTO dim_customer (customer_id, customer_name, segment)
SELECT DISTINCT
    customer_id,
    customer_name,
    segment
FROM stg_clean_superstore
ORDER BY customer_id;

-- C. Populate dim_product (Distinct product combinations, 1,894 expected)
INSERT INTO dim_product (product_id, product_name, category, sub_category)
SELECT DISTINCT
    product_id,
    product_name,
    category,
    sub_category
FROM stg_clean_superstore
ORDER BY product_id, product_name;

-- D. Populate dim_location (Distinct geographic destinations, 632 expected)
INSERT INTO dim_location (country, city, state, postal_code, region)
SELECT DISTINCT
    country,
    city,
    state,
    postal_code,
    region
FROM stg_clean_superstore
ORDER BY state, city, postal_code;

-- ------------------------------------------------------------------------------
-- 5. Populate Fact Table: fact_sales
-- ------------------------------------------------------------------------------
-- Resolves all surrogate foreign keys by joining staging against dimensions.
-- Preserves all 9,994 rows, original row_id (1..9994), and duplicates 3406 & 3407.
INSERT INTO fact_sales (
    row_id,
    order_id,
    order_date_key,
    ship_date_key,
    customer_key,
    product_key,
    location_key,
    ship_mode,
    sales,
    quantity,
    discount,
    profit,
    total_cost,
    unit_selling_price,
    unit_cost,
    profit_margin_pct,
    shipping_duration_days
)
SELECT
    stg.row_id,
    stg.order_id,
    d_order.date_key AS order_date_key,
    d_ship.date_key AS ship_date_key,
    c.customer_key,
    p.product_key,
    l.location_key,
    stg.ship_mode,
    stg.sales,
    stg.quantity,
    stg.discount,
    stg.profit,
    stg.total_cost,
    stg.unit_selling_price,
    stg.unit_cost,
    stg.profit_margin_pct,
    stg.shipping_duration_days
FROM stg_clean_superstore stg
INNER JOIN dim_date d_order 
    ON stg.order_date = d_order.full_date
INNER JOIN dim_date d_ship 
    ON stg.ship_date = d_ship.full_date
INNER JOIN dim_customer c 
    ON stg.customer_id = c.customer_id
INNER JOIN dim_product p 
    ON stg.product_id = p.product_id 
   AND stg.product_name = p.product_name
INNER JOIN dim_location l 
    ON stg.country = l.country
   AND stg.city = l.city
   AND stg.state = l.state
   AND stg.postal_code = l.postal_code
   AND stg.region = l.region
ORDER BY stg.row_id;

-- ------------------------------------------------------------------------------
-- 6. Clean Up Staging (Optional)
-- ------------------------------------------------------------------------------
-- DROP TABLE IF EXISTS stg_clean_superstore;

-- ------------------------------------------------------------------------------
-- 7. Automated Data Ingestion Validation Suite
-- ------------------------------------------------------------------------------

-- Check 1: Record Count Reconciliation (Expected: 9,994)
SELECT 
    'fact_sales Total Rows' AS validation_check,
    COUNT(*) AS actual_value,
    9994 AS expected_value,
    CASE WHEN COUNT(*) = 9994 THEN 'PASSED' ELSE 'FAILED' END AS status
FROM fact_sales;

-- Check 2: Unique Primary Keys in Fact Table (Expected: 9,994)
SELECT 
    'fact_sales Unique row_id Count' AS validation_check,
    COUNT(DISTINCT row_id) AS actual_value,
    9994 AS expected_value,
    CASE WHEN COUNT(DISTINCT row_id) = 9994 THEN 'PASSED' ELSE 'FAILED' END AS status
FROM fact_sales;

-- Check 3: Row ID 3406 and 3407 Duplicate Preservation Check (Expected: 2)
SELECT 
    'Duplicate Row IDs 3406 & 3407 Retained' AS validation_check,
    COUNT(*) AS actual_value,
    2 AS expected_value,
    CASE WHEN COUNT(*) = 2 THEN 'PASSED' ELSE 'FAILED' END AS status
FROM fact_sales
WHERE row_id IN (3406, 3407);

-- Check 4: Total Revenue Financial Reconciliation (Expected: 2,297,200.8600)
SELECT 
    'Total Net Revenue Reconciled ($)' AS validation_check,
    ROUND(SUM(sales), 2) AS actual_value,
    2297200.86 AS expected_value,
    CASE WHEN ROUND(SUM(sales), 2) = 2297200.86 THEN 'PASSED' ELSE 'FAILED' END AS status
FROM fact_sales;

-- Check 5: Total Profit Financial Reconciliation (Expected: 286,397.0200)
SELECT 
    'Total Operating Profit Reconciled ($)' AS validation_check,
    ROUND(SUM(profit), 2) AS actual_value,
    286397.02 AS expected_value,
    CASE WHEN ROUND(SUM(profit), 2) = 286397.02 THEN 'PASSED' ELSE 'FAILED' END AS status
FROM fact_sales;

-- Check 6: Total Quantity Reconciliation (Expected: 37,873)
SELECT 
    'Total Units Sold Reconciled' AS validation_check,
    SUM(quantity) AS actual_value,
    37873 AS expected_value,
    CASE WHEN SUM(quantity) = 37873 THEN 'PASSED' ELSE 'FAILED' END AS status
FROM fact_sales;

-- Check 7: Referential Integrity / Orphan Foreign Key Check (Expected: 0)
SELECT 
    'Orphan Foreign Keys in fact_sales' AS validation_check,
    COUNT(*) AS actual_value,
    0 AS expected_value,
    CASE WHEN COUNT(*) = 0 THEN 'PASSED' ELSE 'FAILED' END AS status
FROM fact_sales f
LEFT JOIN dim_date d_order ON f.order_date_key = d_order.date_key
LEFT JOIN dim_date d_ship ON f.ship_date_key = d_ship.date_key
LEFT JOIN dim_customer c ON f.customer_key = c.customer_key
LEFT JOIN dim_product p ON f.product_key = p.product_key
LEFT JOIN dim_location l ON f.location_key = l.location_key
WHERE d_order.date_key IS NULL
   OR d_ship.date_key IS NULL
   OR c.customer_key IS NULL
   OR p.product_key IS NULL
   OR l.location_key IS NULL;

-- Check 8: Dimension Cardinality Verification
SELECT 'dim_customer' AS dimension_table, COUNT(*) AS total_records, 793 AS expected_records FROM dim_customer
UNION ALL
SELECT 'dim_product' AS dimension_table, COUNT(*) AS total_records, 1894 AS expected_records FROM dim_product
UNION ALL
SELECT 'dim_location' AS dimension_table, COUNT(*) AS total_records, 632 AS expected_records FROM dim_location
UNION ALL
SELECT 'dim_date' AS dimension_table, COUNT(*) AS total_records, 1434 AS expected_records FROM dim_date;
