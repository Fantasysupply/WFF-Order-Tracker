"""Wefulfil order API adapter.

The official Wefulfil API contract is still pending. This client therefore
contains a small documented mapping layer and a mock fallback so the MVP can be
run end-to-end immediately.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import Order


class WefulfilClient:
    """Fetch and normalize orders from the Wefulfil API."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def fetch_orders(self) -> list[Order]:
        """Fetch daily orders.

        If no API key is configured, sample orders are returned so teams can test
        the reporting pipeline while API documentation is being prepared.
        """

        if not self.api_key:
            return list(self._sample_orders())

        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        orders: list[Order] = []
        page = 1
        while True:
            url = f"{self.base_url}/orders?{urlencode({'page': page, 'page_size': 100})}"
            request = Request(url, headers=headers, method="GET")
            try:
                with urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - configured API URL
                    payload = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                raise RuntimeError(f"Wefulfil API request failed with HTTP {exc.code}") from exc
            items = payload.get("data", payload.get("orders", []))
            orders.extend(self._normalize_order(item) for item in items)
            if not payload.get("next_page") and page >= int(payload.get("total_pages", page)):
                break
            page += 1
        return orders

    def _normalize_order(self, item: dict[str, Any]) -> Order:
        """Normalize a raw API record into the MVP domain model.

        Update this mapping after the Wefulfil API document is available.
        """

        shipped_at = item.get("shipped_at") or item.get("shipping_time") or item.get("fulfilled_at")
        if not shipped_at:
            raise ValueError(f"Order {item.get('order_number', item.get('id'))} has no shipped_at value")

        return Order(
            order_number=str(item.get("order_number") or item.get("id")),
            customer_name=str(item.get("customer_name") or item.get("customer") or "未归属客户"),
            account_manager=str(item.get("account_manager") or item.get("manager") or "未归属客户经理"),
            tracking_number=str(item.get("tracking_number") or item.get("tracking_no") or ""),
            carrier=str(item.get("carrier") or item.get("logistics_provider") or ""),
            logistics_template=str(item.get("logistics_template") or item.get("shipping_template") or ""),
            promised_delivery_days=int(item.get("promised_delivery_days") or item.get("promise_days") or 10),
            shipped_at=datetime.fromisoformat(str(shipped_at).replace("Z", "+00:00")),
            destination_country=str(item.get("destination_country") or item.get("country") or ""),
            raw=item,
        )

    def _sample_orders(self) -> Iterable[Order]:
        """Return deterministic sample data for the MVP dry-run path."""

        now = datetime.now(timezone.utc)
        return [
            Order(
                order_number="WFF-DEMO-1001",
                customer_name="Demo客户A",
                account_manager="客户经理-张三",
                tracking_number="YT1234567890000001",
                carrier="YunExpress",
                logistics_template="美国普货 7-10天",
                promised_delivery_days=10,
                shipped_at=now.replace(day=max(1, now.day - 13)),
                destination_country="US",
            ),
            Order(
                order_number="WFF-DEMO-1002",
                customer_name="Demo客户B",
                account_manager="客户经理-李四",
                tracking_number="LS123456789CN",
                carrier="China Post",
                logistics_template="欧洲经济 10-15天",
                promised_delivery_days=15,
                shipped_at=now.replace(day=max(1, now.day - 6)),
                destination_country="DE",
            ),
        ]
