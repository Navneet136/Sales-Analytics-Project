"""
Phase 10 End-to-End Analytics Pipeline Orchestrator.

Coordinates the full local analytics workflow:
  Step 1: Data Cleaning & Feature Engineering (src/main.py)
  Step 2: Publication Chart Generation (src/generate_charts.py)
  Step 3: Automated Executive Excel Report (src/generate_excel_report.py)
  Step 4: Power BI Offline Data Extracts (src/export_powerbi_views.py)
  Step 5 (Optional): MySQL Star Schema Ingestion (src/load_to_mysql.py)

Usage:
    python src/run_pipeline.py
    python src/run_pipeline.py --no-skip-mysql --mysql-user root
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import export_powerbi_views, generate_charts, generate_excel_report, main as etl_main


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sales_pipeline")


def parse_args() -> argparse.Namespace:
    """Parse pipeline orchestration arguments."""
    parser = argparse.ArgumentParser(
        description="Run the end-to-end Retail Sales Analytics & Reporting pipeline."
    )
    parser.add_argument(
        "--skip-mysql",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip MySQL ingestion step by default (use --no-skip-mysql to run load_to_mysql.py).",
    )
    parser.add_argument(
        "--mysql-user",
        default=os.getenv("MYSQL_USER", "root"),
        help="MySQL username used when --no-skip-mysql is specified (default: root).",
    )
    parser.add_argument(
        "--mysql-host",
        default=os.getenv("MYSQL_HOST", "localhost"),
        help="MySQL host (default: localhost).",
    )
    parser.add_argument(
        "--mysql-port",
        type=int,
        default=int(os.getenv("MYSQL_PORT", 3306)),
        help="MySQL port (default: 3306).",
    )
    parser.add_argument(
        "--mysql-database",
        default=os.getenv("MYSQL_DATABASE", "sales_analytics_db"),
        help="Target MySQL database name (default: sales_analytics_db).",
    )
    return parser.parse_args()


def run_step(step_name: str, fn: Callable[[], None]) -> None:
    """Execute a pipeline step with timing and structured logging."""
    logger.info("START: %s", step_name)
    start = time.perf_counter()
    fn()
    elapsed = time.perf_counter() - start
    logger.info("DONE : %s (%.2fs)", step_name, elapsed)


def run_mysql_step(args: argparse.Namespace) -> None:
    """Invoke src/load_to_mysql.py using the active Python interpreter."""
    script_path = PROJECT_ROOT / "src" / "load_to_mysql.py"
    cmd = [
        sys.executable,
        str(script_path),
        "--host",
        args.mysql_host,
        "--port",
        str(args.mysql_port),
        "--user",
        args.mysql_user,
        "--database",
        args.mysql_database,
    ]
    logger.info("Executing MySQL ingestion: %s", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(PROJECT_ROOT))


def main() -> None:
    """Run all enabled pipeline stages in sequence."""
    args = parse_args()
    pipeline_start = time.perf_counter()
    logger.info("Initializing End-to-End Sales Analytics Pipeline")

    run_step("Step 1/4 - Data Cleaning & Feature Engineering (src/main.py)", etl_main.main)
    run_step("Step 2/4 - Visualization Generation (src/generate_charts.py)", generate_charts.main)
    run_step("Step 3/4 - Automated Executive Excel Report (src/generate_excel_report.py)", generate_excel_report.main)
    run_step("Step 4/4 - Power BI Offline Extracts (src/export_powerbi_views.py)", export_powerbi_views.main)

    if args.skip_mysql:
        logger.info("SKIP : MySQL Ingestion (--skip-mysql is enabled by default)")
    else:
        run_step("Step 5 - MySQL Star Schema Ingestion (src/load_to_mysql.py)", lambda: run_mysql_step(args))

    total_elapsed = time.perf_counter() - pipeline_start
    logger.info("Pipeline completed successfully in %.2fs", total_elapsed)


if __name__ == "__main__":
    main()
