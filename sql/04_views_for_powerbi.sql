-- ==============================================================================
-- PROJECT: Sales Data Analysis & Business Intelligence Dashboard
-- MODULE: Phase 4 - Database Modeling & Views
-- FILE: sql/04_views_for_powerbi.sql
-- DESCRIPTION: Pre-aggregated and denormalized analytical views optimized for
--              direct ingestion and reporting in Microsoft Power BI.
-- ==============================================================================

USE sales_analytics_db;

-- ------------------------------------------------------------------------------
-- 1. View: vw_sales_summary
-- Purpose: Denormalized transactional view with complete dimensional context.
--          Grain: One row per sales line item (9,994 rows).
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_sales_summary;

CREATE VIEW vw_sales_summary AS
SELECT
    f.row_id,
    f.order_id,
    d_order.full_date AS order_date,
    d_order.year AS order_year,
    d_order.quarter AS order_quarter,
    d_order.month AS order_month,
    d_order.month_name AS order_month_name,
    d_order.day_name AS order_day_name,
    d_ship.full_date AS ship_date,
    f.shipping_duration_days,
    f.ship_mode,
    c.customer_id,
    c.customer_name,
    c.segment AS customer_segment,
    p.product_id,
    p.product_name,
    p.category AS product_category,
    p.sub_category AS product_sub_category,
    l.country,
    l.city,
    l.state,
    l.postal_code,
    l.region,
    f.sales,
    f.quantity,
    f.discount,
    f.profit,
    f.total_cost,
    f.unit_selling_price,
    f.unit_cost,
    f.profit_margin_pct,
    CASE WHEN f.profit < 0 THEN 1 ELSE 0 END AS is_loss_order
FROM fact_sales f
INNER JOIN dim_date d_order ON f.order_date_key = d_order.date_key
INNER JOIN dim_date d_ship ON f.ship_date_key = d_ship.date_key
INNER JOIN dim_customer c ON f.customer_key = c.customer_key
INNER JOIN dim_product p ON f.product_key = p.product_key
INNER JOIN dim_location l ON f.location_key = l.location_key;


-- ------------------------------------------------------------------------------
-- 2. View: vw_monthly_sales
-- Purpose: Pre-aggregated monthly financial KPIs for trend visuals.
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_monthly_sales;

CREATE VIEW vw_monthly_sales AS
SELECT
    d.year AS order_year,
    d.month AS order_month,
    d.month_name AS order_month_name,
    CONCAT(d.year, '-', LPAD(d.month, 2, '0')) AS year_month_label,
    ROUND(SUM(f.sales), 2) AS total_sales,
    ROUND(SUM(f.profit), 2) AS total_profit,
    ROUND(SUM(f.total_cost), 2) AS total_cogs,
    SUM(f.quantity) AS total_units_sold,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(DISTINCT f.customer_key) AS active_customers,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS profit_margin_pct,
    ROUND(AVG(f.discount) * 100, 2) AS avg_discount_pct
FROM fact_sales f
INNER JOIN dim_date d ON f.order_date_key = d.date_key
GROUP BY d.year, d.month, d.month_name;


-- ------------------------------------------------------------------------------
-- 3. View: vw_category_performance
-- Purpose: Hierarchical category and sub-category performance summary.
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_category_performance;

CREATE VIEW vw_category_performance AS
SELECT
    p.category,
    p.sub_category,
    COUNT(*) AS total_transactions,
    COUNT(DISTINCT f.order_id) AS total_orders,
    SUM(f.quantity) AS total_units_sold,
    ROUND(SUM(f.sales), 2) AS total_sales,
    ROUND(SUM(f.profit), 2) AS total_profit,
    ROUND(SUM(f.total_cost), 2) AS total_cost,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS profit_margin_pct,
    ROUND(AVG(f.discount) * 100, 2) AS avg_discount_pct,
    SUM(CASE WHEN f.profit < 0 THEN 1 ELSE 0 END) AS loss_transactions_count,
    ROUND(SUM(CASE WHEN f.profit < 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS loss_rate_pct
FROM fact_sales f
INNER JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.category, p.sub_category;


-- ------------------------------------------------------------------------------
-- 4. View: vw_region_performance
-- Purpose: Territorial performance matrix by Region, State, and City.
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_region_performance;

CREATE VIEW vw_region_performance AS
SELECT
    l.region,
    l.state,
    l.city,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(DISTINCT f.customer_key) AS unique_customers,
    SUM(f.quantity) AS total_units,
    ROUND(SUM(f.sales), 2) AS total_sales,
    ROUND(SUM(f.profit), 2) AS total_profit,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS profit_margin_pct,
    ROUND(AVG(f.discount) * 100, 2) AS avg_discount_pct
FROM fact_sales f
INNER JOIN dim_location l ON f.location_key = l.location_key
GROUP BY l.region, l.state, l.city;


-- ------------------------------------------------------------------------------
-- 5. View: vw_product_performance
-- Purpose: Granular SKU-level analytics for inventory and pricing decisions.
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_product_performance;

CREATE VIEW vw_product_performance AS
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    COUNT(*) AS total_orders_count,
    SUM(f.quantity) AS total_units_sold,
    ROUND(SUM(f.sales), 2) AS total_sales,
    ROUND(SUM(f.profit), 2) AS total_profit,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS profit_margin_pct,
    ROUND(AVG(f.discount) * 100, 2) AS avg_discount_pct,
    CASE WHEN SUM(f.profit) < 0 THEN 'Loss Maker' ELSE 'Profitable' END AS profitability_tier
FROM fact_sales f
INNER JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.product_id, p.product_name, p.category, p.sub_category;


-- ------------------------------------------------------------------------------
-- 6. View: vw_customer_performance
-- Purpose: Customer Lifetime Value (CLV) and purchasing profiles.
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_customer_performance;

CREATE VIEW vw_customer_performance AS
SELECT
    c.customer_id,
    c.customer_name,
    c.segment,
    COUNT(DISTINCT f.order_id) AS total_orders_placed,
    SUM(f.quantity) AS total_units_purchased,
    ROUND(SUM(f.sales), 2) AS lifetime_sales,
    ROUND(SUM(f.profit), 2) AS lifetime_profit,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS lifetime_margin_pct,
    ROUND(SUM(f.sales) / COUNT(DISTINCT f.order_id), 2) AS avg_order_value_usd,
    MIN(d.full_date) AS first_order_date,
    MAX(d.full_date) AS last_order_date,
    DATEDIFF('2017-12-31', MAX(d.full_date)) AS recency_days
FROM fact_sales f
INNER JOIN dim_customer c ON f.customer_key = c.customer_key
INNER JOIN dim_date d ON f.order_date_key = d.date_key
GROUP BY c.customer_id, c.customer_name, c.segment;
