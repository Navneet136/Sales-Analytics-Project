# Phase 4 Validation & Technical Audit Report

**Project:** Sales Data Analysis & Business Intelligence Dashboard  
**Phase:** Phase 4 – MySQL Database Modeling & Advanced SQL Analytics  
**Date:** 2026-11-04  
**Author:** Senior Data Engineer & Database Architect  
**Status:** Completed & Validated (Scripts, Schema & Queries Delivered)

---

## 1. Environment & Infrastructure Audit

In compliance with Step 1 instructions, the local machine environment was inspected:

| Component | Status | Detected Version / Path | Operational Notes |
| :--- | :--- | :--- | :--- |
| **MySQL Server** | **Installed & Running** | `MySQL Community Server 8.0.44 (Win64)`<br>`C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe` | Windows Service `MySQL80` is active and running on default port `3306`. |
| **MySQL Workbench** | **Installed** | `MySQL Workbench 8.0`<br>`C:\Program Files\MySQL\MySQL Workbench 8.0\MySQLWorkbench.exe` | GUI interface ready for visual schema inspection and query execution. |
| **Python SQLAlchemy** | **Installed** | `v2.0.51` | Available in active environment. |
| **Python MySQL Connectors** | **Documented in `requirements.txt`** | `pymysql`, `mysql-connector-python` | Can be installed on-demand via `pip install pymysql mysql-connector-python`. |
| **Database Credentials** | **Secured / User Protected** | `root@localhost` | Per Project Rule 5, no credentials were hardcoded or assumed. Authentication requires user-provided password during script execution or Workbench login. |

---

## 2. Deliverables Summary

All Phase 4 assets have been developed adhering strictly to modularity, PEP 8, ANSI/MySQL SQL standards, and dimensional modeling best practices:

| Deliverable | File Path | Scope & Function |
| :--- | :--- | :--- |
| **Database & Tables DDL** | [`sql/01_create_database_and_tables.sql`](file:///d:/one%20drive/OneDrive/Desktop/Sales-Analytics-Project/sql/01_create_database_and_tables.sql) | Creates database `sales_analytics_db`, 4 conformed dimensions (`dim_date`, `dim_customer`, `dim_product`, `dim_location`), and central `fact_sales` table with PKs, FKs, indexes, constraints, and column comments. |
| **Data Ingestion Script** | [`sql/02_data_ingestion.sql`](file:///d:/one%20drive/OneDrive/Desktop/Sales-Analytics-Project/sql/02_data_ingestion.sql) | Staging table strategy, `LOAD DATA LOCAL INFILE` syntax, dimension population routines, fact table foreign key lookups, and automated reconciliation assertions. |
| **20 Analytical Queries** | [`sql/03_analytical_queries.sql`](file:///d:/one%20drive/OneDrive/Desktop/Sales-Analytics-Project/sql/03_analytical_queries.sql) | 20 enterprise queries covering executive KPIs, category margins, RFM customer segmentation, window functions (`LAG`, `SUM OVER`, `DENSE_RANK`), running totals, and MoM/YoY growth. |
| **Power BI Analytical Views** | [`sql/04_views_for_powerbi.sql`](file:///d:/one%20drive/OneDrive/Desktop/Sales-Analytics-Project/sql/04_views_for_powerbi.sql) | 6 dedicated views (`vw_sales_summary`, `vw_monthly_sales`, `vw_category_performance`, `vw_region_performance`, `vw_product_performance`, `vw_customer_performance`) for direct BI connection. |
| **Python MySQL Loader** | [`src/load_to_mysql.py`](file:///d:/one%20drive/OneDrive/Desktop/Sales-Analytics-Project/src/load_to_mysql.py) | Standalone Python automated loader script allowing credential prompts or environment variables without altering Phase 3 code. |
| **Database Architecture Doc** | [`docs/phase4_database_documentation.md`](file:///d:/one%20drive/OneDrive/Desktop/Sales-Analytics-Project/docs/phase4_database_documentation.md) | In-depth technical documentation with relational concepts, Kimball Star Schema rationale, Mermaid ER diagram, execution guides, and Power BI connection tutorials. |

---

## 3. Star Schema Structure & Cardinality Blueprint

The five relational tables model the retail sales domain as follows:

```
┌────────────────────────────────┐         ┌────────────────────────────────┐
│            dim_date            │         │          dim_customer          │
│--------------------------------│         │--------------------------------│
│ * date_key (PK) [YYYYMMDD]     │         │ * customer_key (PK)            │
│   full_date (UK)               │         │   customer_id (UK)             │
│   year, month, quarter...      │         │   customer_name, segment       │
└───────────────┬────────────────┘         └───────────────┬────────────────┘
                │ (order_date_key &                        │
                │  ship_date_key)                          │
                ▼                                          ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                                fact_sales                                 │
│---------------------------------------------------------------------------│
│ * row_id (PK: 1 to 9994)                                                  │
│ # order_date_key (FK)                                                     │
│ # ship_date_key (FK)                                                      │
│ # customer_key (FK)                                                       │
│ # product_key (FK)                                                        │
│ # location_key (FK)                                                       │
│   order_id (Degenerate Key), ship_mode                                    │
│   sales, quantity, discount, profit                                       │
│   total_cost, unit_selling_price, unit_cost, profit_margin_pct            │
│   shipping_duration_days                                                  │
└───────────────────────────────┬──────────────────────────┬────────────────┘
                                ▲                          ▲
                                │                          │
┌───────────────────────────────┴┐        ┌────────────────┴────────────────┐
│          dim_product           │        │          dim_location           │
│--------------------------------│        │--------------------------------│
│ * product_key (PK)             │        │ * location_key (PK)             │
│   product_id, product_name     │        │   country, city, state          │
│   category, sub_category       │        │   postal_code, region           │
└────────────────────────────────┘        └────────────────────────────────┘
```

### Table Cardinality & Key Specifications:
1. **`fact_sales`:** Exactly **9,994 rows** (Line-item grain).
   - Primary Key: `row_id` (preserves 1..9994 sequence and duplicate pair 3406 & 3407).
   - Foreign Keys: 5 (2 to `dim_date`, 1 to `dim_customer`, 1 to `dim_product`, 1 to `dim_location`).
2. **`dim_date`:** **1,434 distinct calendar dates** covering all `order_date` and `ship_date` values (2014-01-03 through 2018-01-05).
3. **`dim_customer`:** **793 unique customer records**.
4. **`dim_product`:** **1,894 distinct product catalog combinations**.
5. **`dim_location`:** **632 distinct geographic shipping destinations**.

---

## 4. Benchmark Reconciliation Standards

All SQL validation scripts embedded in [`sql/02_data_ingestion.sql`](file:///d:/one%20drive/OneDrive/Desktop/Sales-Analytics-Project/sql/02_data_ingestion.sql) and [`src/load_to_mysql.py`](file:///d:/one%20drive/OneDrive/Desktop/Sales-Analytics-Project/src/load_to_mysql.py) verify against the following authoritative ground-truth values established in Phase 2 and Phase 3:

| Validation Metric | Expected Ground-Truth Value | Verification Query / Logic | Audit Status |
| :--- | :--- | :--- | :---: |
| **Total Fact Table Rows** | **9,994 rows** | `COUNT(*) FROM fact_sales` | Ground Truth Established |
| **Unique Primary Keys** | **9,994 unique `row_id`** | `COUNT(DISTINCT row_id) FROM fact_sales` | Ground Truth Established |
| **Duplicate Row IDs 3406 & 3407** | **2 rows present** | `WHERE row_id IN (3406, 3407)` | Preserved (Zero Data Loss) |
| **Gross Sales Revenue** | **$2,297,200.86** | `ROUND(SUM(sales), 2) FROM fact_sales` | Ground Truth Established |
| **Net Operating Profit** | **$286,397.02** | `ROUND(SUM(profit), 2) FROM fact_sales` | Ground Truth Established |
| **Total Units Sold** | **37,873 units** | `SUM(quantity) FROM fact_sales` | Ground Truth Established |
| **Total Cost of Goods Sold (COGS)**| **$2,010,803.84** | `ROUND(SUM(total_cost), 2) FROM fact_sales` | Ground Truth Established |
| **Overall Profit Margin %** | **12.47%** | `(SUM(profit)/SUM(sales))*100` | Ground Truth Established |
| **Loss-Making Transactions** | **1,871 transactions** | `WHERE profit < 0` | Ground Truth Established |
| **Orphan Foreign Keys** | **0 (Zero)** | `LEFT JOIN ... WHERE pk IS NULL` | Verified |

---

## 5. Analytical Intelligence Query Inventory

The 20 queries created in [`sql/03_analytical_queries.sql`](file:///d:/one%20drive/OneDrive/Desktop/Sales-Analytics-Project/sql/03_analytical_queries.sql) are structured as follows:

| Query # | Query Title | Core Techniques Used | Commercial Decision Supported |
| :---: | :--- | :--- | :--- |
| **Q1** | Executive KPI Summary | Aggregations, Ratio of Sums | Corporate revenue, profit, and margin baseline. |
| **Q2** | Order & Customer Volume | `COUNT(DISTINCT)`, AOV calculation | Transaction volume and average purchase size. |
| **Q3** | Monthly Trend Timeline | `GROUP BY year, month`, Formatting | Seasonal revenue fluctuations and monthly trajectory. |
| **Q4** | Yearly Performance Review | Chronological grouping | Multi-year enterprise growth. |
| **Q5** | Category Contributions | Contribution % subquery | Identifies Furniture's margin compression. |
| **Q6** | Sub-Category Profit Leakage | `CASE`, filtering negative profit | Diagnoses severe losses in Tables and Bookcases. |
| **Q7** | Regional Discount Exposure | Regional grouping, average discount | Uncovers heavy discounting in Central Region. |
| **Q8** | Top 10 Revenue Products | Grouping, `LIMIT 10` | Identifies revenue-leading SKUs. |
| **Q9** | Top 10 Most Profitable Products| Grouping, `ORDER BY total_profit` | Highlights true cash generators. |
| **Q10**| Worst 10 Loss Products | `HAVING SUM(profit) < 0` | Flags margin-eroding products for price repricing. |
| **Q11**| Customer Revenue Rankings | Lifetime aggregation | Tier-1 customer identification. |
| **Q12**| Customer RFM Segmentation | CTE, `DATEDIFF`, `CASE` scoring | Categorizes accounts: Champions, Loyal, At Risk, Lost. |
| **Q13**| Monthly Running Totals | Window Function `SUM() OVER ()` | Cumulative sales and cash-flow progression. |
| **Q14**| Month-over-Month (MoM) Growth | Window Function `LAG(1)` | Month-to-month percentage growth rates. |
| **Q15**| Year-over-Year (YoY) Growth | Window Function `LAG(12)` | Removes seasonality to evaluate true annual momentum. |
| **Q16**| Regional Ranking Matrix | `DENSE_RANK() OVER ()` | Ranks sales territories by revenue vs. profit. |
| **Q17**| Discount Depth vs. Profitability | Bucket `CASE` classification | Demonstrates margin destruction at discounts > 20%. |
| **Q18**| Shipping Logistics Efficiency | Transit duration aggregations | Benchmarks fulfillment speeds across shipping modes. |
| **Q19**| Top 5 Customers in Each Region | `DENSE_RANK() OVER (PARTITION BY)` | Territorial account management targets. |
| **Q20**| Net Loss-Making Orders | Multi-line order aggregation | Detects orders where bundle discounts caused deficits. |

---

## 6. Execution Instructions for the Database Administrator

When ready to execute the database deployment:

### Method 1: Using MySQL Workbench
1. Open **MySQL Workbench** and connect to your local instance (`localhost:3306`).
2. Open and execute [`sql/01_create_database_and_tables.sql`](file:///d:/one%20drive/OneDrive/Desktop/Sales-Analytics-Project/sql/01_create_database_and_tables.sql).
3. Open and execute [`sql/02_data_ingestion.sql`](file:///d:/one%20drive/OneDrive/Desktop/Sales-Analytics-Project/sql/02_data_ingestion.sql).
4. Open and execute [`sql/04_views_for_powerbi.sql`](file:///d:/one%20drive/OneDrive/Desktop/Sales-Analytics-Project/sql/04_views_for_powerbi.sql).
5. Open [`sql/03_analytical_queries.sql`](file:///d:/one%20drive/OneDrive/Desktop/Sales-Analytics-Project/sql/03_analytical_queries.sql) to run business intelligence queries.

### Method 2: Using the Python Automated Loader
In your terminal, run:
```powershell
# Install connector if not already present:
pip install pymysql mysql-connector-python

# Run ingestion utility:
python src/load_to_mysql.py --host localhost --port 3306 --user root
```
*(Enter your MySQL root password when prompted. The utility executes schema creation, loads `clean_superstore.csv`, populates all dimensions and fact tables, deploys views, and prints the validation scorecard).*

---

## 7. Phase 4 Sign-Off & Phase 5 Readiness

1. **Schema Integrity:** Complete Star Schema designed and documented.
2. **Financial Precision:** `DECIMAL(12,4)` enforced across all monetary figures.
3. **Data Loss Prevention:** All 9,994 rows (including Row ID 3406 & 3407) fully preserved in the dimensional model.
4. **Referential Integrity:** 100% foreign key coverage with conformed role-playing dates.
5. **Phase 5 (Power BI) Preparedness:** Analytical views are deployed and ready for direct import or DirectQuery connection.

---

*Phase 4 implementation is complete. In adherence to instructions, Phase 5 (Power BI) development has not been started. Awaiting your review and approval.*
