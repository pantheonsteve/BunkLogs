"""Org settings helpers for maintenance email notifications."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from typing import Any

from rest_framework.exceptions import ValidationError

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DEFAULT_DIGEST_TIME = "06:00"
TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def _normalize_recipient(raw: dict[str, Any]) -> dict[str, Any]:
    email = (raw.get("email") or "").strip().lower()
    if not email or not EMAIL_RE.match(email):
        msg = f"Invalid email address: {raw.get('email')!r}"
        raise ValidationError({"maintenance_notification_recipients": msg})
    return {
        "email": email,
        "instant": bool(raw.get("instant")),
        "digest": bool(raw.get("digest")),
    }


def normalize_recipients(raw: list[Any]) -> list[dict[str, Any]]:
    """Validate and dedupe a recipient list (last entry wins per email)."""
    if not isinstance(raw, list):
        msg = "Must be a list of recipient objects."
        raise ValidationError({"maintenance_notification_recipients": msg})

    by_email: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict):
            msg = "Each recipient must be an object with email, instant, and digest."
            raise ValidationError({"maintenance_notification_recipients": msg})
        normalized = _normalize_recipient(item)
        by_email[normalized["email"]] = normalized
    return list(by_email.values())


def validate_digest_time(value: str) -> str:
    if not TIME_RE.match(value):
        msg = "maintenance_digest_time must be HH:MM (24-hour)."
        raise ValidationError({"maintenance_digest_time": msg})
    hour, minute = value.split(":")
    return f"{int(hour):02d}:{int(minute):02d}"


def validate_maintenance_settings_patch(patch: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize maintenance-related keys in a settings patch."""
    normalized: dict[str, Any] = {}
    if "maintenance_notification_recipients" in patch:
        normalized["maintenance_notification_recipients"] = normalize_recipients(
            patch["maintenance_notification_recipients"],
        )
    if "maintenance_digest_time" in patch:
        normalized["maintenance_digest_time"] = validate_digest_time(
            str(patch["maintenance_digest_time"]).strip(),
        )
    return normalized


def get_notification_recipients(org: Organization) -> list[dict[str, Any]]:
    """Return normalized recipient list with legacy ``maintenance_digest_email`` fallback."""
    settings = org.settings or {}
    recipients = settings.get("maintenance_notification_recipients")
    if recipients:
        return normalize_recipients(recipients)
    legacy = (settings.get("maintenance_digest_email") or "").strip().lower()
    if legacy:
        return [{"email": legacy, "instant": False, "digest": True}]
    return []


def get_instant_recipients(org: Organization) -> list[str]:
    return [r["email"] for r in get_notification_recipients(org) if r.get("instant")]


def get_digest_recipients(org: Organization) -> list[str]:
    return [r["email"] for r in get_notification_recipients(org) if r.get("digest")]


def digest_time(org: Organization) -> str:
    return (org.settings or {}).get("maintenance_digest_time", DEFAULT_DIGEST_TIME)


def is_configured_recipient(org: Organization, email: str) -> bool:
    """True when ``email`` is listed for instant or digest on this org."""
    normalized = email.strip().lower()
    return any(r["email"] == normalized for r in get_notification_recipients(org))
