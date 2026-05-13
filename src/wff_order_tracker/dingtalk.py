"""DingTalk robot notification helper.

DingTalk incoming webhooks send messages to a selected group. To reach a precise
fulfillment owner, configure that owner in the robot group and set
DINGTALK_AT_MOBILES so the message mentions the responsible person.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from .config import Settings
from .models import ExceptionRecord, RiskLevel


def send_dingtalk_report(settings: Settings, report_path: Path, records: list[ExceptionRecord]) -> None:
    """Send a Markdown summary to a DingTalk robot webhook."""

    mobiles = [item.strip() for item in settings.dingtalk_at_mobiles.split(",") if item.strip()]
    if settings.dry_run or not settings.dingtalk_webhook:
        print(f"[DRY-RUN] Would notify DingTalk for {report_path} with @ {mobiles or '[no mobiles configured]'}")
        return

    webhook = _signed_webhook(settings.dingtalk_webhook, settings.dingtalk_secret)
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": "Wefulfil 履约异常订单清查报告",
            "text": _build_markdown(report_path, records, mobiles),
        },
        "at": {"atMobiles": mobiles, "isAtAll": False},
    }
    request = Request(
        webhook,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30.0) as response:  # noqa: S310 - configured DingTalk webhook
        body = json.loads(response.read().decode("utf-8"))
    if body.get("errcode") not in {0, None}:
        raise RuntimeError(f"DingTalk notification failed: {body}")


def _signed_webhook(webhook: str, secret: str) -> str:
    if not secret:
        return webhook
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), string_to_sign, digestmod=hashlib.sha256).digest()
    sign = quote_plus(base64.b64encode(digest))
    separator = "&" if "?" in webhook else "?"
    return f"{webhook}{separator}timestamp={timestamp}&sign={sign}"


def _build_markdown(report_path: Path, records: list[ExceptionRecord], mobiles: list[str]) -> str:
    total = len(records)
    high = sum(1 for record in records if record.risk_level == RiskLevel.HIGH)
    by_manager: dict[str, int] = {}
    by_exception: dict[str, int] = {}
    for record in records:
        by_manager[record.account_manager] = by_manager.get(record.account_manager, 0) + 1
        by_exception[record.exception_type] = by_exception.get(record.exception_type, 0) + 1

    manager_lines = "\n".join(f"> - {manager}: {count} 单" for manager, count in sorted(by_manager.items())) or "> - 暂无异常"
    exception_lines = "\n".join(f"> - {kind}: {count} 单" for kind, count in sorted(by_exception.items())) or "> - 暂无异常"
    at_line = " ".join(f"@{mobile}" for mobile in mobiles)
    return (
        "### Wefulfil 履约异常订单清查报告\n\n"
        f"> 异常订单总数：**{total}** 单\n\n"
        f"> 高风险订单：**{high}** 单\n\n"
        "> **按客户经理汇总**\n"
        f"{manager_lines}\n\n"
        "> **按异常类型汇总**\n"
        f"{exception_lines}\n\n"
        f"> Excel 报告路径：`{report_path}`\n\n"
        f"请履约负责人按报告中的 AM/客户维度清查。{at_line}"
    )
