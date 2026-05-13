"""Command line entry point for the Wefulfil order tracking MVP."""

from __future__ import annotations

import argparse
from pathlib import Path

from .analyzer import analyze_orders
from .config import Settings, load_rules
from .mailer import send_report
from .reporting import generate_excel_report
from .tracking import build_tracking_client
from .wefulfil_client import WefulfilClient


def main() -> None:
    """Run the daily order exception workflow."""

    parser = argparse.ArgumentParser(description="Generate Wefulfil fulfillment exception reports.")
    parser.add_argument("--rules", type=Path, default=Path("config/rules.yaml"), help="Path to exception rule YAML file.")
    parser.add_argument("--no-email", action="store_true", help="Generate report without attempting to send email.")
    args = parser.parse_args()

    settings = Settings.load()
    rules = load_rules(args.rules) if args.rules.exists() else {}

    wefulfil = WefulfilClient(settings.wefulfil_base_url, settings.wefulfil_api_key)
    orders = wefulfil.fetch_orders()
    tracking_numbers = [order.tracking_number for order in orders if order.tracking_number]

    tracker = build_tracking_client(settings.tracking_provider, settings.tracking_api_key)
    tracking_events = tracker.get_latest_events(tracking_numbers)

    records = analyze_orders(orders, tracking_events, rules)
    report_path = generate_excel_report(records, settings.report_output_dir)

    print(f"Fetched orders: {len(orders)}")
    print(f"Exception records: {len(records)}")
    print(f"Report generated: {report_path}")

    if not args.no_email:
        send_report(
            settings,
            report_path,
            subject="Wefulfil 履约异常订单清查报告",
            body="请查看附件中的延误风险与物流异常订单，并按客户经理/客户拆分跟进。",
        )


if __name__ == "__main__":
    main()
