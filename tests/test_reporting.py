from datetime import datetime, timezone
from zipfile import ZipFile

from wff_order_tracker.models import ExceptionRecord, RiskLevel
from wff_order_tracker.reporting import generate_excel_report


def test_generate_excel_report_splits_summary_manager_and_customer(tmp_path):
    record = ExceptionRecord(
        exception_type="物流超过阈值未更新",
        risk_level=RiskLevel.MEDIUM,
        order_number="WFF-1",
        customer_name="客户A",
        account_manager="经理A",
        tracking_number="TRACK-1",
        carrier="Carrier",
        logistics_template="US 7-10",
        promised_delivery_days=10,
        transit_days=6,
        days_since_last_update=5,
        last_event_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        last_event_description="old event",
        destination_country="US",
        suggested_action="催促物流商更新轨迹",
    )

    path = generate_excel_report([record], tmp_path, generated_at=datetime(2026, 5, 13, 9, 0, 0))

    assert path.exists()
    with ZipFile(path) as workbook:
        workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
        summary_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "异常汇总" in workbook_xml
    assert "经理-经理A" in workbook_xml
    assert "客户-客户A" in workbook_xml
    assert "物流超过阈值未更新" in summary_xml
