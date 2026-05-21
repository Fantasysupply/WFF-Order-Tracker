"""Configuration loading for the MVP command line workflow."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from environment variables and an optional .env file."""

    wefulfil_base_url: str = "https://api.example-wefulfil.local"
    wefulfil_api_key: str = ""
    tracking_provider: str = "mock"
    tracking_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    mail_from: str = ""
    mail_to: str = ""
    dingtalk_webhook: str = ""
    dingtalk_secret: str = ""
    dingtalk_at_mobiles: str = ""
    report_output_dir: Path = Path("reports")
    dry_run: bool = True

    @classmethod
    def load(cls, env_path: Path = Path(".env")) -> "Settings":
        """Load settings from .env followed by process environment overrides."""

        values = _read_dotenv(env_path)
        merged = {**values, **os.environ}
        return cls(
            wefulfil_base_url=merged.get("WEFULFIL_BASE_URL", "https://api.example-wefulfil.local"),
            wefulfil_api_key=merged.get("WEFULFIL_API_KEY", ""),
            tracking_provider=merged.get("TRACKING_PROVIDER", "mock"),
            tracking_api_key=merged.get("TRACKING_API_KEY", ""),
            smtp_host=merged.get("SMTP_HOST", ""),
            smtp_port=int(merged.get("SMTP_PORT", 587)),
            smtp_username=merged.get("SMTP_USERNAME", ""),
            smtp_password=merged.get("SMTP_PASSWORD", ""),
            mail_from=merged.get("MAIL_FROM", ""),
            mail_to=merged.get("MAIL_TO", ""),
            dingtalk_webhook=merged.get("DINGTALK_WEBHOOK", ""),
            dingtalk_secret=merged.get("DINGTALK_SECRET", ""),
            dingtalk_at_mobiles=merged.get("DINGTALK_AT_MOBILES", ""),
            report_output_dir=Path(merged.get("REPORT_OUTPUT_DIR", "reports")),
            dry_run=merged.get("DRY_RUN", "true").lower() in {"1", "true", "yes", "y"},
        )


def load_rules(path: Path) -> dict[str, Any]:
    """Load simple YAML-style key/value rules used by the exception analyzer."""

    rules: dict[str, Any] = {}
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped:
                continue
            key, value = stripped.split(":", 1)
            value = value.strip()
            rules[key.strip()] = int(value) if value.isdigit() else value
    return rules


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values
