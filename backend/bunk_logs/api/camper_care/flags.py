"""Flagged campers workspace (Story 20).

Endpoints:

* ``GET    /api/v1/camper-care/flags/?status=<>`` — workspace listing
* ``POST   /api/v1/camper-care/flags/<id>/follow-up/`` — interim transition
* ``POST   /api/v1/camper-care/flags/<id>/resolve/`` — terminal, closing note required
* ``POST   /api/v1/camper-care/flags/<id>/reopen/`` — reopen, reason required

Resolution is restricted to Camper Care per CC3 (the original raiser can
add follow-up via a separate note but cannot close the flag); the
endpoint requires an active Camper Care Membership so the gate is
expressed at the same boundary as the rest of the workspace.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status as http_status
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Flag
from bunk_logs.notes.models import Observation

from .common import caseload_camper_ids
from .common import viewer_or_403

# Trigger content types we know how to preview. Adding new types is
# a one-line addition here; the frontend renders ``trigger_preview``
# generically (truncated snippet + source label).
_PREVIEW_LOADERS: dict[str, str] = {
    "specialist_note": "note",
    "camper_care_note": "note",
    "reflection": "reflection",
}
_PREVIEW_MAX_CHARS = 160

ACTIVE_STATUSES: tuple[str, ...] = (Flag.Status.ACTIVE, Flag.Status.FOLLOWED_UP)
ALL_STATUSES: tuple[str, ...] = tuple(s.value for s in Flag.Status)


class FlagListView(APIView):
    """``GET /api/v1/camper-care/flags/`` — workspace listing.

    Query params:
      * ``status`` — one of ``active`` / ``followed_up`` / ``resolved``
        (omit to return active + followed_up = "unresolved")
      * ``caseload_only`` — ``true`` to scope to the viewer's caseload
        (default ``false``: workspace shows ALL camper-care flags for
        the program, per CC2's overlapping-caseload allowance).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        status_q = (request.query_params.get("status") or "").strip().lower()
        if status_q and status_q not in ALL_STATUSES:
            return Response(
                {"status": f"Unknown status {status_q!r}."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        qs = Flag.objects.filter(
            program=ctx.program,
            flagged_for_role="camper_care",
        )
        if not status_q:
            qs = qs.filter(status__in=ACTIVE_STATUSES)
        else:
            qs = qs.filter(status=status_q)

        caseload_only = (request.query_params.get("caseload_only") or "").lower() in {"1", "true"}
        if caseload_only:
            camper_ids = caseload_camper_ids(ctx.membership)
            qs = qs.filter(subject_camper_id__in=camper_ids)

        rows = list(
            qs.select_related(
                "subject_camper", "raised_by_membership__person",
            ).order_by("-created_at"),
        )

        today = ctx.today
        items = [_flag_payload(f, today=today) for f in rows]
        return Response({"items": items, "today": today.isoformat()})


class FlagDetailView(APIView):
    """``GET /api/v1/camper-care/flags/<id>/`` — full flag activity.

    Returns the flag, the *full* source note/reflection body (the list
    endpoint only sends a truncated ``trigger_preview``), and the audit
    history so Camper Care can expand a row to read every follow-up,
    resolution, and reopen note their team has written on it.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, flag_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        flag = (
            Flag.objects.filter(pk=flag_id, program=ctx.program)
            .select_related("subject_camper", "raised_by_membership__person")
            .first()
        )
        if flag is None:
            msg = "Flag not found."
            raise NotFound(msg)
        if flag.flagged_for_role != "camper_care":
            msg = "This flag is not routed to Camper Care."
            raise PermissionDenied(msg)
        return Response(
            {
                "flag": _flag_payload(flag, today=ctx.today),
                "trigger": _trigger_detail(flag),
                "history": _audit_history(flag),
            },
        )


class FlagFollowUpView(APIView):
    """``POST /api/v1/camper-care/flags/<id>/follow-up/`` — interim transition.

    Optional ``note`` captured in audit metadata. ACTIVE -> FOLLOWED_UP
    is the standard path; FOLLOWED_UP -> FOLLOWED_UP is allowed so a
    second follow-up just appends another audit row.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, flag_id, *args, **kwargs):
        return _transition(request, flag_id, to_state=Flag.Status.FOLLOWED_UP)


class FlagResolveView(APIView):
    """``POST /api/v1/camper-care/flags/<id>/resolve/`` — terminal transition.

    ``note`` is required (closing note per Story 20 criterion 5.ii) and
    persisted into the audit event's ``reason_note`` so it surfaces on
    the camper dashboard timeline.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, flag_id, *args, **kwargs):
        return _transition(request, flag_id, to_state=Flag.Status.RESOLVED)


class FlagReopenView(APIView):
    """``POST /api/v1/camper-care/flags/<id>/reopen/`` — reopen to ACTIVE.

    ``note`` is required (reopen reason per Story 20 criterion 5.iii).
    Reopen path covers both RESOLVED -> ACTIVE and FOLLOWED_UP -> ACTIVE.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, flag_id, *args, **kwargs):
        return _transition(request, flag_id, to_state=Flag.Status.ACTIVE)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _transition(request, flag_id, *, to_state: str) -> Response:
    ctx = viewer_or_403(request)
    flag = Flag.objects.filter(pk=flag_id, program=ctx.program).first()
    if flag is None:
        msg = "Flag not found."
        raise NotFound(msg)
    if flag.flagged_for_role != "camper_care":
        msg = "This flag is not routed to Camper Care."
        raise PermissionDenied(msg)
    note = (request.data.get("note") or "").strip()
    try:
        flag.transition_to(to_state, actor=ctx.membership, note=note)
    except DjangoValidationError as e:
        return Response(
            e.message_dict if hasattr(e, "message_dict") else {"detail": str(e)},
            status=http_status.HTTP_400_BAD_REQUEST,
        )
    history = _audit_history(flag)
    return Response({"flag": _flag_payload(flag, today=ctx.today), "history": history})


def _flag_payload(flag: Flag, *, today) -> dict:
    raiser = flag.raised_by_membership
    raiser_person = getattr(raiser, "person", None) if raiser else None
    return {
        "id": str(flag.id),
        "status": flag.status,
        "subject_camper": _camper_brief(flag.subject_camper),
        "flagged_for_role": flag.flagged_for_role,
        "trigger_content_type": flag.trigger_content_type,
        "trigger_content_id": flag.trigger_content_id,
        "trigger_preview": _trigger_preview(flag),
        "raised_by": {
            "membership_id": raiser.id if raiser else None,
            "role": raiser.role if raiser else None,
            "name": (
                f"{raiser_person.first_name} {raiser_person.last_name}".strip()
                if raiser_person else None
            ),
        },
        "created_at": flag.created_at.isoformat(),
        "updated_at": flag.updated_at.isoformat(),
        "resolved_at": flag.resolved_at.isoformat() if flag.resolved_at else None,
        "is_today": flag.created_at.date() == today,
    }


def _observation_for_flag_trigger(trigger_content_id: str) -> Observation | None:
    """Resolve a legacy specialist/camper-care note id to a migrated Observation."""
    if not trigger_content_id:
        return None
    obs = Observation.all_objects.filter(
        legacy_source=f"core.note:{trigger_content_id}",
    ).first()
    if obs is not None:
        return obs
    try:
        return Observation.all_objects.filter(pk=int(trigger_content_id)).first()
    except (ValueError, TypeError):
        return None


def _trigger_preview(flag: Flag) -> str:
    """Short snippet of the row that raised the flag.

    Falls back to "" when the trigger type isn't one we know how to
    preview, or when the underlying row is gone (deleted note, etc).
    Camper Care reads this on the workspace row to know whether to
    open a flag without leaving the workspace.
    """
    loader = _PREVIEW_LOADERS.get(flag.trigger_content_type)
    if not loader or not flag.trigger_content_id:
        return ""
    try:
        if loader == "note":
            obs = _observation_for_flag_trigger(flag.trigger_content_id)
            body = (obs.body or "").strip() if obs else ""
        else:
            # Reflection trigger preview — first non-empty string answer.
            # Lazy import keeps the test path narrow.
            from bunk_logs.core.models import Reflection
            refl = Reflection.all_objects.filter(id=flag.trigger_content_id).first()
            body = ""
            if refl and isinstance(refl.answers, dict):
                for v in refl.answers.values():
                    if isinstance(v, str) and v.strip():
                        body = v.strip()
                        break
    except (ValueError, TypeError):
        return ""
    if not body:
        return ""
    if len(body) > _PREVIEW_MAX_CHARS:
        return body[: _PREVIEW_MAX_CHARS - 1] + "\u2026"
    return body


def _trigger_detail(flag: Flag) -> dict:
    """Full source content that raised the flag (note body / reflection text).

    Unlike :func:`_trigger_preview` this returns the untruncated body plus
    author + timestamp so the workspace can render the whole source inline
    when a row is expanded. Falls back gracefully when the trigger is an
    unknown type or the underlying row was deleted.
    """
    detail = {
        "content_type": flag.trigger_content_type,
        "content_id": flag.trigger_content_id,
        "body": "",
        "author": None,
        "created_at": None,
    }
    loader = _PREVIEW_LOADERS.get(flag.trigger_content_type)
    if not loader or not flag.trigger_content_id:
        return detail
    try:
        if loader == "note":
            obs = _observation_for_flag_trigger(flag.trigger_content_id)
            if obs is not None:
                detail["body"] = (obs.body or "").strip()
                detail["created_at"] = obs.created_at.isoformat()
                detail["author"] = _person_name(obs.author)
        else:
            from bunk_logs.core.models import Reflection
            refl = Reflection.all_objects.filter(id=flag.trigger_content_id).first()
            if refl is not None:
                detail["created_at"] = (
                    refl.created_at.isoformat() if refl.created_at else None
                )
                if isinstance(refl.answers, dict):
                    parts = [
                        v.strip()
                        for v in refl.answers.values()
                        if isinstance(v, str) and v.strip()
                    ]
                    detail["body"] = "\n\n".join(parts)
    except (ValueError, TypeError):
        return detail
    return detail


def _person_name(person) -> str | None:
    if person is None:
        return None
    name = f"{person.first_name} {person.last_name}".strip()
    return name or None


def _actor_brief(membership) -> dict:
    if membership is None:
        return {"membership_id": None, "name": None, "role": None}
    return {
        "membership_id": membership.id,
        "name": _person_name(getattr(membership, "person", None)),
        "role": membership.role,
    }


def _audit_history(flag: Flag) -> list[dict]:
    rows = (
        AuditEvent.objects.filter(content_type="flag", content_id=str(flag.id))
        .select_related("actor_membership__person")
        .order_by("created_at")
    )
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "before_state": e.before_state,
            "after_state": e.after_state,
            "reason_note": e.reason_note,
            "actor": _actor_brief(e.actor_membership),
            "actor_membership_id": e.actor_membership_id,
            "created_at": e.created_at.isoformat(),
        }
        for e in rows
    ]


def _camper_brief(camper) -> dict | None:
    if camper is None:
        return None
    return {
        "id": camper.id,
        "first_name": camper.first_name,
        "last_name": camper.last_name,
        "preferred_name": camper.preferred_name,
    }
