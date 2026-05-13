"""Shared domain models for orders, tracking events, and exception reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class TrackingStatus(StrEnum):
    """Normalized logistics states used by the MVP rules engine."""

    UNKNOWN = "unknown"
    IN_TRANSIT = "in_transit"
    PICKED_UP = "picked_up"
    CUSTOMS = "customs"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"


class RiskLevel(StrEnum):
    """Exception severity used in generated reports."""

    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"


@dataclass(slots=True)
class Order:
    """A normalized Wefulfil order record.

    Field names are intentionally API-agnostic so the Wefulfil API adapter can be
    updated once the official API documentation is available.
    """

    order_number: str
    customer_name: str
    account_manager: str
    tracking_number: str
    carrier: str
    logistics_template: str
    promised_delivery_days: int
    shipped_at: datetime
    destination_country: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TrackingEvent:
    """Latest normalized tracking snapshot for a logistics number."""

    tracking_number: str
    status: TrackingStatus
    last_event_at: datetime | None
    last_event_description: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExceptionRecord:
    """A row in the fulfillment exception report."""

    exception_type: str
    risk_level: RiskLevel
    order_number: str
    customer_name: str
    account_manager: str
    tracking_number: str
    carrier: str
    logistics_template: str
    promised_delivery_days: int
    transit_days: int
    days_since_last_update: int | None
    last_event_at: datetime | None
    last_event_description: str
    destination_country: str
    suggested_action: str

    def to_excel_row(self) -> list[str | int | None]:
        """Return a localized row that can be appended to an Excel worksheet."""

        return [
            self.exception_type,
            self.risk_level.value,
            self.order_number,
            self.customer_name,
            self.account_manager,
            self.tracking_number,
            self.carrier,
            self.logistics_template,
            self.promised_delivery_days,
            self.transit_days,
            self.days_since_last_update,
            self.last_event_at.isoformat(sep=" ", timespec="seconds") if self.last_event_at else "",
            self.last_event_description,
            self.destination_country,
            self.suggested_action,
        ]
