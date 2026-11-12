# Power BI Integration & Interactive Dashboard Architecture Guide

**Project:** Sales Data Analysis & Business Intelligence Dashboard  
**Target Database:** `sales_analytics_db` (MySQL 8.0+)  
**Source DDL & Views:** [`sql/01_create_database_and_tables.sql`](../sql/01_create_database_and_tables.sql) | [`sql/04_views_for_powerbi.sql`](../sql/04_views_for_powerbi.sql)  
**Offline CSV Fallback Extracts:** `powerbi/data_extracts/` (generated via [`src/export_powerbi_views.py`](../src/export_powerbi_views.py))

---

## 1. MySQL Connector Setup in Power BI Desktop

### Prerequisites
- **Power BI Desktop** (latest release)
- **MySQL Connector/NET** (v8.0+ / compatible ADO.NET driver for Power BI Desktop)
- Running MySQL instance loaded via `src/load_to_mysql.py`

### Step-by-Step Connection Instructions
1. Open **Power BI Desktop** and select **Home → Get Data → More...**
2. Search for **MySQL database** and click **Connect**.
3. Enter connection parameters:
   - **Server:** `localhost` (or `localhost:3306`)
   - **Database:** `sales_analytics_db`
4. Click **OK**, select **Database** authentication, and enter your MySQL username (`root` or read-only BI service user) and password. Click **Connect**.
5. In the **Navigator** window, select:
   - **Core Star Schema Tables (Recommended for Dynamic DAX Slicing):**
     - `dim_date`
     - `dim_customer`
     - `dim_product`
     - `dim_location`
     - `fact_sales`
   - **Pre-Aggregated Analytical Views (Optional / Fast Reference):**
     - `vw_sales_summary`
     - `vw_monthly_sales`
     - `vw_category_performance`
     - `vw_region_performance`
     - `vw_product_performance`
     - `vw_customer_performance`
6. Click **Load** (or **Transform Data** in Power Query to verify types: `sales`/`profit`/`total_cost` as Fixed Decimal Number, `postal_code` as Text, `full_date` as Date).

> **Offline / Portable Alternative (No MySQL Server Required):**  
> Run `python src/export_powerbi_views.py` and connect Power BI Desktop via **Get Data → Text/CSV** to load the exact Star Schema tables and `vw_*` extracts from `powerbi/data_extracts/`.

---

## 2. Deployed View Catalog (`sql/04_views_for_powerbi.sql`)

| View Name | Grain / Purpose | Key Columns |
|---|---|---|
| `vw_sales_summary` | Line-item denormalized table (9,994 rows) | `row_id`, `order_id`, `order_date`, `order_year`, `order_quarter`, `order_month`, `order_month_name`, `order_day_name`, `ship_date`, `shipping_duration_days`, `ship_mode`, `customer_id`, `customer_name`, `customer_segment`, `product_id`, `product_name`, `product_category`, `product_sub_category`, `country`, `city`, `state`, `postal_code`, `region`, `sales`, `quantity`, `discount`, `profit`, `total_cost`, `unit_selling_price`, `unit_cost`, `profit_margin_pct`, `is_loss_order` |
| `vw_monthly_sales` | Monthly revenue & KPI trend | `order_year`, `order_month`, `order_month_name`, `year_month_label`, `total_sales`, `total_profit`, `total_cogs`, `total_units_sold`, `total_orders`, `active_customers`, `profit_margin_pct`, `avg_discount_pct` |
| `vw_category_performance` | Category & sub-category scorecard | `category`, `sub_category`, `total_transactions`, `total_orders`, `total_units_sold`, `total_sales`, `total_profit`, `total_cost`, `profit_margin_pct`, `avg_discount_pct`, `loss_transactions_count`, `loss_rate_pct` |
| `vw_region_performance` | Geographic rollups | `region`, `state`, `city`, `total_orders`, `unique_customers`, `total_units`, `total_sales`, `total_profit`, `profit_margin_pct`, `avg_discount_pct` |
| `vw_product_performance` | SKU profitability & tiering | `product_id`, `product_name`, `category`, `sub_category`, `total_orders_count`, `total_units_sold`, `total_sales`, `total_profit`, `profit_margin_pct`, `avg_discount_pct`, `profitability_tier` |
| `vw_customer_performance` | Customer LTV & recency | `customer_id`, `customer_name`, `segment`, `total_orders_placed`, `total_units_purchased`, `lifetime_sales`, `lifetime_profit`, `lifetime_margin_pct`, `avg_order_value_usd`, `first_order_date`, `last_order_date`, `recency_days` |

---

## 3. Star Schema Relationship Diagram

All dimension tables filter `fact_sales` with **Single-direction (`1:*`)** cross-filtering (`One` on Dimension → `Many` on Fact).

```text
+-----------------------------------+          +------------------------------------+
|            dim_date               |          |            dim_customer            |
|-----------------------------------|          |------------------------------------|
| PK date_key (YYYYMMDD)            |          | PK customer_key                    |
|    full_date                      |          |    customer_id                     |
|    year, month, month_name        |          |    customer_name                   |
|    quarter, day_name              |          |    segment                         |
+-----------------------------------+          +------------------------------------+
        | 1                     | 1 (Inactive)                  | 1
        | order_date_key        | ship_date_key                 | customer_key
        v *                     v *                             v *
+-----------------------------------------------------------------------------------+
|                                   fact_sales                                      |
|-----------------------------------------------------------------------------------|
| PK row_id | order_id | ship_mode | sales | quantity | discount | profit           |
| FK order_date_key | FK ship_date_key | FK customer_key | FK product_key           |
| FK location_key | total_cost | unit_selling_price | unit_cost | profit_margin_pct |
| shipping_duration_days                                                            |
+-----------------------------------------------------------------------------------+
        ^ *                                                     ^ *
        | product_key                                           | location_key
        | 1                                                     | 1
+-----------------------------------+          +------------------------------------+
|           dim_product             |          |            dim_location            |
|-----------------------------------|          |------------------------------------|
| PK product_key                    |          | PK location_key                    |
|    product_id, product_name       |          |    country, region, state          |
|    category, sub_category         |          |    city, postal_code               |
+-----------------------------------+          +------------------------------------+
```

### Model Configuration Rules in Power BI
1. Mark `dim_date` as a **Date Table** using `dim_date[full_date]`.
2. Keep `dim_date[date_key] -> fact_sales[order_date_key]` as the **Active** relationship, and `dim_date[date_key] -> fact_sales[ship_date_key]` as **Inactive** (invoke via `USERELATIONSHIP` when needed).
3. Hide surrogate keys (`*_key`) in Report View to keep the field list clean for business users.

---

## 4. Production DAX Measures Library

Create a dedicated `_Measures` table in Power BI Desktop and add the following DAX measures:

```dax
Total Sales =
SUM(fact_sales[sales])
```

```dax
Total Profit =
SUM(fact_sales[profit])
```

```dax
Profit Margin % =
DIVIDE([Total Profit], [Total Sales], 0)
```

```dax
Prior Year Sales =
CALCULATE(
    [Total Sales],
    SAMEPERIODLASTYEAR(dim_date[full_date])
)
```

```dax
YoY Sales Growth % =
VAR CurrentSales = [Total Sales]
VAR LastYearSales = [Prior Year Sales]
RETURN
DIVIDE(CurrentSales - LastYearSales, LastYearSales, BLANK())
```

```dax
Total Orders =
DISTINCTCOUNT(fact_sales[order_id])
```

```dax
Average Order Value =
DIVIDE([Total Sales], [Total Orders], 0)
```

```dax
Discount Leakage Loss $ =
CALCULATE(
    SUM(fact_sales[profit]),
    fact_sales[discount] > 0.20,
    fact_sales[profit] < 0
)
```

```dax
Loss-Making Orders Count =
CALCULATE(
    DISTINCTCOUNT(fact_sales[order_id]),
    FILTER(
        VALUES(fact_sales[order_id]),
        CALCULATE([Total Profit]) < 0
    )
)
```

> **Formatting Recommendations:** Format `[Total Sales]`, `[Total Profit]`, `[Average Order Value]`, and `[Discount Leakage Loss $]` as `$#,##0.00`; `[Profit Margin %]` and `[YoY Sales Growth %]` as `0.00%`; `[Total Orders]` and `[Loss-Making Orders Count]` as `#,##0`.

---

## 5. 3-Page Interactive Dashboard Wireframe Specification

### Global Slicers (Shared Across Pages 1–3)
- `dim_date[year]` (Dropdown / Tile slicer: 2014–2017)
- `dim_location[region]` (Multi-select tile: West, East, Central, South)
- `dim_product[category]` (Furniture, Office Supplies, Technology)
- `dim_customer[segment]` (Consumer, Corporate, Home Office)

### Page 1: Executive Overview
- **Top Row (KPI Cards):**
  - `[Total Sales]` (`$2.30M`) | `[Total Profit]` (`$286.40K`) | `[Profit Margin %]` (`12.47%`) | `[Total Orders]` (`5,009`) | `[Average Order Value]` (`$458.61`) | `[YoY Sales Growth %]`
- **Middle Left (Line & Clustered Column / Dual-Line Chart):**
  - **Monthly Sales & Profit Trend:** X-axis `dim_date[year]` + `dim_date[month_name]` (sorted by `month`), Values `[Total Sales]` & `[Total Profit]` — highlights Q4 (Sept–Dec) revenue surges.
- **Middle Right (Filled Map / Bubble Map):**
  - **Regional & State Performance:** Location `dim_location[state]` (Data Category: State or Province), Bubble Size `[Total Sales]`, Color Saturation `[Profit Margin %]`.
- **Bottom (Clustered Bar / Donut + Matrix):**
  - **Category Breakdown:** `dim_product[category]` showing `[Total Sales]`, `[Total Profit]`, `[Profit Margin %]`, and % of Total Sales.

### Page 2: Margin & Discount Leakage Analysis
- **Top Banner KPIs:** `[Discount Leakage Loss $]` (`-$135,376.06` across `discount > 20%` loss lines), `[Loss-Making Orders Count]`, Avg Discount % (`AVERAGE(fact_sales[discount])`).
- **Left Visual (Horizontal Bar Chart):**
  - **Sub-Category Profit & Margin Bar Chart:** Axis `dim_product[sub_category]`, Value `[Total Profit]` (or `[Profit Margin %]`), conditional color formatting (`#2CA02C` if `>= 0`, `#D62728` if `< 0`), immediately spotlighting `Tables`, `Bookcases`, and `Supplies`.
- **Right Visual (Scatter Plot):**
  - **Discount % vs. Profit Margin %:** Details `fact_sales[order_id]` or `dim_product[sub_category]`, X-axis `AVERAGE(fact_sales[discount])`, Y-axis `[Profit Margin %]`, Size `[Total Sales]`, Legend `dim_product[category]`, with a constant X-axis reference line at `0.20` (`20%` threshold).
- **Bottom Table:**
  - **Top Loss-Making Products Table:** Columns `product_id`, `product_name`, `category`, `sub_category`, `Total Sales`, `Total Profit`, `Avg Discount %`, `Loss Line Items` (filtered to `[Total Profit] < 0`, sorted ascending).

### Page 3: Customer & RFM Segmentation
- **Top Left (Donut / Stacked Bar Chart):**
  - **Segment Distribution:** `dim_customer[segment]` by `[Total Sales]`, `[Total Profit]`, and `[Profit Margin %]` (`Consumer`, `Corporate`, `Home Office`).
- **Top Right (Clustered Column Chart / Table):**
  - **Shipping Mode Efficiency:** Axis `fact_sales[ship_mode]`, Values `AVERAGE(fact_sales[shipping_duration_days])`, `[Total Orders]`, and `[Total Profit]`.
- **Bottom Left & Right (Leaderboard Table + Scatter):**
  - **Customer Lifetime Value Leaderboard:** Source `vw_customer_performance` (or Star Schema measures), columns `customer_id`, `customer_name`, `segment`, `total_orders_placed`, `lifetime_sales`, `lifetime_profit`, `lifetime_margin_pct`, `recency_days`, sorted descending by `lifetime_sales` / `lifetime_profit`.
  - **RFM Quadrant Scatter:** X-axis `recency_days`, Y-axis `lifetime_sales`, Size `total_orders_placed`, Legend `segment`.
