-- ==============================================================================
-- PROJECT: Sales Data Analysis & Business Intelligence Dashboard
-- MODULE: Phase 4 - Advanced SQL Analytics
-- FILE: sql/03_analytical_queries.sql
-- DESCRIPTION: 20 industry-level business intelligence and analytical queries.
--              Includes CTEs, Window Functions (LAG, SUM OVER, DENSE_RANK),
--              Customer RFM Segmentation, Cohort Metrics, and Profitability Analysis.
-- ==============================================================================

USE sales_analytics_db;

-- ==============================================================================
-- QUERY 1: Executive KPI Summary: Total Sales, Total Profit & Profit Margin %
-- Business Purpose: High-level financial health check. Accurately calculates
-- profit margin as (SUM(profit) / SUM(sales)) * 100 to avoid arithmetic averaging bias.
-- ==============================================================================
SELECT
    ROUND(SUM(sales), 2) AS total_sales,
    ROUND(SUM(profit), 2) AS total_profit,
    ROUND((SUM(profit) / SUM(sales)) * 100, 2) AS overall_profit_margin_pct,
    SUM(quantity) AS total_units_sold,
    ROUND(AVG(sales), 2) AS avg_line_item_sales
FROM fact_sales;


-- ==============================================================================
-- QUERY 2: Total Distinct Orders, Total Customers & Average Order Value (AOV)
-- Business Purpose: Evaluates commercial volume and transaction purchasing size.
-- ==============================================================================
SELECT
    COUNT(DISTINCT order_id) AS total_orders,
    COUNT(DISTINCT customer_key) AS total_unique_customers,
    ROUND(SUM(sales) / COUNT(DISTINCT order_id), 2) AS avg_order_value_usd,
    ROUND(COUNT(DISTINCT order_id) * 1.0 / COUNT(DISTINCT customer_key), 2) AS avg_orders_per_customer
FROM fact_sales;


-- ==============================================================================
-- QUERY 3: Multi-Year Monthly Sales & Profit Trend (Chronological)
-- Business Purpose: Tracks revenue velocity, seasonal peaks, and margin shifts across months.
-- ==============================================================================
SELECT
    d.year,
    d.month,
    d.month_name,
    CONCAT(d.year, '-', LPAD(d.month, 2, '0')) AS year_month,
    ROUND(SUM(f.sales), 2) AS monthly_sales,
    ROUND(SUM(f.profit), 2) AS monthly_profit,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS profit_margin_pct,
    COUNT(DISTINCT f.order_id) AS total_orders
FROM fact_sales f
INNER JOIN dim_date d ON f.order_date_key = d.date_key
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;


-- ==============================================================================
-- QUERY 4: Yearly Sales & Profit Comparison (Annual Commercial Trajectory)
-- Business Purpose: Measures macro enterprise performance year-over-year.
-- ==============================================================================
SELECT
    d.year,
    COUNT(DISTINCT f.order_id) AS total_orders,
    SUM(f.quantity) AS total_units_sold,
    ROUND(SUM(f.sales), 2) AS annual_sales,
    ROUND(SUM(f.profit), 2) AS annual_profit,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS annual_margin_pct
FROM fact_sales f
INNER JOIN dim_date d ON f.order_date_key = d.date_key
GROUP BY d.year
ORDER BY d.year;


-- ==============================================================================
-- QUERY 5: Category-Wise Sales, Profit & Profit Margin Contribution
-- Business Purpose: Pinpoints which broad retail categories generate the bulk of
-- revenue vs. profit, uncovering Furniture's severe margin compression.
-- ==============================================================================
SELECT
    p.category,
    COUNT(DISTINCT f.order_id) AS total_orders,
    SUM(f.quantity) AS total_units_sold,
    ROUND(SUM(f.sales), 2) AS total_sales,
    ROUND(SUM(f.profit), 2) AS total_profit,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS profit_margin_pct,
    ROUND((SUM(f.sales) * 100.0 / (SELECT SUM(sales) FROM fact_sales)), 2) AS sales_contribution_pct
FROM fact_sales f
INNER JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.category
ORDER BY total_sales DESC;


-- ==============================================================================
-- QUERY 6: Sub-Category Profitability & Loss Identification (Tables & Bookcases)
-- Business Purpose: Diagnoses product sub-categories to identify bottom-line leaks.
-- ==============================================================================
SELECT
    p.category,
    p.sub_category,
    COUNT(*) AS total_transactions,
    ROUND(SUM(f.sales), 2) AS total_sales,
    ROUND(SUM(f.profit), 2) AS total_profit,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS profit_margin_pct,
    ROUND(AVG(f.discount) * 100, 2) AS avg_discount_pct,
    CASE WHEN SUM(f.profit) < 0 THEN 'LOSS-MAKING' ELSE 'PROFITABLE' END AS commercial_health
FROM fact_sales f
INNER JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.category, p.sub_category
ORDER BY total_profit ASC;


-- ==============================================================================
-- QUERY 7: Regional Performance & Discount Exposure Analysis
-- Business Purpose: Compares regional sales productivity and evaluates whether
-- heavy discounting in the Central region suppresses operating margins.
-- ==============================================================================
SELECT
    l.region,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(DISTINCT f.customer_key) AS customer_count,
    ROUND(SUM(f.sales), 2) AS total_sales,
    ROUND(SUM(f.profit), 2) AS total_profit,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS regional_margin_pct,
    ROUND(AVG(f.discount) * 100, 2) AS avg_discount_pct
FROM fact_sales f
INNER JOIN dim_location l ON f.location_key = l.location_key
GROUP BY l.region
ORDER BY total_sales DESC;


-- ==============================================================================
-- QUERY 8: Top 10 Revenue-Generating Products
-- Business Purpose: Identifies the corporate flagship products driving gross sales.
-- ==============================================================================
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    SUM(f.quantity) AS total_units_sold,
    ROUND(SUM(f.sales), 2) AS total_sales,
    ROUND(SUM(f.profit), 2) AS total_profit,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS profit_margin_pct
FROM fact_sales f
INNER JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.product_id, p.product_name, p.category, p.sub_category
ORDER BY total_sales DESC
LIMIT 10;


-- ==============================================================================
-- QUERY 9: Top 10 Most Profitable Products
-- Business Purpose: Identifies true commercial champions maximizing bottom-line cash.
-- ==============================================================================
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    SUM(f.quantity) AS units_sold,
    ROUND(SUM(f.sales), 2) AS total_sales,
    ROUND(SUM(f.profit), 2) AS total_profit,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS profit_margin_pct
FROM fact_sales f
INNER JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.product_id, p.product_name, p.category, p.sub_category
ORDER BY total_profit DESC
LIMIT 10;


-- ==============================================================================
-- QUERY 10: Worst 10 Loss-Making Products (Critical Margin Destruction Audit)
-- Business Purpose: Identifies SKUs generating significant cumulative losses.
-- ==============================================================================
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    SUM(f.quantity) AS units_sold,
    ROUND(SUM(f.sales), 2) AS total_sales,
    ROUND(SUM(f.profit), 2) AS net_loss_usd,
    ROUND(AVG(f.discount) * 100, 2) AS avg_discount_pct
FROM fact_sales f
INNER JOIN dim_product p ON f.product_key = p.product_key
GROUP BY p.product_id, p.product_name, p.category, p.sub_category
HAVING SUM(f.profit) < 0
ORDER BY net_loss_usd ASC
LIMIT 10;


-- ==============================================================================
-- QUERY 11: Top 10 Customers Ranked by Total Sales & Lifetime Margin
-- Business Purpose: Uncovers high-value corporate accounts for dedicated relationship management.
-- ==============================================================================
SELECT
    c.customer_id,
    c.customer_name,
    c.segment,
    COUNT(DISTINCT f.order_id) AS total_orders_placed,
    SUM(f.quantity) AS total_items_bought,
    ROUND(SUM(f.sales), 2) AS lifetime_sales,
    ROUND(SUM(f.profit), 2) AS lifetime_profit,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS lifetime_margin_pct
FROM fact_sales f
INNER JOIN dim_customer c ON f.customer_key = c.customer_key
GROUP BY c.customer_id, c.customer_name, c.segment
ORDER BY lifetime_sales DESC
LIMIT 10;


-- ==============================================================================
-- QUERY 12: Customer RFM Segmentation Analysis (Recency, Frequency, Monetary)
-- Business Purpose: Segments customers into actionable behavioral tiers.
-- Reference Date: '2017-12-31' (The end of the 4-year retail reporting horizon).
-- Segmentation Rules:
--   - Champions: Recency <= 60 days, Frequency >= 8 orders, Monetary >= $4,000
--   - Loyal Customers: Recency <= 120 days, Frequency >= 5 orders
--   - Potential Loyalists: Recency <= 90 days, Frequency < 5 orders
--   - At Risk: Recency BETWEEN 121 AND 300 days, Frequency >= 4 orders
--   - Hibernating / Lost: Recency > 300 days
-- ==============================================================================
WITH customer_rfm_raw AS (
    SELECT
        c.customer_key,
        c.customer_id,
        c.customer_name,
        c.segment,
        DATEDIFF('2017-12-31', MAX(d.full_date)) AS recency_days,
        COUNT(DISTINCT f.order_id) AS frequency_orders,
        ROUND(SUM(f.sales), 2) AS monetary_value_usd,
        ROUND(SUM(f.profit), 2) AS total_profit_usd
    FROM fact_sales f
    INNER JOIN dim_customer c ON f.customer_key = c.customer_key
    INNER JOIN dim_date d ON f.order_date_key = d.date_key
    GROUP BY c.customer_key, c.customer_id, c.customer_name, c.segment
)
SELECT
    customer_id,
    customer_name,
    segment,
    recency_days,
    frequency_orders,
    monetary_value_usd,
    total_profit_usd,
    CASE
        WHEN recency_days <= 60 AND frequency_orders >= 8 AND monetary_value_usd >= 4000 THEN 'Champions'
        WHEN recency_days <= 120 AND frequency_orders >= 5 THEN 'Loyal Customers'
        WHEN recency_days <= 90 AND frequency_orders < 5 THEN 'Potential Loyalists'
        WHEN recency_days BETWEEN 121 AND 300 AND frequency_orders >= 4 THEN 'At Risk'
        WHEN recency_days > 300 THEN 'Hibernating / Lost'
        ELSE 'Regular / Promising'
    END AS rfm_segment
FROM customer_rfm_raw
ORDER BY monetary_value_usd DESC
LIMIT 20;


-- ==============================================================================
-- QUERY 13: Cumulative Running Total of Monthly Sales (Window Function SUM OVER)
-- Business Purpose: Analyzes cumulative cash flow and progression across the business lifecycle.
-- ==============================================================================
WITH monthly_sales_agg AS (
    SELECT
        d.year,
        d.month,
        CONCAT(d.year, '-', LPAD(d.month, 2, '0')) AS year_month,
        ROUND(SUM(f.sales), 2) AS monthly_sales,
        ROUND(SUM(f.profit), 2) AS monthly_profit
    FROM fact_sales f
    INNER JOIN dim_date d ON f.order_date_key = d.date_key
    GROUP BY d.year, d.month
)
SELECT
    year,
    month,
    year_month,
    monthly_sales,
    monthly_profit,
    ROUND(SUM(monthly_sales) OVER (ORDER BY year, month), 2) AS running_total_sales,
    ROUND(SUM(monthly_profit) OVER (ORDER BY year, month), 2) AS running_total_profit
FROM monthly_sales_agg
ORDER BY year, month;


-- ==============================================================================
-- QUERY 14: Month-over-Month (MoM) Sales Growth Rate using LAG()
-- Business Purpose: Tracks immediate short-term sales velocity and identifies seasonal shifts.
-- ==============================================================================
WITH monthly_data AS (
    SELECT
        d.year,
        d.month,
        CONCAT(d.year, '-', LPAD(d.month, 2, '0')) AS year_month,
        ROUND(SUM(f.sales), 2) AS current_month_sales
    FROM fact_sales f
    INNER JOIN dim_date d ON f.order_date_key = d.date_key
    GROUP BY d.year, d.month
)
SELECT
    year,
    month,
    year_month,
    current_month_sales,
    LAG(current_month_sales, 1) OVER (ORDER BY year, month) AS prior_month_sales,
    ROUND(current_month_sales - LAG(current_month_sales, 1) OVER (ORDER BY year, month), 2) AS mom_dollar_change,
    ROUND(
        (current_month_sales - LAG(current_month_sales, 1) OVER (ORDER BY year, month)) * 100.0 /
        NULLIF(LAG(current_month_sales, 1) OVER (ORDER BY year, month), 0),
        2
    ) AS mom_growth_pct
FROM monthly_data
ORDER BY year, month;


-- ==============================================================================
-- QUERY 15: Year-over-Year (YoY) Monthly Sales Comparison using LAG(12)
-- Business Purpose: Removes annual seasonality to measure true growth vs. prior year.
-- ==============================================================================
WITH monthly_agg AS (
    SELECT
        d.year,
        d.month,
        CONCAT(d.year, '-', LPAD(d.month, 2, '0')) AS year_month,
        ROUND(SUM(f.sales), 2) AS monthly_sales
    FROM fact_sales f
    INNER JOIN dim_date d ON f.order_date_key = d.date_key
    GROUP BY d.year, d.month
)
SELECT
    year,
    month,
    year_month,
    monthly_sales AS current_sales,
    LAG(monthly_sales, 12) OVER (ORDER BY year, month) AS same_month_last_year_sales,
    ROUND(monthly_sales - LAG(monthly_sales, 12) OVER (ORDER BY year, month), 2) AS yoy_dollar_growth,
    ROUND(
        (monthly_sales - LAG(monthly_sales, 12) OVER (ORDER BY year, month)) * 100.0 /
        NULLIF(LAG(monthly_sales, 12) OVER (ORDER BY year, month), 0),
        2
    ) AS yoy_growth_pct
FROM monthly_agg
ORDER BY year, month;


-- ==============================================================================
-- QUERY 16: Regional Sales & Profit Rankings using DENSE_RANK()
-- Business Purpose: Ranks territories by sales volume and profitability independently.
-- ==============================================================================
SELECT
    l.region,
    ROUND(SUM(f.sales), 2) AS total_sales,
    DENSE_RANK() OVER (ORDER BY SUM(f.sales) DESC) AS sales_rank,
    ROUND(SUM(f.profit), 2) AS total_profit,
    DENSE_RANK() OVER (ORDER BY SUM(f.profit) DESC) AS profit_rank,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS profit_margin_pct
FROM fact_sales f
INNER JOIN dim_location l ON f.location_key = l.location_key
GROUP BY l.region
ORDER BY sales_rank;


-- ==============================================================================
-- QUERY 17: Discount Depth vs. Profitability: Margin Destruction Analysis
-- Business Purpose: Analyzes average margins across tiered discount buckets.
-- Proves that discounts > 20% systematically destroy retail operating margin.
-- ==============================================================================
SELECT
    CASE
        WHEN f.discount = 0.00 THEN '0% (No Discount)'
        WHEN f.discount <= 0.10 THEN '1% - 10%'
        WHEN f.discount <= 0.20 THEN '11% - 20%'
        WHEN f.discount <= 0.40 THEN '21% - 40%'
        ELSE 'Over 40% (Deep Clearance)'
    END AS discount_tier,
    COUNT(*) AS total_transactions,
    ROUND(SUM(f.sales), 2) AS total_sales,
    ROUND(SUM(f.profit), 2) AS total_profit,
    ROUND((SUM(f.profit) / SUM(f.sales)) * 100, 2) AS profit_margin_pct,
    SUM(CASE WHEN f.profit < 0 THEN 1 ELSE 0 END) AS loss_making_orders_count,
    ROUND(SUM(CASE WHEN f.profit < 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS loss_order_pct
FROM fact_sales f
GROUP BY discount_tier
ORDER BY MIN(f.discount);


-- ==============================================================================
-- QUERY 18: Average Shipping Duration & Delivery Efficiency by Shipping Mode
-- Business Purpose: Benchmarks logistics speed across different shipping options.
-- ==============================================================================
SELECT
    f.ship_mode,
    COUNT(DISTINCT f.order_id) AS total_orders,
    ROUND(AVG(f.shipping_duration_days), 2) AS avg_transit_days,
    MIN(f.shipping_duration_days) AS min_transit_days,
    MAX(f.shipping_duration_days) AS max_transit_days,
    ROUND(SUM(f.sales), 2) AS total_sales,
    ROUND(SUM(f.profit), 2) AS total_profit
FROM fact_sales f
GROUP BY f.ship_mode
ORDER BY avg_transit_days ASC;


-- ==============================================================================
-- QUERY 19: Top 5 Customers in Each Region (Window Function PARTITION BY)
-- Business Purpose: Surfaces the leading territorial accounts for regional managers.
-- ==============================================================================
WITH regional_customer_sales AS (
    SELECT
        l.region,
        c.customer_id,
        c.customer_name,
        ROUND(SUM(f.sales), 2) AS total_sales,
        ROUND(SUM(f.profit), 2) AS total_profit,
        DENSE_RANK() OVER (
            PARTITION BY l.region 
            ORDER BY SUM(f.sales) DESC
        ) AS regional_rank
    FROM fact_sales f
    INNER JOIN dim_customer c ON f.customer_key = c.customer_key
    INNER JOIN dim_location l ON f.location_key = l.location_key
    GROUP BY l.region, c.customer_id, c.customer_name
)
SELECT
    region,
    regional_rank,
    customer_id,
    customer_name,
    total_sales,
    total_profit
FROM regional_customer_sales
WHERE regional_rank <= 5
ORDER BY region, regional_rank;


-- ==============================================================================
-- QUERY 20: Orders with Negative Net Operating Profit (Severe Revenue Bleed)
-- Business Purpose: Discovers entire multi-item orders resulting in net deficits.
-- ==============================================================================
SELECT
    f.order_id,
    d.full_date AS order_date,
    c.customer_name,
    l.city,
    l.state,
    COUNT(*) AS line_items_in_order,
    ROUND(SUM(f.sales), 2) AS total_order_sales,
    ROUND(SUM(f.profit), 2) AS total_order_net_loss,
    ROUND(AVG(f.discount) * 100, 2) AS avg_order_discount_pct
FROM fact_sales f
INNER JOIN dim_customer c ON f.customer_key = c.customer_key
INNER JOIN dim_location l ON f.location_key = l.location_key
INNER JOIN dim_date d ON f.order_date_key = d.date_key
GROUP BY f.order_id, d.full_date, c.customer_name, l.city, l.state
HAVING SUM(f.profit) < 0
ORDER BY total_order_net_loss ASC
LIMIT 15;
