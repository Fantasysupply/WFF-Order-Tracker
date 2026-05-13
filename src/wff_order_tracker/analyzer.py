"""Rules engine for fulfillment delay and tracking exception detection."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import ExceptionRecord, Order, RiskLevel, TrackingEvent, TrackingStatus


DEFAULT_RULES: dict[str, Any] = {
    "stale_tracking_days": 5,
    "delay_warning_buffer_days": 2,
    "customs_stale_days": 3,
    "delivery_stale_days": 2,
    "waiting_pickup_stale_days": 2,
    "super_delay_days_after_promise": 7,
}


def analyze_orders(
    orders: list[Order],
    tracking_events: dict[str, TrackingEvent],
    rules: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> list[ExceptionRecord]:
    """Return exception records that should be reviewed by fulfillment teams."""

    active_rules = {**DEFAULT_RULES, **(rules or {})}
    current_time = now or datetime.now(timezone.utc)
    records: list[ExceptionRecord] = []

    for order in orders:
        if not order.tracking_number:
            records.append(_build_record(order, None, current_time, "缺少物流单号", RiskLevel.HIGH, "补充物流单号并确认是否已发货"))
            continue

        event = tracking_events.get(order.tracking_number)
        if event and event.status == TrackingStatus.DELIVERED:
            continue

        transit_days = max(0, (current_time - _ensure_aware(order.shipped_at)).days)
        days_since_update = _days_since_update(event, current_time)

        if event and event.status == TrackingStatus.EXCEPTION:
            records.append(_build_record(order, event, current_time, "物流平台标记异常", RiskLevel.HIGH, "立即联系物流商处理异常节点"))
            continue

        if event and event.status == TrackingStatus.DELIVERY_FAILED:
            records.append(_build_record(order, event, current_time, "派送失败", RiskLevel.HIGH, "联系尾程物流确认失败原因，通知AM协调客户补充地址/电话或安排重派"))
            continue

        if event and event.status in {TrackingStatus.RETURNING, TrackingStatus.RETURNED}:
            records.append(_build_record(order, event, current_time, "退件/退回风险", RiskLevel.HIGH, "确认退件原因与拦截可能性，通知AM同步客户处理方案"))
            continue

        if event and event.status == TrackingStatus.WAITING_PICKUP and days_since_update is not None:
            if days_since_update >= int(active_rules["waiting_pickup_stale_days"]):
                records.append(_build_record(order, event, current_time, "等待取件超时", RiskLevel.MEDIUM, "提醒AM通知客户尽快取件，必要时联系尾程确认保管期限"))
                continue

        super_delay_threshold = order.promised_delivery_days + int(active_rules["super_delay_days_after_promise"])
        if transit_days > super_delay_threshold:
            records.append(
                _build_record(
                    order,
                    event,
                    current_time,
                    "超长延误",
                    RiskLevel.HIGH,
                    "升级物流商核查是否丢件/卡关/退回，并由履约负责人推动专项处理",
                )
            )
            continue

        if transit_days > order.promised_delivery_days:
            records.append(
                _build_record(
                    order,
                    event,
                    current_time,
                    "已超承诺时效未签收",
                    RiskLevel.HIGH,
                    "联系物流商核查延误原因，并同步客户经理跟进客户预期",
                )
            )
            continue

        warning_threshold = max(0, order.promised_delivery_days - int(active_rules["delay_warning_buffer_days"]))
        if transit_days >= warning_threshold:
            records.append(
                _build_record(
                    order,
                    event,
                    current_time,
                    "临近承诺时效风险",
                    RiskLevel.MEDIUM,
                    "优先确认目的国节点和预计派送时间",
                )
            )
            continue

        if days_since_update is not None and days_since_update >= int(active_rules["stale_tracking_days"]):
            records.append(
                _build_record(
                    order,
                    event,
                    current_time,
                    "物流超过阈值未更新",
                    RiskLevel.MEDIUM,
                    "催促物流商更新轨迹，排查是否丢件或卡仓",
                )
            )
            continue

        if event and event.status == TrackingStatus.CUSTOMS and days_since_update is not None:
            if days_since_update >= int(active_rules["customs_stale_days"]):
                records.append(
                    _build_record(order, event, current_time, "清关节点停留过久", RiskLevel.MEDIUM, "核查清关资料与税费状态")
                )
                continue

        if event and event.status == TrackingStatus.OUT_FOR_DELIVERY and days_since_update is not None:
            if days_since_update >= int(active_rules["delivery_stale_days"]):
                records.append(
                    _build_record(order, event, current_time, "派送节点停留过久", RiskLevel.MEDIUM, "联系尾程物流确认派送失败原因")
                )
                continue

    return records


def _build_record(
    order: Order,
    event: TrackingEvent | None,
    now: datetime,
    exception_type: str,
    risk_level: RiskLevel,
    suggested_action: str,
) -> ExceptionRecord:
    transit_days = max(0, (now - _ensure_aware(order.shipped_at)).days)
    return ExceptionRecord(
        exception_type=exception_type,
        risk_level=risk_level,
        order_number=order.order_number,
        customer_name=order.customer_name,
        account_manager=order.account_manager,
        tracking_number=order.tracking_number,
        carrier=order.carrier,
        logistics_template=order.logistics_template,
        promised_delivery_days=order.promised_delivery_days,
        transit_days=transit_days,
        days_since_last_update=_days_since_update(event, now),
        last_event_at=event.last_event_at if event else None,
        last_event_description=event.last_event_description if event else "未查询到物流轨迹",
        destination_country=order.destination_country,
        suggested_action=suggested_action,
    )


def _days_since_update(event: TrackingEvent | None, now: datetime) -> int | None:
    if not event or not event.last_event_at:
        return None
    return max(0, (now - _ensure_aware(event.last_event_at)).days)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
