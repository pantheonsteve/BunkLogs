"""Admin Programs + Settings management (Step 7_13 PR2, Stories 58 + 56).

Endpoints under ``/api/v1/admin/``:

* ``GET    /programs/``                 list active + archived programs
* ``POST   /programs/``                 create
* ``GET    /programs/<id>/``            detail
* ``PATCH  /programs/<id>/``            edit identity, dates, settings
* ``POST   /programs/<id>/end/``        End Program transaction (Story 58 c5)
* ``GET    /settings/``                 org-level settings JSON
* ``PATCH  /settings/``                 partial update

Key invariants:

* ``POST /programs/<id>/end/`` runs inside a single ``transaction.atomic``
  block so partial failures roll back. Memberships are soft-deactivated
  (``is_active=False`` + ``end_date=today``), open orders and tickets
  are closed via the state machine (``unable_to_fulfill``) with an
  ``override_close`` audit row, and an end-of-program AuditEvent is
  written per affected row.
* End Program refuses (400) when there are still open Camper Care
  flags -- those need to be resolved or migrated by the Admin
  intentionally rather than swept up automatically.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from django.db import transaction
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.maintenance.notifications import send_maintenance_notifications_test_email
from bunk_logs.api.maintenance.settings import normalize_recipients
from bunk_logs.api.maintenance.settings import validate_maintenance_settings_patch
from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Flag
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import Program
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser
from bunk_logs.core.state_machine import OrderStateMachine

from .common import viewer_or_403

logger = logging.getLogger(__name__)

PROGRAM_PATCH_FIELDS = (
    "name",
    "slug",
    "program_type",
    "start_date",
    "end_date",
    "settings",
    "is_active",
)
SETTINGS_PATCH_FIELDS = (
    "settings",
    "supported_languages",
    "rollover_hour",
    "tag_vocabulary",
)


def _serialize_program(p: Program) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "slug": p.slug,
        "program_type": p.program_type,
        "start_date": p.start_date.isoformat() if p.start_date else None,
        "end_date": p.end_date.isoformat() if p.end_date else None,
        "is_active": p.is_active,
        "settings": p.settings or {},
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _program_snapshot(p: Program) -> dict:
    return {
        "name": p.name,
        "slug": p.slug,
        "program_type": p.program_type,
        "start_date": p.start_date.isoformat() if p.start_date else None,
        "end_date": p.end_date.isoformat() if p.end_date else None,
        "is_active": p.is_active,
        "settings": dict(p.settings or {}),
    }


def _coerce_date(raw, fallback: date | None = None) -> date | None:
    if not raw:
        return fallback
    if isinstance(raw, date):
        return raw
    return parse_date(str(raw)) or fallback


# ---------------------------------------------------------------------------
# Programs list / create
# ---------------------------------------------------------------------------


class AdminProgramsListCreateView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        qs = Program.all_objects.filter(organization=ctx.organization)
        status_filter = (request.query_params.get("status") or "").strip().lower()
        if status_filter == "active":
            qs = qs.filter(is_active=True)
        elif status_filter == "archived":
            qs = qs.filter(is_active=False)
        return Response({
            "results": [_serialize_program(p) for p in qs.order_by("-start_date")],
        })

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        data = request.data or {}
        actor = ctx.membership or request.user
        try:
            program = Program(
                organization=ctx.organization,
                name=data.get("name") or "",
                slug=data.get("slug") or "",
                program_type=data.get("program_type") or "",
                start_date=_coerce_date(data.get("start_date")),
                end_date=_coerce_date(data.get("end_date")),
                settings=data.get("settings") or {},
                is_active=bool(data.get("is_active", True)),
            )
            with transaction.atomic():
                program.save()
                audit_module.created(
                    actor, program, content_type="program",
                    after_state=_program_snapshot(program),
                )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_serialize_program(program), status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Program detail / patch / end
# ---------------------------------------------------------------------------


class AdminProgramDetailView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, program_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        program = _get_program(ctx, program_id)
        if program is None:
            return _not_found()
        return Response(_serialize_program(program))

    def patch(self, request, program_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        program = _get_program(ctx, program_id)
        if program is None:
            return _not_found()
        before = _program_snapshot(program)
        changed: list[str] = []
        for field in PROGRAM_PATCH_FIELDS:
            if field not in request.data:
                continue
            value = request.data[field]
            if field in ("start_date", "end_date"):
                value = _coerce_date(value, getattr(program, field, None))
            current = getattr(program, field, None)
            if current == value:
                continue
            setattr(program, field, value)
            changed.append(field)
        if changed:
            try:
                with transaction.atomic():
                    program.save(update_fields=changed)
                    actor = ctx.membership or request.user
                    audit_module.edited(
                        actor, program, before, _program_snapshot(program),
                        content_type="program",
                    )
            except Exception as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_serialize_program(program))


class AdminProgramEndView(APIView):
    """``POST /admin/programs/<id>/end/`` -- Story 58 c5 + Story 56 cleanup.

    All side effects run in a single transaction. The response body
    summarises the rows touched so the UI can render the typed
    confirmation summary.
    """

    permission_classes = [IsOrgAdminOrSuperuser]

    def post(self, request, program_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        program = _get_program(ctx, program_id)
        if program is None:
            return _not_found()
        reason = (request.data.get("reason") or "").strip()
        if not reason:
            return Response(
                {"detail": "reason is required to end a program."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if program.is_active is False:
            return Response(
                {"detail": "Program is already ended/inactive."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        open_flags = Flag.all_objects.filter(
            organization=ctx.organization, program=program,
            status=Flag.Status.ACTIVE,
        ).count()
        if open_flags:
            return Response(
                {"detail": (
                    f"Refusing to end program with {open_flags} active Camper Care "
                    "flags. Resolve or reassign first."
                )},
                status=status.HTTP_400_BAD_REQUEST,
            )

        actor = ctx.membership or request.user
        end_date = ctx.today

        with transaction.atomic():
            # Deactivate active Memberships.
            ms_qs = Membership.all_objects.filter(program=program, is_active=True)
            deactivated_count = 0
            for m in list(ms_qs):
                before = {"is_active": m.is_active, "end_date": m.end_date.isoformat() if m.end_date else None}
                m.is_active = False
                if not m.end_date:
                    m.end_date = end_date
                m.save(update_fields=["is_active", "end_date"])
                audit_module.deactivated(
                    actor, m,
                    before_state=before,
                    after_state={"is_active": False, "end_date": end_date.isoformat()},
                    reason=f"Program ended: {reason}",
                )
                deactivated_count += 1

            # Close open orders.
            open_orders = list(
                Order.all_objects.filter(
                    organization=ctx.organization, program=program,
                    status__in=(OrderStateMachine.NEW, OrderStateMachine.IN_PROGRESS),
                ),
            )
            for o in open_orders:
                before = {"status": o.status}
                o.status = OrderStateMachine.UNABLE_TO_FULFILL
                o.save(update_fields=["status"])
                audit_module.override_close(
                    actor, o,
                    before_state=before, after_state={"status": o.status},
                    reason=f"Program ended: {reason}",
                )

            # Close open maintenance tickets.
            open_tickets = list(
                MaintenanceTicket.all_objects.filter(
                    organization=ctx.organization, program=program,
                    status__in=(OrderStateMachine.NEW, OrderStateMachine.IN_PROGRESS),
                ),
            )
            for t in open_tickets:
                before = {"status": t.status}
                t.status = OrderStateMachine.UNABLE_TO_FULFILL
                t.save(update_fields=["status"])
                audit_module.override_close(
                    actor, t,
                    before_state=before, after_state={"status": t.status},
                    reason=f"Program ended: {reason}",
                )

            before_prog = _program_snapshot(program)
            program.is_active = False
            # If End Program runs before the originally scheduled start
            # date (rare but legitimate — e.g. cancellation during setup
            # for TBE Fall 2026), respect the model's check constraint
            # ``end_date >= start_date`` by leaving ``end_date`` alone.
            # ``is_active=False`` is the canonical "ended" signal; the
            # ``ended_at`` is captured on the response summary and in the
            # audit row.
            if program.start_date and end_date >= program.start_date:
                program.end_date = end_date
                program.save(update_fields=["is_active", "end_date"])
            else:
                program.save(update_fields=["is_active"])
            audit_module.deactivated(
                actor, program, content_type="program",
                before_state=before_prog,
                after_state=_program_snapshot(program),
                reason=reason,
            )

        return Response({
            "program": _serialize_program(program),
            "summary": {
                "memberships_deactivated": deactivated_count,
                "orders_closed": len(open_orders),
                "maintenance_tickets_closed": len(open_tickets),
                "ended_at": end_date.isoformat(),
            },
        })


def _get_program(ctx, program_id) -> Program | None:
    try:
        return Program.all_objects.get(pk=program_id, organization=ctx.organization)
    except (Program.DoesNotExist, ValueError):
        return None


def _not_found() -> Response:
    return Response({"detail": "Program not found in this org."}, status=status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Org-level settings
# ---------------------------------------------------------------------------


class AdminSettingsView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        org = ctx.organization
        settings = org.settings or {}
        return Response({
            "organization_id": org.id,
            "name": org.name,
            "slug": org.slug,
            "settings": settings,
            "supported_languages": settings.get("supported_languages") or ["en"],
            "rollover_hour": settings.get("rollover_hour"),
            "tag_vocabulary": settings.get("tag_vocabulary") or [],
            "day_rollover_hour": settings.get("rollover_hour"),
        })

    def patch(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        org = ctx.organization
        before = dict(org.settings or {})
        new_settings: dict[str, Any] = dict(before)
        data = request.data or {}

        if "settings" in data and isinstance(data["settings"], dict):
            new_settings.update(data["settings"])
        for key in ("supported_languages", "rollover_hour", "tag_vocabulary"):
            if key in data:
                new_settings[key] = data[key]

        maintenance_keys = {
            k for k in new_settings
            if k in (
                "maintenance_notification_recipients",
                "maintenance_digest_time",
            )
        }
        if maintenance_keys:
            validated = validate_maintenance_settings_patch(
                {k: new_settings[k] for k in maintenance_keys},
            )
            new_settings.update(validated)

        if new_settings == before:
            return Response({"settings": before})
        org.settings = new_settings
        org.save(update_fields=["settings"])
        # Org isn't an OrgScoped model -- write a manual AuditEvent so
        # rollover / tag-vocab changes show up in the audit trail.
        AuditEvent.all_objects.create(
            event_type=AuditEvent.EventType.EDITED,
            actor_membership=ctx.membership,
            actor_user=request.user if request.user.is_authenticated else None,
            content_type="organization_settings",
            content_id=str(org.id),
            organization=org,
            before_state={"settings": before},
            after_state={"settings": new_settings},
        )
        return Response({"settings": new_settings})


class AdminMaintenanceNotificationsTestView(APIView):
    """``POST /api/v1/admin/settings/test-notifications/`` — send a test email."""

    permission_classes = [IsOrgAdminOrSuperuser]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        data = request.data or {}
        email = (data.get("email") or "").strip().lower()
        if not email:
            person = getattr(ctx, "person", None)
            email = (getattr(person, "email", None) or "").strip().lower()
        if not email:
            return Response(
                {"detail": "Email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            normalize_recipients([
                {"email": email, "instant": True, "digest": False},
            ])
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = send_maintenance_notifications_test_email(email)
        except Exception:
            logger.exception(
                "maintenance notifications test email failed for org %s",
                ctx.organization.slug,
            )
            return Response(
                {"detail": "Failed to send test email. Check server logs."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(result)
