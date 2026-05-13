"""External logistics tracking provider adapters."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

import json
from urllib.request import Request, urlopen

from .models import TrackingEvent, TrackingStatus


class TrackingClient(Protocol):
    """Protocol implemented by tracking providers such as 17TRACK and 51Tracking."""

    def get_latest_events(self, tracking_numbers: list[str]) -> dict[str, TrackingEvent]:
        """Return latest tracking events keyed by tracking number."""


class MockTrackingClient:
    """Deterministic provider used before external API keys are connected."""

    def get_latest_events(self, tracking_numbers: list[str]) -> dict[str, TrackingEvent]:
        now = datetime.now(timezone.utc)
        events: dict[str, TrackingEvent] = {}
        for index, number in enumerate(tracking_numbers):
            stale_days = 6 if index % 2 == 0 else 1
            events[number] = TrackingEvent(
                tracking_number=number,
                status=TrackingStatus.IN_TRANSIT,
                last_event_at=now - timedelta(days=stale_days),
                last_event_description="包裹运输途中（MVP 示例轨迹）",
            )
        return events


class SeventeenTrackClient:
    """Placeholder 17TRACK adapter.

    The endpoint paths and payload format should be adjusted after confirming the
    contracted 17TRACK API version for the company account.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.17track.net") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def get_latest_events(self, tracking_numbers: list[str]) -> dict[str, TrackingEvent]:
        if not self.api_key:
            raise ValueError("17TRACK API key is required when TRACKING_PROVIDER=17track")
        request = Request(
            f"{self.base_url}/track/v2/gettrackinfo",
            data=json.dumps([{"number": number} for number in tracking_numbers]).encode("utf-8"),
            headers={"17token": self.api_key, "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=30.0) as response:  # noqa: S310 - configured provider URL
            payload = json.loads(response.read().decode("utf-8"))
        return self._normalize_response(payload, tracking_numbers)

    def _normalize_response(self, payload: object, tracking_numbers: list[str]) -> dict[str, TrackingEvent]:
        # Conservative fallback until the official account API sample is provided.
        return {
            number: TrackingEvent(
                tracking_number=number,
                status=TrackingStatus.UNKNOWN,
                last_event_at=None,
                last_event_description="17TRACK 已返回数据，请按实际 API 响应完善字段映射",
                raw={"payload": payload},
            )
            for number in tracking_numbers
        }


class FiftyOneTrackingClient:
    """Placeholder 51Tracking adapter with a documented normalization seam."""

    def __init__(self, api_key: str, base_url: str = "https://api.51tracking.com") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def get_latest_events(self, tracking_numbers: list[str]) -> dict[str, TrackingEvent]:
        if not self.api_key:
            raise ValueError("51Tracking API key is required when TRACKING_PROVIDER=51track")
        request = Request(
            f"{self.base_url}/v4/trackings/batch",
            data=json.dumps({"tracking_numbers": tracking_numbers}).encode("utf-8"),
            headers={"Tracking-Api-Key": self.api_key, "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=30.0) as response:  # noqa: S310 - configured provider URL
            payload = json.loads(response.read().decode("utf-8"))
        return {
            number: TrackingEvent(
                tracking_number=number,
                status=TrackingStatus.UNKNOWN,
                last_event_at=None,
                last_event_description="51Tracking 已返回数据，请按实际 API 响应完善字段映射",
                raw={"payload": payload},
            )
            for number in tracking_numbers
        }


def build_tracking_client(provider: str, api_key: str) -> TrackingClient:
    """Create a provider adapter from configuration."""

    normalized = provider.lower().strip()
    if normalized in {"mock", "demo", ""}:
        return MockTrackingClient()
    if normalized in {"17track", "17TRACK".lower()}:
        return SeventeenTrackClient(api_key)
    if normalized in {"51track", "51tracking"}:
        return FiftyOneTrackingClient(api_key)
    raise ValueError(f"Unsupported tracking provider: {provider}")
