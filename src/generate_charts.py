"""
Phase 6 Automated Visualization & Reporting Script.

Generates publication-ready analytical charts from the processed Superstore
dataset (data/processed/clean_superstore.parquet with CSV fallback) and
saves 300 DPI PNG exports to reports/figures/.

Usage:
    python src/generate_charts.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd
import seaborn as sns


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARQUET_PATH = PROJECT_ROOT / "data" / "processed" / "clean_superstore.parquet"
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "clean_superstore.csv"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"


def load_data() -> pd.DataFrame:
    """Load processed Superstore dataset from Parquet, falling back to CSV."""
    if PARQUET_PATH.exists():
        df = pd.read_parquet(PARQUET_PATH)
    elif CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH)
    else:
        raise FileNotFoundError(
            f"Processed dataset not found at {PARQUET_PATH} or {CSV_PATH}."
        )
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


def currency_k_formatter(x: float, _pos: int) -> str:
    """Format dollar values in thousands ($K) for clean axis ticks."""
    return f"${x / 1_000:,.0f}K"


def plot_monthly_sales_trend(df: pd.DataFrame, output_path: Path) -> None:
    """Save line chart of monthly revenue and profit trends over time."""
    monthly = (
        df.assign(year_month=df["order_date"].dt.to_period("M").dt.to_timestamp())
        .groupby("year_month", as_index=False)[["sales", "profit"]]
        .sum()
        .sort_values("year_month")
    )

    fig, ax = plt.subplots(figsize=(13, 6))
    sns.lineplot(
        data=monthly,
        x="year_month",
        y="sales",
        ax=ax,
        marker="o",
        linewidth=2.2,
        color="#1f77b4",
        label="Monthly Revenue (Sales)",
    )
    sns.lineplot(
        data=monthly,
        x="year_month",
        y="profit",
        ax=ax,
        marker="s",
        linewidth=2.2,
        color="#2ca02c",
        label="Monthly Profit",
    )

    ax.axhline(0, color="#555555", linestyle="--", linewidth=0.9, alpha=0.7)
    ax.set_title("Monthly Revenue & Profit Trend (2014–2017)", fontsize=14, fontweight="bold", pad=14)
    ax.set_xlabel("Order Month", fontsize=11)
    ax.set_ylabel("Amount (USD)", fontsize=11)
    ax.yaxis.set_major_formatter(FuncFormatter(currency_k_formatter))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.xticks(rotation=45, ha="right")
    ax.legend(frameon=True, loc="upper left")
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_category_subcat_margins(df: pd.DataFrame, output_path: Path) -> None:
    """Save horizontal bar chart of profit margin % across all 17 sub-categories."""
    subcat = (
        df.groupby("sub_category", as_index=False)[["sales", "profit"]]
        .sum()
    )
    subcat["profit_margin_pct"] = (subcat["profit"] / subcat["sales"]) * 100.0
    subcat = subcat.sort_values("profit_margin_pct", ascending=True).reset_index(drop=True)
    colors = ["#d62728" if m < 0 else "#2ca02c" for m in subcat["profit_margin_pct"]]

    fig, ax = plt.subplots(figsize=(11, 7.5))
    bars = ax.barh(
        subcat["sub_category"],
        subcat["profit_margin_pct"],
        color=colors,
        edgecolor="#222222",
        linewidth=0.5,
        alpha=0.9,
    )
    ax.axvline(0, color="#222222", linewidth=1.0)

    for bar, margin in zip(bars, subcat["profit_margin_pct"]):
        offset = 0.8 if margin >= 0 else -0.8
        ha = "left" if margin >= 0 else "right"
        ax.text(
            margin + offset,
            bar.get_y() + bar.get_height() / 2,
            f"{margin:.1f}%",
            va="center",
            ha=ha,
            fontsize=9,
            fontweight="semibold",
            color="#222222",
        )

    xmin, xmax = subcat["profit_margin_pct"].min(), subcat["profit_margin_pct"].max()
    ax.set_xlim(xmin - 7, xmax + 7)
    ax.set_title("Profit Margin (%) Across All 17 Sub-Categories", fontsize=14, fontweight="bold", pad=14)
    ax.set_xlabel("Profit Margin (%)", fontsize=11)
    ax.set_ylabel("Sub-Category", fontsize=11)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_discount_vs_profit_scatter(df: pd.DataFrame, output_path: Path) -> None:
    """Save scatter plot with regression trendline showing discount impact on margin %."""
    plot_df = df.assign(discount_pct=df["discount"] * 100.0)

    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    sns.regplot(
        data=plot_df,
        x="discount_pct",
        y="profit_margin_pct",
        ax=ax,
        scatter_kws={"alpha": 0.25, "s": 24, "color": "#1f77b4", "edgecolors": "none"},
        line_kws={"color": "#d62728", "linewidth": 2.4, "label": "Linear Trendline"},
    )
    ax.axhline(0, color="#333333", linestyle="--", linewidth=1.0, alpha=0.8)
    ax.set_title("Discount Rate (%) vs. Profit Margin (%)", fontsize=14, fontweight="bold", pad=14)
    ax.set_xlabel("Discount Rate (%)", fontsize=11)
    ax.set_ylabel("Profit Margin (%)", fontsize=11)
    ax.legend(frameon=True, loc="upper right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_regional_performance(df: pd.DataFrame, output_path: Path) -> None:
    """Save grouped bar chart comparing total Sales vs Profit across all 4 regions."""
    regional = (
        df.groupby("region", as_index=False)[["sales", "profit"]]
        .sum()
        .sort_values("sales", ascending=False)
    )
    melted = regional.melt(
        id_vars="region",
        value_vars=["sales", "profit"],
        var_name="Metric",
        value_name="Amount",
    )
    melted["Metric"] = melted["Metric"].map({"sales": "Total Sales", "profit": "Total Profit"})

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(
        data=melted,
        x="region",
        y="Amount",
        hue="Metric",
        ax=ax,
        palette={"Total Sales": "#1f77b4", "Total Profit": "#2ca02c"},
    )

    for container in ax.containers:
        ax.bar_label(
            container,
            labels=[f"${v / 1_000:,.1f}K" for v in container.datavalues],
            padding=3,
            fontsize=9,
            fontweight="semibold",
        )

    ax.set_title("Regional Sales vs. Profit Comparison", fontsize=14, fontweight="bold", pad=14)
    ax.set_xlabel("Region", fontsize=11)
    ax.set_ylabel("Amount (USD)", fontsize=11)
    ax.yaxis.set_major_formatter(FuncFormatter(currency_k_formatter))
    ax.set_ylim(0, regional["sales"].max() * 1.14)
    ax.legend(title="Metric", frameon=True, loc="upper right")
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    """Generate all Phase 6 analytical charts."""
    sns.set_theme(style="whitegrid")
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()

    charts = [
        ("01_monthly_sales_trend.png", plot_monthly_sales_trend),
        ("02_category_subcat_margins.png", plot_category_subcat_margins),
        ("03_discount_vs_profit_scatter.png", plot_discount_vs_profit_scatter),
        ("04_regional_performance.png", plot_regional_performance),
    ]

    for filename, plot_fn in charts:
        out_path = FIGURES_DIR / filename
        plot_fn(df, out_path)
        print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
