from datetime import datetime, timedelta, timezone

from wff_order_tracker.analyzer import analyze_orders
from wff_order_tracker.models import Order, TrackingEvent, TrackingStatus


def _order(**overrides):
    data = {
        "order_number": "WFF-1",
        "customer_name": "客户A",
        "account_manager": "经理A",
        "tracking_number": "TRACK-1",
        "carrier": "Carrier",
        "logistics_template": "US 7-10",
        "promised_delivery_days": 10,
        "shipped_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
        "destination_country": "US",
    }
    data.update(overrides)
    return Order(**data)


def test_order_over_promised_days_is_high_risk():
    now = datetime(2026, 5, 13, tzinfo=timezone.utc)
    event = TrackingEvent("TRACK-1", TrackingStatus.IN_TRANSIT, now - timedelta(days=1), "in transit")

    records = analyze_orders([_order()], {"TRACK-1": event}, now=now)

    assert len(records) == 1
    assert records[0].exception_type == "已超承诺时效未签收"
    assert records[0].risk_level.value == "高"


def test_stale_tracking_is_reported_before_promise_deadline():
    now = datetime(2026, 5, 6, tzinfo=timezone.utc)
    event = TrackingEvent("TRACK-1", TrackingStatus.IN_TRANSIT, now - timedelta(days=5), "old event")

    records = analyze_orders([_order(promised_delivery_days=15)], {"TRACK-1": event}, now=now)

    assert len(records) == 1
    assert records[0].exception_type == "物流超过阈值未更新"
    assert records[0].days_since_last_update == 5


def test_delivered_order_is_skipped():
    now = datetime(2026, 5, 6, tzinfo=timezone.utc)
    event = TrackingEvent("TRACK-1", TrackingStatus.DELIVERED, now, "delivered")

    records = analyze_orders([_order()], {"TRACK-1": event}, now=now)

    assert records == []


def test_super_delay_is_reported_after_extra_delay_threshold():
    now = datetime(2026, 5, 20, tzinfo=timezone.utc)
    event = TrackingEvent("TRACK-1", TrackingStatus.IN_TRANSIT, now - timedelta(days=1), "in transit")

    records = analyze_orders([_order()], {"TRACK-1": event}, now=now)

    assert len(records) == 1
    assert records[0].exception_type == "超长延误"


def test_delivery_failed_is_high_risk():
    now = datetime(2026, 5, 6, tzinfo=timezone.utc)
    event = TrackingEvent("TRACK-1", TrackingStatus.DELIVERY_FAILED, now, "address incorrect")

    records = analyze_orders([_order(promised_delivery_days=15)], {"TRACK-1": event}, now=now)

    assert len(records) == 1
    assert records[0].exception_type == "派送失败"
    assert records[0].risk_level.value == "高"


def test_waiting_pickup_timeout_is_reported():
    now = datetime(2026, 5, 6, tzinfo=timezone.utc)
    event = TrackingEvent("TRACK-1", TrackingStatus.WAITING_PICKUP, now - timedelta(days=2), "waiting pickup")

    records = analyze_orders([_order(promised_delivery_days=15)], {"TRACK-1": event}, now=now)

    assert len(records) == 1
    assert records[0].exception_type == "等待取件超时"
