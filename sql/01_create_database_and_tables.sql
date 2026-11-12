-- ==============================================================================
-- PROJECT: Sales Data Analysis & Business Intelligence Dashboard
-- MODULE: Phase 4 - MySQL Database Modeling
-- FILE: sql/01_create_database_and_tables.sql
-- DESCRIPTION: DDL script to create the database, Star Schema dimensional tables,
--              fact table, constraints, primary keys, foreign keys, and indexes.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Database Initialization
-- ------------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS sales_analytics_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE sales_analytics_db;

-- ------------------------------------------------------------------------------
-- 2. Drop Existing Tables (in reverse foreign key dependency order)
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_location;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_date;

-- ------------------------------------------------------------------------------
-- 3. Create Dimension Tables
-- ------------------------------------------------------------------------------

-- Table: dim_date
-- Purpose: Conformed calendar dimension supporting role-playing foreign keys
--          (order_date_key and ship_date_key).
CREATE TABLE dim_date (
    date_key INT NOT NULL COMMENT 'Surrogate Primary Key in YYYYMMDD format (e.g., 20140423)',
    full_date DATE NOT NULL COMMENT 'Exact calendar date',
    year INT NOT NULL COMMENT 'Calendar year (e.g., 2014, 2015, 2016, 2017)',
    month INT NOT NULL COMMENT 'Month number (1 to 12)',
    month_name VARCHAR(20) NOT NULL COMMENT 'Full month name (e.g., January, April)',
    quarter INT NOT NULL COMMENT 'Calendar quarter (1 to 4)',
    day_name VARCHAR(20) NOT NULL COMMENT 'Day of the week (e.g., Monday, Wednesday)',
    CONSTRAINT pk_dim_date PRIMARY KEY (date_key),
    CONSTRAINT uq_dim_date_full_date UNIQUE (full_date),
    INDEX idx_dim_date_year_month (year, month),
    INDEX idx_dim_date_quarter (quarter)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Calendar dimension table covering historical transaction dates';

-- Table: dim_customer
-- Purpose: Stores unique customer demographic and segmentation attributes.
CREATE TABLE dim_customer (
    customer_key INT AUTO_INCREMENT NOT NULL COMMENT 'Surrogate Primary Key for customer dimension',
    customer_id VARCHAR(20) NOT NULL COMMENT 'Natural business customer identifier (e.g., CG-12520)',
    customer_name VARCHAR(150) NOT NULL COMMENT 'Full name of the customer',
    segment VARCHAR(50) NOT NULL COMMENT 'Customer segment (Consumer, Corporate, Home Office)',
    CONSTRAINT pk_dim_customer PRIMARY KEY (customer_key),
    CONSTRAINT uq_dim_customer_id UNIQUE (customer_id),
    INDEX idx_dim_customer_segment (segment),
    INDEX idx_dim_customer_name (customer_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Customer dimension table with natural key and customer segmentations';

-- Table: dim_product
-- Purpose: Stores product catalog, hierarchy, category, and sub-category.
CREATE TABLE dim_product (
    product_key INT AUTO_INCREMENT NOT NULL COMMENT 'Surrogate Primary Key for product dimension',
    product_id VARCHAR(50) NOT NULL COMMENT 'Business product code / SKU (e.g., FUR-BO-10001798)',
    product_name VARCHAR(255) NOT NULL COMMENT 'Full descriptive title of the retail product',
    category VARCHAR(50) NOT NULL COMMENT 'High-level department (Furniture, Office Supplies, Technology)',
    sub_category VARCHAR(50) NOT NULL COMMENT 'Specific sub-category (Chairs, Phones, Binders, Tables, etc.)',
    CONSTRAINT pk_dim_product PRIMARY KEY (product_key),
    INDEX idx_dim_product_id (product_id),
    INDEX idx_dim_product_category (category),
    INDEX idx_dim_product_sub_category (sub_category),
    INDEX idx_dim_product_name (product_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Product catalog dimension containing categories and item classifications';

-- Table: dim_location
-- Purpose: Geographical hierarchy for store orders (Country, City, State, ZIP, Region).
CREATE TABLE dim_location (
    location_key INT AUTO_INCREMENT NOT NULL COMMENT 'Surrogate Primary Key for geographic location',
    country VARCHAR(50) NOT NULL DEFAULT 'United States' COMMENT 'Country of delivery',
    city VARCHAR(100) NOT NULL COMMENT 'City name',
    state VARCHAR(100) NOT NULL COMMENT 'State or territory name',
    postal_code VARCHAR(20) NOT NULL COMMENT 'Standard 5-digit zero-padded ZIP code string',
    region VARCHAR(50) NOT NULL COMMENT 'Sales territory region (Central, East, South, West)',
    CONSTRAINT pk_dim_location PRIMARY KEY (location_key),
    INDEX idx_dim_location_region (region),
    INDEX idx_dim_location_state (state),
    INDEX idx_dim_location_city (city),
    INDEX idx_dim_location_postal (postal_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Geographical dimension capturing shipping and market destinations';

-- ------------------------------------------------------------------------------
-- 4. Create Fact Table: fact_sales
-- ------------------------------------------------------------------------------
-- Grain: One row per individual retail sales transaction line item.
-- Total Rows: Exactly 9,994 records (reconciling with raw and processed datasets).
-- Primary Key: row_id (Preserving original sequence 1..9994, including 3406 & 3407).
-- Role-Playing Dates: order_date_key and ship_date_key both point to dim_date(date_key).
CREATE TABLE fact_sales (
    row_id INT NOT NULL COMMENT 'Surrogate Primary Key representing the transaction line item (1 to 9994)',
    order_id VARCHAR(30) NOT NULL COMMENT 'Degenerate business order identifier (e.g., CA-2016-152156)',
    order_date_key INT NOT NULL COMMENT 'Role-playing foreign key to dim_date for order placement date',
    ship_date_key INT NOT NULL COMMENT 'Role-playing foreign key to dim_date for order fulfillment date',
    customer_key INT NOT NULL COMMENT 'Foreign key to dim_customer(customer_key)',
    product_key INT NOT NULL COMMENT 'Foreign key to dim_product(product_key)',
    location_key INT NOT NULL COMMENT 'Foreign key to dim_location(location_key)',
    ship_mode VARCHAR(50) NOT NULL COMMENT 'Logistics class (Standard Class, Second Class, First Class, Same Day)',
    sales DECIMAL(12, 4) NOT NULL COMMENT 'Gross sales revenue in USD ($)',
    quantity INT NOT NULL COMMENT 'Number of units ordered (>= 1)',
    discount DECIMAL(5, 4) NOT NULL COMMENT 'Promotional discount rate (0.0000 to 0.8000)',
    profit DECIMAL(12, 4) NOT NULL COMMENT 'Net operating margin in USD ($) (positive or negative)',
    total_cost DECIMAL(12, 4) NOT NULL COMMENT 'Cost of goods sold (COGS = sales - profit)',
    unit_selling_price DECIMAL(12, 4) NOT NULL COMMENT 'Realized selling price per unit (sales / quantity)',
    unit_cost DECIMAL(12, 4) NOT NULL COMMENT 'Cost per unit (total_cost / quantity)',
    profit_margin_pct DECIMAL(9, 4) NOT NULL COMMENT 'Operating profit percentage ((profit / sales) * 100)',
    shipping_duration_days INT NOT NULL COMMENT 'Transit duration elapsed between order and ship dates (>= 0)',
    
    -- Primary Key Constraint
    CONSTRAINT pk_fact_sales PRIMARY KEY (row_id),
    
    -- Foreign Key Constraints
    CONSTRAINT fk_sales_order_date FOREIGN KEY (order_date_key) 
        REFERENCES dim_date (date_key) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_sales_ship_date FOREIGN KEY (ship_date_key) 
        REFERENCES dim_date (date_key) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_sales_customer FOREIGN KEY (customer_key) 
        REFERENCES dim_customer (customer_key) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_sales_product FOREIGN KEY (product_key) 
        REFERENCES dim_product (product_key) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_sales_location FOREIGN KEY (location_key) 
        REFERENCES dim_location (location_key) ON UPDATE CASCADE ON DELETE RESTRICT,
        
    -- Analytical Performance Indexes
    INDEX idx_sales_order_id (order_id),
    INDEX idx_sales_order_date (order_date_key),
    INDEX idx_sales_ship_date (ship_date_key),
    INDEX idx_sales_customer (customer_key),
    INDEX idx_sales_product (product_key),
    INDEX idx_sales_location (location_key),
    INDEX idx_sales_ship_mode (ship_mode)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Central fact table storing retail sales transactions and measures at line-item grain';
