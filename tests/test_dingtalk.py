from datetime import datetime, timezone
from pathlib import Path

from wff_order_tracker.config import Settings
from wff_order_tracker.dingtalk import _build_markdown, send_dingtalk_report
from wff_order_tracker.models import ExceptionRecord, RiskLevel


def _record():
    return ExceptionRecord(
        exception_type="派送失败",
        risk_level=RiskLevel.HIGH,
        order_number="WFF-1",
        customer_name="客户A",
        account_manager="经理A",
        tracking_number="TRACK-1",
        carrier="Carrier",
        logistics_template="US 7-10",
        promised_delivery_days=10,
        transit_days=6,
        days_since_last_update=1,
        last_event_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        last_event_description="address incorrect",
        destination_country="US",
        suggested_action="通知 AM 协调客户补充地址",
    )


def test_dingtalk_markdown_summarizes_manager_and_exception():
    markdown = _build_markdown(Path("reports/demo.xlsx"), [_record()], ["13800000000"])

    assert "异常订单总数" in markdown
    assert "经理A: 1 单" in markdown
    assert "派送失败: 1 单" in markdown
    assert "@13800000000" in markdown


def test_dingtalk_dry_run_without_webhook(capsys):
    settings = Settings(dry_run=True, dingtalk_at_mobiles="13800000000")

    send_dingtalk_report(settings, Path("reports/demo.xlsx"), [_record()])

    assert "[DRY-RUN] Would notify DingTalk" in capsys.readouterr().out
