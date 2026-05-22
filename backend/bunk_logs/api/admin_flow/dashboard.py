"""``GET /api/v1/admin/dashboard/`` -- Story 54.

Returns three top-level sections:

* ``org_snapshot`` -- counts an Admin glances at first thing in the
  morning: active people, memberships by role, today's reflection
  completion rate, open Camper Care orders, open Maintenance tickets,
  active Camper Care flags.
* ``attention_required`` -- six conditions from Story 54 criterion 5
  (stale tickets / orders, unresolved flags, pending template review,
  digest delivery failures, translation pipeline failures). Each card
  carries a count and a deep-link payload so the frontend doesn't have
  to know how to construct the URL.
* ``recent_activity`` -- significant ``AuditEvent`` rows, rate-limited
  to event types that matter to an Admin (criterion 6). Routine
  submissions / note edits are excluded.

The endpoint is gated by :class:`IsOrgAdminOrSuperuser` so a non-admin
JWT cannot reach it even if it knows the URL.
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Flag
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser
from bunk_logs.core.state_machine import OrderStateMachine

from .common import AdminContext
from .common import viewer_or_403

# Conservative defaults for the "stale" / "pending review" / "digest
# failures" thresholds. Each is overridable via ``Organization.settings``
# JSONField keys (Story 58) so an Admin can tighten / loosen without a
# code deploy. The defaults below match the wording in Story 54 c5 plus
# spec decisions captured in `docs/user_stories/08_admin/STORIES.md`.
DEFAULT_STALE_TICKET_DAYS = 3
DEFAULT_STALE_ORDER_DAYS = 3
UNRESOLVED_FLAG_DAYS = 7
PENDING_REVIEW_DAYS = 14
DIGEST_FAILURE_CONSECUTIVE = 3
TRANSLATION_FAILURE_LOOKBACK_HOURS = 24
TRANSLATION_FAILURE_MIN = 5

OPEN_STATUSES: tuple[str, ...] = (
    OrderStateMachine.NEW,
    OrderStateMachine.IN_PROGRESS,
)

# Recent activity feed: keep it to "an admin would want to know within
# the day" events. Routine submissions / per-note edits are excluded to
# avoid drowning the section.
SIGNIFICANT_EVENT_TYPES: tuple[str, ...] = (
    AuditEvent.EventType.CREATED,
    AuditEvent.EventType.DEACTIVATED,
    AuditEvent.EventType.REACTIVATED,
    AuditEvent.EventType.STATE_CHANGED,
    AuditEvent.EventType.OVERRIDE_EDIT,
    AuditEvent.EventType.OVERRIDE_CLOSE,
    AuditEvent.EventType.OVERRIDE_RESOLVE,
)
RECENT_ACTIVITY_LIMIT = 25
RECENT_ACTIVITY_LOOKBACK_DAYS = 7
ACTIVITY_CONTENT_FILTER = (
    "membership",
    "supervision",
    "reflection_template",
    "template_assignment",
    "order",
    "maintenance_ticket",
    "flag",
    "program",
    "person",
)


class AdminDashboardView(APIView):
    """Org snapshot + Attention required + Recent activity."""

    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        payload = {
            "today": ctx.today.isoformat(),
            "org": _org_header(ctx),
            "org_snapshot": _build_org_snapshot(ctx),
            "attention_required": _build_attention_required(ctx),
            "recent_activity": _build_recent_activity(ctx),
        }
        return Response(payload)


# ---------------------------------------------------------------------------
# Org header
# ---------------------------------------------------------------------------


def _org_header(ctx: AdminContext) -> dict:
    """Org name + active programs summary."""
    programs = list(
        Program.all_objects.filter(
            organization=ctx.organization, is_active=True,
        ).values("id", "name", "program_type", "start_date", "end_date"),
    )
    return {
        "id": ctx.organization.id,
        "name": ctx.organization.name,
        "slug": ctx.organization.slug,
        "active_programs": [
            {
                "id": p["id"],
                "name": p["name"],
                "program_type": p["program_type"],
                "start_date": p["start_date"].isoformat() if p["start_date"] else None,
                "end_date": p["end_date"].isoformat() if p["end_date"] else None,
            }
            for p in programs
        ],
    }


# ---------------------------------------------------------------------------
# Org snapshot (Story 54 c3)
# ---------------------------------------------------------------------------


def _build_org_snapshot(ctx: AdminContext) -> dict:
    """Counts an Admin glances at first thing.

    Memberships are grouped by role (active only) so the snapshot
    surfaces under-staffing without requiring an extra round trip.
    """
    org = ctx.organization

    active_people = Person.all_objects.filter(
        organization=org,
        memberships__is_active=True,
    ).distinct().count()

    role_counts = list(
        Membership.all_objects.filter(
            program__organization=org, is_active=True,
        )
        .values("role")
        .annotate(count=Count("id"))
        .order_by("role"),
    )

    open_cc_orders = Order.all_objects.filter(
        organization=org, status__in=OPEN_STATUSES,
    ).count()
    open_maint_tickets = MaintenanceTicket.all_objects.filter(
        organization=org, status__in=OPEN_STATUSES,
    ).count()
    active_flags = Flag.all_objects.filter(
        organization=org, status=Flag.Status.ACTIVE,
    ).count()

    return {
        "active_people": active_people,
        "memberships_by_role": [
            {"role": r["role"], "count": r["count"]} for r in role_counts
        ],
        "open_camper_care_orders": open_cc_orders,
        "open_maintenance_tickets": open_maint_tickets,
        "active_flags": active_flags,
        # Today's completion rate is computed once per role-flow via
        # their dashboard endpoints; the org-wide rollup is best left to
        # the per-role drill-downs and is intentionally omitted here to
        # keep this endpoint cheap. The frontend can fetch the
        # completion summary from the dashboards/coverage endpoint when
        # it wants the cross-role view.
    }


# ---------------------------------------------------------------------------
# Attention required (Story 54 c5)
# ---------------------------------------------------------------------------


def _build_attention_required(ctx: AdminContext) -> list[dict]:
    """Six conditions, ordered by severity then alphabetical card key."""
    org = ctx.organization
    org_settings = org.settings or {}
    today = ctx.today

    stale_ticket_days = _int_setting(
        org_settings, "stale_maintenance_ticket_days", DEFAULT_STALE_TICKET_DAYS,
    )
    stale_order_days = _int_setting(
        org_settings, "stale_camper_care_order_days", DEFAULT_STALE_ORDER_DAYS,
    )

    cutoff_ticket = today - timedelta(days=stale_ticket_days)
    cutoff_order = today - timedelta(days=stale_order_days)
    cutoff_flag = today - timedelta(days=UNRESOLVED_FLAG_DAYS)
    cutoff_template = timezone.now() - timedelta(days=PENDING_REVIEW_DAYS)

    stale_tickets = (
        MaintenanceTicket.all_objects.filter(
            organization=org,
            status__in=OPEN_STATUSES,
            created_at__date__lte=cutoff_ticket,
        ).count()
    )
    stale_orders = (
        Order.all_objects.filter(
            organization=org,
            status__in=OPEN_STATUSES,
            created_at__date__lte=cutoff_order,
        ).count()
    )
    unresolved_flags = (
        Flag.all_objects.filter(
            organization=org,
            status=Flag.Status.ACTIVE,
            created_at__date__lte=cutoff_flag,
        ).count()
    )
    pending_review = _pending_template_review_count(
        organization=org, cutoff=cutoff_template,
    )
    digest_failures = _digest_delivery_failure_count(org)
    translation_failures = _translation_failure_count(org)

    # Surface ALL six cards (zero counts included) so the UI can render
    # a stable layout; the frontend hides cards with zero counts if it
    # wants a compact view.
    return [
        {
            "key": "stale_maintenance_tickets",
            "label": "Stale Maintenance tickets",
            "count": stale_tickets,
            "threshold_days": stale_ticket_days,
            "deep_link": "/admin/operations/maintenance?filter=stale",
        },
        {
            "key": "stale_camper_care_orders",
            "label": "Stale Camper Care orders",
            "count": stale_orders,
            "threshold_days": stale_order_days,
            "deep_link": "/admin/operations/orders?filter=stale",
        },
        {
            "key": "unresolved_flags",
            "label": "Unresolved Camper Care flags",
            "count": unresolved_flags,
            "threshold_days": UNRESOLVED_FLAG_DAYS,
            "deep_link": "/admin/operations/flags?filter=stale",
        },
        {
            "key": "pending_template_review",
            "label": "Pending template review",
            "count": pending_review,
            "threshold_days": PENDING_REVIEW_DAYS,
            "deep_link": "/admin/templates?filter=pending_review",
        },
        {
            "key": "digest_delivery_failures",
            "label": "Digest delivery failures",
            "count": digest_failures,
            "threshold_days": DIGEST_FAILURE_CONSECUTIVE,
            "deep_link": "/admin/settings?tab=notifications",
        },
        {
            "key": "translation_pipeline_failures",
            "label": "Translation pipeline failures",
            "count": translation_failures,
            "threshold_days": 1,
            "deep_link": "/admin/operations/translations",
        },
    ]


def _int_setting(settings_dict: dict, key: str, fallback: int) -> int:
    raw = settings_dict.get(key)
    if isinstance(raw, bool):
        return fallback
    if isinstance(raw, int) and raw > 0:
        return raw
    return fallback


def _pending_template_review_count(*, organization, cutoff) -> int:
    """Templates published in the last N days that aren't yet marked reviewed.

    PR3 adds the ``ReflectionTemplate.metadata.review_status`` annotation
    flow (``reviewed`` / ``needs_revision``). We filter those out here so
    the dashboard badge only counts genuinely-stale rows. ``published_at``
    is the canonical recency anchor; templates without it (older rows
    pre-migration) fall back to ``created_at`` for backward compatibility.
    """
    base = ReflectionTemplate.all_objects.filter(
        organization=organization,
        status=ReflectionTemplate.Status.PUBLISHED,
    )
    candidates = base.filter(published_at__gte=cutoff) | base.filter(
        published_at__isnull=True, created_at__gte=cutoff,
    )
    # JSONField key lookups are Postgres-specific but we already require
    # Postgres for the rest of the admin search surface, so this is safe.
    return candidates.exclude(
        metadata__review_status__in=("reviewed", "needs_revision"),
    ).count()


def _digest_delivery_failure_count(organization) -> int:
    """Maintenance digest emails that failed 3+ days in a row.

    ``EmailLog`` is in the messaging app and is not org-scoped today
    (single recipient list per deploy), so this counts org-wide. The
    heuristic: any digest-named template that has 3 or more consecutive
    failures in the last 7 days surfaces as one card-worthy event.
    """
    try:
        from bunk_logs.messaging.models import EmailLog
    except ImportError:  # pragma: no cover - messaging app should always be installed
        return 0
    since = timezone.now() - timedelta(days=7)
    recent = list(
        EmailLog.objects.filter(
            sent_at__gte=since,
            subject__icontains="digest",
        )
        .order_by("-sent_at")
        .values_list("success", flat=True)[: DIGEST_FAILURE_CONSECUTIVE * 4],
    )
    if not recent:
        return 0
    consecutive_failures = 0
    for success in recent:
        if success:
            break
        consecutive_failures += 1
    return 1 if consecutive_failures >= DIGEST_FAILURE_CONSECUTIVE else 0


def _translation_failure_count(organization) -> int:
    """Terminal translation failures in the last 24h for this org."""
    try:
        from bunk_logs.core.models import TranslationRecord
    except ImportError:  # pragma: no cover
        return 0
    since = timezone.now() - timedelta(hours=TRANSLATION_FAILURE_LOOKBACK_HOURS)
    count = TranslationRecord.objects.filter(
        organization=organization,
        status=TranslationRecord.Status.FAILED_TERMINAL,
        created_at__gte=since,
    ).count()
    return count if count >= TRANSLATION_FAILURE_MIN else 0


# ---------------------------------------------------------------------------
# Recent activity feed (Story 54 c6)
# ---------------------------------------------------------------------------


def _build_recent_activity(ctx: AdminContext) -> list[dict]:
    """Latest significant audit events, rate-limited and deep-linked."""
    org = ctx.organization
    since = timezone.now() - timedelta(days=RECENT_ACTIVITY_LOOKBACK_DAYS)
    events = list(
        AuditEvent.all_objects.filter(
            organization=org,
            created_at__gte=since,
            event_type__in=SIGNIFICANT_EVENT_TYPES,
            content_type__in=ACTIVITY_CONTENT_FILTER,
        )
        .select_related("actor_membership__person")
        .order_by("-created_at")[: RECENT_ACTIVITY_LIMIT * 2],
    )

    out: list[dict] = []
    for e in events:
        if len(out) >= RECENT_ACTIVITY_LIMIT:
            break
        actor_name = _actor_display(e)
        out.append({
            "id": str(e.id),
            "event_type": e.event_type,
            "content_type": e.content_type,
            "content_id": e.content_id,
            "created_at": e.created_at.isoformat(),
            "actor": actor_name,
            "is_admin_override": e.is_admin_override,
            "deep_link": _deep_link_for(e),
            "summary": _summarize(e),
        })
    return out


def _actor_display(event: AuditEvent) -> str | None:
    membership = event.actor_membership
    if membership and membership.person:
        p = membership.person
        return (p.preferred_name or p.first_name or "") + " " + (p.last_name or "")
    return None


def _deep_link_for(event: AuditEvent) -> str:
    """Best-effort frontend path for a given audit row."""
    ct = event.content_type
    cid = event.content_id
    if ct in ("order",):
        return f"/admin/operations/orders/{cid}"
    if ct == "maintenance_ticket":
        return f"/admin/operations/maintenance/{cid}"
    if ct == "flag":
        return f"/admin/operations/flags/{cid}"
    if ct == "membership":
        return f"/admin/memberships/{cid}"
    if ct == "supervision":
        return f"/admin/assignments?supervision_id={cid}"
    if ct in ("reflection_template", "template_assignment"):
        return f"/admin/templates/{cid}"
    if ct == "person":
        return f"/admin/people/{cid}"
    return "/admin"


def _summarize(event: AuditEvent) -> str:
    ev = event.event_type
    ct = event.content_type.replace("_", " ").title()
    if ev == AuditEvent.EventType.STATE_CHANGED:
        before = (event.before_state or {}).get("status") or "?"
        after = (event.after_state or {}).get("status") or "?"
        return f"{ct}: {before} -> {after}"
    if ev == AuditEvent.EventType.CREATED:
        return f"{ct} created"
    if ev == AuditEvent.EventType.DEACTIVATED:
        return f"{ct} deactivated"
    if ev == AuditEvent.EventType.REACTIVATED:
        return f"{ct} reactivated"
    if ev == AuditEvent.EventType.OVERRIDE_EDIT:
        return f"Admin override: edited {ct}"
    if ev == AuditEvent.EventType.OVERRIDE_CLOSE:
        return f"Admin override: closed {ct}"
    if ev == AuditEvent.EventType.OVERRIDE_RESOLVE:
        return f"Admin override: resolved {ct}"
    return f"{ct} {ev}"
