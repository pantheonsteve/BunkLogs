"""``POST /api/v1/admin/override-edit/`` -- Story 59 criterion 8.

Admin overrides another role's authorship on a content row (reflection
or note) by submitting an edit with a mandatory reason. The write goes
straight to the underlying model so the Admin doesn't have to spoof the
authoring role's endpoint, and the action is captured in the audit log
via :func:`bunk_logs.core.audit.override_edit` so reviewers can see
*who* did *what*, *why*, with the before/after diff.

Supported content types in PR1:

* ``reflection`` -- patches ``answers``, ``language``,
  ``team_visibility``, ``is_complete``, ``is_sensitive``.
* ``note`` -- patches ``body``, ``is_sensitive``,
  ``maintenance_visibility``, ``language``.

Other content types raise a 400. Override-close / override-resolve
flows live alongside the order/flag endpoints in PR2.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import Note
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import note_snapshot
from bunk_logs.core.models import reflection_snapshot
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser

from .common import viewer_or_403

# Fields we let an Admin patch per content type. Anything outside this
# allowlist is silently ignored so a client cannot, say, rewrite a
# Reflection's ``author`` from the override surface.
ALLOWED_REFLECTION_FIELDS = frozenset({
    "answers",
    "language",
    "team_visibility",
    "is_complete",
    "is_sensitive",
})
ALLOWED_NOTE_FIELDS = frozenset({
    "body",
    "is_sensitive",
    "maintenance_visibility",
    "language",
})


class AdminOverrideEditView(APIView):
    """Admin override path with required reason."""

    permission_classes = [IsOrgAdminOrSuperuser]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        content_type = (request.data.get("content_type") or "").strip()
        content_id = request.data.get("content_id")
        patch = request.data.get("patch") or {}
        reason = (request.data.get("reason") or "").strip()

        if not content_type or content_id in (None, ""):
            return Response(
                {"detail": "content_type and content_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not reason:
            # Per Story 59 c8: Admin override is an explicit, auditable
            # action -- reason is mandatory.
            return Response(
                {"detail": "reason is required for an admin override."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if not isinstance(patch, dict):
            return Response(
                {"detail": "patch must be an object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        actor = ctx.membership or request.user
        try:
            with transaction.atomic():
                if content_type == "reflection":
                    payload = _apply_reflection_override(
                        ctx, content_id, patch, reason, actor,
                    )
                elif content_type == "note":
                    payload = _apply_note_override(
                        ctx, content_id, patch, reason, actor,
                    )
                else:
                    return Response(
                        {
                            "detail": (
                                "Unsupported content_type for override-edit. "
                                "Supported: reflection, note."
                            ),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except _OverrideNotFoundError:
            return Response(
                {"detail": "Target content not found in this org."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(payload)


# ---------------------------------------------------------------------------
# Reflection override
# ---------------------------------------------------------------------------


def _apply_reflection_override(
    ctx, content_id, patch: dict, reason: str, actor: Any,
) -> dict:
    try:
        reflection = (
            Reflection.all_objects.select_related("template", "organization")
            .get(pk=content_id, organization=ctx.organization)
        )
    except Reflection.DoesNotExist as exc:
        raise _OverrideNotFoundError from exc
    before = reflection_snapshot(reflection)
    changed = _apply_patch(reflection, patch, ALLOWED_REFLECTION_FIELDS)
    if changed:
        reflection.save()
    after = reflection_snapshot(reflection)
    audit_module.override_edit(
        actor, reflection, before, after, reason=reason,
    )
    return {
        "content_type": "reflection",
        "content_id": reflection.id,
        "before": before,
        "after": after,
        "fields_changed": sorted(changed),
    }


# ---------------------------------------------------------------------------
# Note override
# ---------------------------------------------------------------------------


def _apply_note_override(
    ctx, content_id, patch: dict, reason: str, actor: Any,
) -> dict:
    try:
        note = Note.all_objects.select_related("organization").get(
            pk=content_id, organization=ctx.organization,
        )
    except Note.DoesNotExist as exc:
        raise _OverrideNotFoundError from exc
    before = note_snapshot(note)
    changed = _apply_patch(note, patch, ALLOWED_NOTE_FIELDS)
    if changed:
        note.save()
    after = note_snapshot(note)
    audit_module.override_edit(
        actor, note, before, after, reason=reason,
    )
    return {
        "content_type": "note",
        "content_id": note.id,
        "before": before,
        "after": after,
        "fields_changed": sorted(changed),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_patch(instance, patch: dict, allowed: frozenset) -> set[str]:
    """Set allowed fields from ``patch`` on ``instance``; return the set we touched."""
    changed: set[str] = set()
    for key, value in patch.items():
        if key not in allowed:
            continue
        current = getattr(instance, key, None)
        if current == value:
            continue
        setattr(instance, key, value)
        changed.add(key)
    return changed


class _OverrideNotFoundError(Exception):
    """Internal sentinel for the not-found branches."""
