"""
Interactive Retail Sales & Profitability Analytics Dashboard (Streamlit).

Designed for local exploration and public deployment on Streamlit Community Cloud.
Loads data/processed/clean_superstore.parquet (with CSV fallback) and supports
optional user-uploaded CSV files.

Run locally:
    streamlit run app.py
"""

from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
PARQUET_PATH = PROJECT_ROOT / "data" / "processed" / "clean_superstore.parquet"
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "clean_superstore.csv"
EXCEL_REPORT_PATH = PROJECT_ROOT / "reports" / "Executive_Sales_Report.xlsx"

REQUIRED_COLUMNS = {
    "order_id",
    "order_date",
    "region",
    "segment",
    "category",
    "sub_category",
    "product_id",
    "product_name",
    "customer_id",
    "customer_name",
    "sales",
    "quantity",
    "discount",
    "profit",
}


st.set_page_config(
    page_title="Retail Sales & Profitability Analytics Dashboard",
    page_icon="📊",
    layout="wide",
)


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and derive required analytical fields if missing."""
    df = df.copy()
    df.columns = [
        str(col).strip().lower().replace(" ", "_").replace("-", "_")
        for col in df.columns
    ]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Uploaded dataset is missing required columns: {sorted(missing)}")

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df = df.dropna(subset=["order_date"])

    if "order_year" not in df.columns:
        df["order_year"] = df["order_date"].dt.year
    if "profit_margin_pct" not in df.columns:
        df["profit_margin_pct"] = np.where(
            df["sales"] != 0,
            (df["profit"] / df["sales"]) * 100.0,
            0.0,
        )

    for col in ("sales", "profit", "discount", "quantity", "profit_margin_pct"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["order_year"] = df["order_year"].astype(int)
    return df


@st.cache_data
def load_default_data() -> Tuple[pd.DataFrame, str]:
    """Load the repository's processed dataset from Parquet or CSV fallback."""
    if PARQUET_PATH.exists():
        raw = pd.read_parquet(PARQUET_PATH)
        return prepare_dataframe(raw), str(PARQUET_PATH.relative_to(PROJECT_ROOT))
    if CSV_PATH.exists():
        raw = pd.read_csv(CSV_PATH)
        return prepare_dataframe(raw), str(CSV_PATH.relative_to(PROJECT_ROOT))
    raise FileNotFoundError(
        "Could not find data/processed/clean_superstore.parquet or clean_superstore.csv."
    )


def render_sidebar(df: pd.DataFrame) -> Tuple[pd.DataFrame, object]:
    """Render sidebar file uploader and interactive filters."""
    st.sidebar.header("Data & Filters")
    uploaded_file = st.sidebar.file_uploader(
        "Upload custom Sales CSV (optional)",
        type=["csv"],
        help="Upload a Superstore-compatible CSV to test custom data.",
    )

    if uploaded_file is not None:
        try:
            df = prepare_dataframe(pd.read_csv(uploaded_file))
            st.sidebar.success(f"Loaded custom file: {uploaded_file.name}")
        except Exception as exc:
            st.sidebar.error(f"Could not parse uploaded CSV: {exc}")

    regions = sorted(df["region"].dropna().unique().tolist())
    categories = sorted(df["category"].dropna().unique().tolist())
    segments = sorted(df["segment"].dropna().unique().tolist())
    years = sorted(df["order_year"].dropna().unique().tolist())

    sel_regions = st.sidebar.multiselect("Region", options=regions, default=regions)
    sel_categories = st.sidebar.multiselect("Category", options=categories, default=categories)
    sel_segments = st.sidebar.multiselect("Segment", options=segments, default=segments)
    sel_years = st.sidebar.multiselect("Year", options=years, default=years)

    filtered = df[
        df["region"].isin(sel_regions)
        & df["category"].isin(sel_categories)
        & df["segment"].isin(sel_segments)
        & df["order_year"].isin(sel_years)
    ].copy()

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Showing **{len(filtered):,}** of **{len(df):,}** line items")
    return filtered, uploaded_file


def render_kpi_row(df: pd.DataFrame) -> None:
    """Render the 4-metric executive KPI scorecard."""
    total_sales = float(df["sales"].sum())
    total_profit = float(df["profit"].sum())
    overall_margin = (total_profit / total_sales * 100.0) if total_sales else 0.0
    total_orders = int(df["order_id"].nunique())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Sales ($)", f"${total_sales:,.2f}")
    c2.metric("Total Profit ($)", f"${total_profit:,.2f}")
    c3.metric("Overall Profit Margin (%)", f"{overall_margin:.2f}%")
    c4.metric("Total Orders", f"{total_orders:,}")


def render_executive_trends_tab(df: pd.DataFrame) -> None:
    """Tab 1: Monthly Sales & Profit trend line chart and Regional performance."""
    monthly = (
        df.assign(year_month=df["order_date"].dt.to_period("M").dt.to_timestamp())
        .groupby("year_month", as_index=False)[["sales", "profit"]]
        .sum()
        .sort_values("year_month")
    )

    fig_trend = go.Figure()
    fig_trend.add_trace(
        go.Scatter(
            x=monthly["year_month"],
            y=monthly["sales"],
            mode="lines+markers",
            name="Monthly Sales ($)",
            line=dict(color="#1f77b4", width=2.5),
            hovertemplate="%{x|%Y-%m}<br>Sales: $%{y:,.2f}<extra></extra>",
        )
    )
    fig_trend.add_trace(
        go.Scatter(
            x=monthly["year_month"],
            y=monthly["profit"],
            mode="lines+markers",
            name="Monthly Profit ($)",
            line=dict(color="#2ca02c", width=2.5),
            hovertemplate="%{x|%Y-%m}<br>Profit: $%{y:,.2f}<extra></extra>",
        )
    )
    fig_trend.update_layout(
        title="Monthly Revenue & Profit Trend",
        xaxis_title="Order Month",
        yaxis_title="Amount (USD)",
        hovermode="x unified",
        height=420,
    )
    st.plotly_chart(fig_trend, width="stretch")

    regional = (
        df.groupby("region", as_index=False)[["sales", "profit"]]
        .sum()
        .sort_values("sales", ascending=False)
    )
    reg_melt = regional.melt(
        id_vars="region",
        value_vars=["sales", "profit"],
        var_name="Metric",
        value_name="Amount",
    )
    reg_melt["Metric"] = reg_melt["Metric"].map({"sales": "Total Sales", "profit": "Total Profit"})

    fig_region = px.bar(
        reg_melt,
        x="region",
        y="Amount",
        color="Metric",
        barmode="group",
        color_discrete_map={"Total Sales": "#1f77b4", "Total Profit": "#2ca02c"},
        title="Regional Performance: Sales vs. Profit",
        labels={"region": "Region", "Amount": "Amount (USD)"},
        height=400,
    )
    fig_region.update_traces(hovertemplate="%{x}<br>%{fullData.name}: $%{y:,.2f}<extra></extra>")
    st.plotly_chart(fig_region, width="stretch")


def render_margin_leakage_tab(df: pd.DataFrame) -> None:
    """Tab 2: Sub-category profit margins and Discount % vs Profit Margin scatter."""
    col1, col2 = st.columns(2)

    with col1:
        subcat = df.groupby("sub_category", as_index=False)[["sales", "profit"]].sum()
        subcat["profit_margin_pct"] = np.where(
            subcat["sales"] != 0,
            (subcat["profit"] / subcat["sales"]) * 100.0,
            0.0,
        )
        subcat = subcat.sort_values("profit_margin_pct", ascending=True)
        subcat["status"] = np.where(subcat["profit_margin_pct"] < 0, "Loss-Making", "Profitable")

        fig_sub = px.bar(
            subcat,
            x="profit_margin_pct",
            y="sub_category",
            orientation="h",
            color="status",
            color_discrete_map={"Loss-Making": "#d62728", "Profitable": "#2ca02c"},
            title="Sub-Category Profit Margin (%)",
            labels={"profit_margin_pct": "Profit Margin (%)", "sub_category": "Sub-Category"},
            height=520,
        )
        fig_sub.add_vline(x=0, line_dash="solid", line_color="#333333", line_width=1)
        fig_sub.update_traces(hovertemplate="%{y}: %{x:.2f}%<extra></extra>")
        st.plotly_chart(fig_sub, width="stretch")

    with col2:
        scatter_df = df.assign(discount_pct=df["discount"] * 100.0)
        fig_scatter = px.scatter(
            scatter_df,
            x="discount_pct",
            y="profit_margin_pct",
            color="category",
            opacity=0.45,
            title="Discount Rate (%) vs. Profit Margin (%) — 20% Profitability Threshold",
            labels={
                "discount_pct": "Discount Rate (%)",
                "profit_margin_pct": "Profit Margin (%)",
                "category": "Category",
            },
            hover_data=["sub_category", "sales", "profit"],
            height=520,
        )

        if len(scatter_df) >= 2 and scatter_df["discount_pct"].nunique() > 1:
            slope, intercept = np.polyfit(scatter_df["discount_pct"], scatter_df["profit_margin_pct"], 1)
            x_line = np.linspace(scatter_df["discount_pct"].min(), scatter_df["discount_pct"].max(), 50)
            fig_scatter.add_trace(
                go.Scatter(
                    x=x_line,
                    y=slope * x_line + intercept,
                    mode="lines",
                    name="Linear Trendline",
                    line=dict(color="#111111", width=2.5),
                )
            )

        fig_scatter.add_hline(y=0, line_dash="dash", line_color="#444444")
        fig_scatter.add_vline(
            x=20,
            line_dash="dot",
            line_color="#d62728",
            annotation_text="20% Threshold",
            annotation_position="top right",
        )
        st.plotly_chart(fig_scatter, width="stretch")


def render_leaderboard_tab(df: pd.DataFrame) -> None:
    """Tab 3: Top 10 Products by Profit, Top 10 Customers by Revenue, and Downloads."""
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top 10 Most Profitable Products")
        top_products = (
            df.groupby(["product_id", "product_name", "category", "sub_category"], as_index=False)
            .agg(units_sold=("quantity", "sum"), sales=("sales", "sum"), profit=("profit", "sum"))
            .assign(margin_pct=lambda d: np.where(d["sales"] != 0, d["profit"] / d["sales"] * 100.0, 0.0))
            .sort_values("profit", ascending=False)
            .head(10)
        )
        st.dataframe(
            top_products.style.format({"units_sold": "{:,}", "sales": "${:,.2f}", "profit": "${:,.2f}", "margin_pct": "{:.2f}%"}),
            width="stretch",
            hide_index=True,
        )

    with col2:
        st.subheader("Top 10 Customers by Revenue")
        top_customers = (
            df.groupby(["customer_id", "customer_name", "segment"], as_index=False)
            .agg(orders=("order_id", "nunique"), sales=("sales", "sum"), profit=("profit", "sum"))
            .assign(margin_pct=lambda d: np.where(d["sales"] != 0, d["profit"] / d["sales"] * 100.0, 0.0))
            .sort_values("sales", ascending=False)
            .head(10)
        )
        st.dataframe(
            top_customers.style.format({"orders": "{:,}", "sales": "${:,.2f}", "profit": "${:,.2f}", "margin_pct": "{:.2f}%"}),
            width="stretch",
            hide_index=True,
        )

    st.markdown("---")
    st.subheader("Export Reports & Filtered Data")
    dl1, dl2 = st.columns(2)

    with dl1:
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Filtered Dataset (CSV)",
            data=csv_bytes,
            file_name="filtered_superstore_sales.csv",
            mime="text/csv",
        )

    with dl2:
        if EXCEL_REPORT_PATH.exists():
            st.download_button(
                label="Download Executive Sales Report (Excel)",
                data=EXCEL_REPORT_PATH.read_bytes(),
                file_name="Executive_Sales_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("Executive_Sales_Report.xlsx not found. Run `python src/generate_excel_report.py` to generate it.")


def main() -> None:
    """Application entrypoint."""
    st.title("📊 Retail Sales & Profitability Analytics Dashboard")
    st.caption("Interactive US Superstore Business Intelligence Explorer (2014–2017)")

    base_df, source_label = load_default_data()
    filtered_df, uploaded_file = render_sidebar(base_df)
    if uploaded_file is None:
        st.sidebar.caption(f"Source: `{source_label}`")

    if filtered_df.empty:
        st.warning("No records match the current sidebar filter selection. Adjust filters to view results.")
        st.stop()

    render_kpi_row(filtered_df)
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs([
        "Executive Trends",
        "Margin & Discount Leakage",
        "Customer & Product Leaderboard",
    ])
    with tab1:
        render_executive_trends_tab(filtered_df)
    with tab2:
        render_margin_leakage_tab(filtered_df)
    with tab3:
        render_leaderboard_tab(filtered_df)


if __name__ == "__main__":
    main()
