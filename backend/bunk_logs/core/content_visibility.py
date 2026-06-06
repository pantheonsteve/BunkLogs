"""Cross-cutting visibility model — audience rules per content type.

Canonical product spec: ``docs/user_stories/00_cross_cutting/visibility_model.md``
"""
from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bunk_logs.core.models import Reflection

# Display labels for AudienceDisclosure (English defaults; i18n keys in frontend).
ROLE_LABELS: dict[str, str] = {
    "counselor": "Counselor",
    "unit_head": "Unit Head",
    "camper_care": "Camper Care",
    "leadership_team": "Leadership Team",
    "admin": "Admin",
    "health_center": "Health Center",
    "special_diets": "Special Diets",
    "specialist": "Specialist",
    "maintenance": "Maintenance",
    "administrative_staff": "Administrative Staff",
    "kitchen_staff": "Kitchen Staff",
    "medical": "Medical",
    "madrich": "Madrich",
    "director": "Director",
    "platform_support": "Platform support",
}


class ContentType(StrEnum):
    CAMPER_REFLECTION = "camper_reflection"
    COUNSELOR_SELF_REFLECTION = "counselor_self_reflection"
    UNIT_HEAD_SELF_REFLECTION = "unit_head_self_reflection"
    CAMPER_CARE_NOTE = "camper_care_note"
    SPECIALIST_NOTE = "specialist_note"
    SPECIALIST_SELF_REFLECTION = "specialist_self_reflection"
    MAINTENANCE_TICKET_NOTE = "maintenance_ticket_note"
    KITCHEN_STAFF_REFLECTION = "kitchen_staff_reflection"
    LEADERSHIP_TEAM_SELF_REFLECTION = "leadership_team_self_reflection"
    MADRICH_REFLECTION = "madrich_reflection"
    ADMIN_SELF_REFLECTION = "admin_self_reflection"


class MaintenanceNoteVisibility(StrEnum):
    TEAM_ONLY = "team_only"
    SUBMITTER_VISIBLE = "submitter_visible"


# Membership.role keys allowed to read each content type.
# Line-by-line encoding of the visibility table in visibility_model.md.
_DEFAULT_AUDIENCES: dict[ContentType, frozenset[str]] = {
    ContentType.CAMPER_REFLECTION: frozenset({
        "counselor", "unit_head", "camper_care", "leadership_team", "admin",
    }),
    ContentType.COUNSELOR_SELF_REFLECTION: frozenset({
        "counselor", "unit_head", "leadership_team", "admin",
    }),
    ContentType.UNIT_HEAD_SELF_REFLECTION: frozenset({
        "unit_head", "leadership_team", "admin",
    }),
    ContentType.CAMPER_CARE_NOTE: frozenset({
        "camper_care", "leadership_team", "admin",
    }),
    ContentType.SPECIALIST_NOTE: frozenset({
        "counselor", "unit_head", "camper_care", "leadership_team", "admin",
    }),
    ContentType.SPECIALIST_SELF_REFLECTION: frozenset({
        "specialist", "leadership_team", "admin",
    }),
    ContentType.KITCHEN_STAFF_REFLECTION: frozenset({
        "leadership_team", "admin",
    }),
    ContentType.LEADERSHIP_TEAM_SELF_REFLECTION: frozenset({
        "leadership_team", "admin",
    }),
    ContentType.MADRICH_REFLECTION: frozenset({
        "director", "admin",
    }),
    ContentType.ADMIN_SELF_REFLECTION: frozenset({
        "admin", "platform_support",
    }),
}

_SENSITIVE_AUDIENCES: dict[ContentType, frozenset[str]] = {
    ContentType.CAMPER_CARE_NOTE: frozenset({
        "camper_care", "health_center", "medical", "special_diets", "admin",
    }),
    ContentType.SPECIALIST_NOTE: frozenset({
        "camper_care", "health_center", "medical", "special_diets", "admin",
    }),
    ContentType.LEADERSHIP_TEAM_SELF_REFLECTION: frozenset({"admin"}),
    ContentType.ADMIN_SELF_REFLECTION: frozenset({"admin"}),
}

_MAINTENANCE_TEAM_ONLY = frozenset({"maintenance", "admin"})
_MAINTENANCE_SUBMITTER_VISIBLE = frozenset({
    "maintenance", "admin", "counselor", "unit_head", "leadership_team",
})


def audience_roles(
    content_type: ContentType,
    *,
    is_sensitive: bool = False,
    is_private: bool = False,
    maintenance_visibility: MaintenanceNoteVisibility | str | None = None,
) -> frozenset[str]:
    """Return membership.role keys that may read this content (excluding author bypass)."""
    if is_private or is_sensitive:
        sensitive = _SENSITIVE_AUDIENCES.get(content_type)
        if sensitive is not None:
            return sensitive

    if content_type is ContentType.MAINTENANCE_TICKET_NOTE:
        mode = maintenance_visibility or MaintenanceNoteVisibility.TEAM_ONLY
        if isinstance(mode, str):
            mode = MaintenanceNoteVisibility(mode)
        if mode is MaintenanceNoteVisibility.SUBMITTER_VISIBLE:
            return _MAINTENANCE_SUBMITTER_VISIBLE
        return _MAINTENANCE_TEAM_ONLY

    return _DEFAULT_AUDIENCES[content_type]


def audience_labels(
    content_type: ContentType,
    *,
    is_sensitive: bool = False,
    is_private: bool = False,
    maintenance_visibility: MaintenanceNoteVisibility | str | None = None,
) -> list[str]:
    """Human-readable role labels for write-time AudienceDisclosure."""
    roles = audience_roles(
        content_type,
        is_sensitive=is_sensitive,
        is_private=is_private,
        maintenance_visibility=maintenance_visibility,
    )
    return [ROLE_LABELS.get(r, r.replace("_", " ").title()) for r in sorted(roles)]


def viewer_can_read(
    viewer_roles: frozenset[str] | set[str],
    content_type: ContentType,
    *,
    is_sensitive: bool = False,
    is_private: bool = False,
    maintenance_visibility: MaintenanceNoteVisibility | str | None = None,
    is_author: bool = False,
    is_org_admin: bool = False,
) -> bool:
    """Whether a viewer may read content given their active membership roles."""
    if is_author or is_org_admin:
        return True
    allowed = audience_roles(
        content_type,
        is_sensitive=is_sensitive,
        is_private=is_private,
        maintenance_visibility=maintenance_visibility,
    )
    expanded = set(viewer_roles)
    # Director reads madrich reflections; org admin satisfies TBE Admin / platform_support.
    if "leadership_team" in expanded and "director" in allowed:
        expanded.add("director")
    if "admin" in expanded:
        expanded.update({"admin", "platform_support", "director"})
    return bool(expanded & allowed)


def reflection_content_type(reflection: Reflection) -> ContentType:
    """Map a Reflection instance to its visibility content type."""
    tpl = reflection.template
    role = tpl.role or ""
    subject_mode = tpl.subject_mode or "self"

    if subject_mode == "self":
        mapping = {
            "counselor": ContentType.COUNSELOR_SELF_REFLECTION,
            "unit_head": ContentType.UNIT_HEAD_SELF_REFLECTION,
            "specialist": ContentType.SPECIALIST_SELF_REFLECTION,
            "leadership_team": ContentType.LEADERSHIP_TEAM_SELF_REFLECTION,
            "admin": ContentType.ADMIN_SELF_REFLECTION,
            "kitchen_staff": ContentType.KITCHEN_STAFF_REFLECTION,
            "madrich": ContentType.MADRICH_REFLECTION,
        }
        if role in mapping:
            return mapping[role]
        return ContentType.COUNSELOR_SELF_REFLECTION

    if role == "counselor" or "camper" in (tpl.subject_role_filter or []):
        return ContentType.CAMPER_REFLECTION
    if role == "specialist":
        return ContentType.SPECIALIST_NOTE
    if role == "camper_care":
        return ContentType.CAMPER_CARE_NOTE
    if role == "kitchen_staff":
        return ContentType.KITCHEN_STAFF_REFLECTION
    if role == "madrich":
        return ContentType.MADRICH_REFLECTION
    return ContentType.CAMPER_REFLECTION


def reflection_is_private(reflection: Reflection) -> bool:
    from bunk_logs.core.models import Reflection as ReflectionModel

    return reflection.team_visibility == ReflectionModel.TeamVisibility.SUPERVISORS_ONLY


def gating_role_label(content_type: ContentType) -> str:
    """Role label for SensitiveNotePlaceholder (who to ask about gated content)."""
    if content_type in (ContentType.CAMPER_CARE_NOTE, ContentType.SPECIALIST_NOTE):
        return ROLE_LABELS["camper_care"]
    if content_type in (
        ContentType.LEADERSHIP_TEAM_SELF_REFLECTION,
        ContentType.ADMIN_SELF_REFLECTION,
    ):
        return ROLE_LABELS["admin"]
    return ROLE_LABELS["camper_care"]
