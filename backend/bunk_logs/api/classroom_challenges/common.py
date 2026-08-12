"""Shared serializers + classroom-membership helpers for Step 4_8.

Semi-anonymity rules (MA7): peer Madrichim never see another author's
identity; the author sees their own; faculty and admin always see it.
Faculty replies are always attributed. Centralizing ``serialize_author``
here keeps that rule from drifting between the Madrich and Faculty
endpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bunk_logs.core.models import AssignmentGroupMembership

if TYPE_CHECKING:
    from bunk_logs.core.models import ClassroomChallenge
    from bunk_logs.core.models import ClassroomChallengeResponse
    from bunk_logs.core.models import Person
    from bunk_logs.core.models import Program

BODY_PREVIEW_LEN = 120
REDACTED_DISPLAY = "A Madrich"


def _truncate(text: str, limit: int = BODY_PREVIEW_LEN) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"


def serialize_author(person: Person | None, *, redacted: bool) -> dict:
    """Viewer-dependent author redaction (semi-anonymity table, MA7).

    Never leaks ``id`` when ``redacted`` -- peer Madrichim get a display
    label only, so a stale id can't be joined against another endpoint.
    """
    if redacted:
        return {"display": REDACTED_DISPLAY, "redacted": True}
    if person is None:
        return {"display": "Unknown", "redacted": False}
    return {
        "id": person.id,
        "display_name": person.full_name,
        "redacted": False,
    }


def classroom_brief(group) -> dict:
    return {"id": group.id, "name": group.name}


def response_payload(response: ClassroomChallengeResponse) -> dict:
    """Faculty replies are always attributed, even to a peer viewer."""
    return {
        "id": str(response.id),
        "author": serialize_author(response.author, redacted=False),
        "body": response.body,
        "created_at": response.created_at.isoformat(),
    }


def challenge_list_item(
    challenge: ClassroomChallenge, *, redacted: bool, response_count: int, include_group: bool = False,
) -> dict:
    item = {
        "id": str(challenge.id),
        "category": challenge.category,
        "category_label": challenge.get_category_display(),
        "session_date": challenge.session_date.isoformat(),
        "body_preview": _truncate(challenge.body),
        "status": challenge.status,
        "author": serialize_author(challenge.author, redacted=redacted),
        "response_count": response_count,
        "created_at": challenge.created_at.isoformat(),
    }
    if include_group:
        item["assignment_group"] = classroom_brief(challenge.assignment_group)
    return item


def challenge_detail(challenge: ClassroomChallenge, *, redacted: bool) -> dict:
    return {
        "id": str(challenge.id),
        "assignment_group": classroom_brief(challenge.assignment_group),
        "category": challenge.category,
        "category_label": challenge.get_category_display(),
        "session_date": challenge.session_date.isoformat(),
        "body": challenge.body,
        "status": challenge.status,
        "author": serialize_author(challenge.author, redacted=redacted),
        "created_at": challenge.created_at.isoformat(),
        "updated_at": challenge.updated_at.isoformat(),
        "resolved_at": challenge.resolved_at.isoformat() if challenge.resolved_at else None,
        "resolved_by": (
            serialize_author(challenge.resolved_by, redacted=False)
            if challenge.resolved_by_id
            else None
        ),
        "responses": [
            response_payload(r) for r in challenge.responses.all().select_related("author")
        ],
    }


def classroom_group_ids_for_role(person: Person, program: Program, *, role_in_group: str) -> list[int]:
    """Active classroom ``AssignmentGroup`` ids where ``person`` holds ``role_in_group``."""
    return list(
        AssignmentGroupMembership.objects.filter(
            person=person,
            role_in_group=role_in_group,
            is_active=True,
            group__group_type="classroom",
            group__program=program,
            group__is_active=True,
        ).values_list("group_id", flat=True),
    )


def is_classroom_subject(person: Person, group_id: int) -> bool:
    return AssignmentGroupMembership.objects.filter(
        person=person, group_id=group_id, role_in_group="subject", is_active=True,
    ).exists()


def is_classroom_author(person: Person, group_id: int) -> bool:
    return AssignmentGroupMembership.objects.filter(
        person=person, group_id=group_id, role_in_group="author", is_active=True,
    ).exists()
