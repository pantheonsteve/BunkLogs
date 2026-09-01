"""Admin People + Membership management (Step 7_13 PR2, Story 55).

Endpoints under ``/api/v1/admin/``:

* ``GET    /people/``                          list + filter
* ``POST   /people/``                          create Person (with first Membership)
* ``GET    /people/<id>/``                     profile (identity + memberships + recent activity)
* ``PATCH  /people/<id>/``                     edit identity (audit'd)
* ``POST   /people/<id>/memberships/``         add Membership
* ``PATCH  /memberships/<id>/``                edit Membership role/dates/tags/grade
* ``POST   /memberships/<id>/deactivate/``     soft-deactivate
* ``POST   /people/<id>/invite/``              trigger invitation email (audited)

Design notes:

* All writes funnel through :mod:`bunk_logs.core.audit` so the action
  appears in the cross-cutting audit trail (Step 7_4). ``Membership``
  inherits audit content-type ``membership`` from its model name.
* Person email conflicts (Story 55 c9) return 409 with the existing
  Person + Memberships payload so the UI can offer "Add membership to
  the existing record" instead of forcing a duplicate.
* `Membership.role` is immutable post-create (capability derives from
  it; mutations would corrupt the RBAC layer). PATCH /memberships/<id>/
  silently ignores `role` and `capability`.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Trim
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit as audit_module
from bunk_logs.core.campminder_user_link import UserLinkAction
from bunk_logs.core.campminder_user_link import ensure_user_for_imported_person
from bunk_logs.core.models import SUBJECT_ROLES
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser
from bunk_logs.messaging.services.email_service import get_email_service

from .common import viewer_or_403

VALID_ROLES = frozenset(role for role, _ in Membership.ROLES)
RECENT_ACTIVITY_DAYS = 30

# "Who hasn't logged in yet?" is the most-asked question in September, so the
# three states are derived once here and reused by the list filter.
INVITE_NEVER = "never"
INVITE_INVITED = "invited"
INVITE_ACTIVE = "active"
INVITE_STATUSES = frozenset({INVITE_NEVER, INVITE_INVITED, INVITE_ACTIVE})

def invitable_people(organization):
    """Active people outside SUBJECT_ROLES -- who an invitation applies to."""
    return Person.all_objects.filter(
        organization=organization, memberships__is_active=True,
    ).exclude(memberships__role__in=SUBJECT_ROLES).distinct()


def by_invite_status(queryset, invite_status: str):
    """Narrow a Person queryset to one of the three invite states.

    Shared by the People list filter, the dashboard's setup card and the
    sidebar badge so all three agree on what "never invited" means.
    """
    signed_in = Q(user__isnull=False) & Q(user__last_login__isnull=False)
    if invite_status == INVITE_ACTIVE:
        return queryset.filter(signed_in)
    if invite_status == INVITE_INVITED:
        return queryset.exclude(signed_in).filter(invited_at__isnull=False)
    return queryset.exclude(signed_in).filter(invited_at__isnull=True)


# ---------------------------------------------------------------------------
# Serialisation helpers (lean, hand-rolled — no DRF serializer overhead)
# ---------------------------------------------------------------------------


def _invite_status(person: Person) -> str:
    """never invited -> invited but never signed in -> active.

    Signing in is the only proof an invitation landed, so ``last_login``
    outranks ``invited_at``: a person who was imported with a pre-existing
    login reads as active even though we never emailed them.
    """
    if person.user_id and getattr(person.user, "last_login", None):
        return INVITE_ACTIVE
    if person.invited_at:
        return INVITE_INVITED
    return INVITE_NEVER


def _serialize_membership(m: Membership) -> dict:
    return {
        "id": m.id,
        "program_id": m.program_id,
        "program_name": m.program.name if m.program_id else None,
        "role": m.role,
        "capability": m.capability,
        "grade_level": m.grade_level,
        "tags": m.tags or [],
        "start_date": m.start_date.isoformat() if m.start_date else None,
        "end_date": m.end_date.isoformat() if m.end_date else None,
        "is_active": m.is_active,
        "metadata": m.metadata or {},
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def _serialize_person(
    person: Person,
    *,
    include_memberships: bool = False,
    include_summary: bool = False,
) -> dict:
    payload: dict[str, Any] = {
        "id": person.id,
        "organization_id": person.organization_id,
        "first_name": person.first_name,
        "last_name": person.last_name,
        "preferred_name": person.preferred_name,
        "full_name": person.full_name,
        "email": person.email,
        "date_of_birth": person.date_of_birth.isoformat() if person.date_of_birth else None,
        "preferred_language": person.preferred_language,
        "translation_preference": person.translation_preference,
        "external_ids": person.external_ids or {},
        "has_user": person.user_id is not None,
        "user_id": person.user_id,
        "invite_status": _invite_status(person),
        "invited_at": person.invited_at.isoformat() if person.invited_at else None,
        "last_login": (
            person.user.last_login.isoformat()
            if person.user_id and person.user.last_login
            else None
        ),
        "created_at": person.created_at.isoformat() if person.created_at else None,
    }
    if include_summary:
        # Filtering by role you can't see is an act of faith, so list rows
        # carry the same facts the filters narrow on.
        payload["roles"] = sorted(
            {m.role for m in person.memberships.all() if m.is_active},
        )
        payload["groups"] = sorted(
            {
                gm.group.name
                for gm in person.assignment_group_memberships.all()
                if gm.is_active and gm.group.is_active
            },
        )
    if include_memberships:
        payload["memberships"] = [
            _serialize_membership(m)
            for m in Membership.all_objects.filter(person=person)
            .select_related("program")
            .order_by("-is_active", "-created_at")
        ]
    return payload


def _person_snapshot(person: Person) -> dict:
    return {
        "first_name": person.first_name,
        "last_name": person.last_name,
        "preferred_name": person.preferred_name,
        "email": person.email,
        "preferred_language": person.preferred_language,
        "translation_preference": person.translation_preference,
        "external_ids": person.external_ids or {},
        "date_of_birth": person.date_of_birth.isoformat() if person.date_of_birth else None,
    }


def _membership_snapshot(m: Membership) -> dict:
    return {
        "role": m.role,
        "capability": m.capability,
        "grade_level": m.grade_level,
        "tags": list(m.tags or []),
        "start_date": m.start_date.isoformat() if m.start_date else None,
        "end_date": m.end_date.isoformat() if m.end_date else None,
        "is_active": m.is_active,
        "metadata": dict(m.metadata or {}),
    }


def _resolve_program(ctx, program_id) -> Program | None:
    if program_id in (None, ""):
        return None
    try:
        return Program.all_objects.get(pk=program_id, organization=ctx.organization)
    except Program.DoesNotExist:
        return None


def _normalize_tags(values) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values or []:
        if v is None:
            continue
        t = str(v).strip().lower()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


# ---------------------------------------------------------------------------
# People list + create
# ---------------------------------------------------------------------------


class AdminPeopleListCreateView(APIView):
    """``GET`` list + ``POST`` create."""

    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        qs = Person.all_objects.filter(organization=ctx.organization)

        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = (
                qs.filter(last_name__icontains=search)
                | qs.filter(first_name__icontains=search)
                | qs.filter(preferred_name__icontains=search)
                | qs.filter(email__icontains=search)
            ).distinct()

        role = (request.query_params.get("role") or "").strip()
        if role:
            qs = qs.filter(memberships__role=role, memberships__is_active=True).distinct()

        program_id = (request.query_params.get("program") or "").strip()
        if program_id:
            qs = qs.filter(memberships__program_id=program_id).distinct()

        tag = (request.query_params.get("tag") or "").strip().lower()
        if tag:
            qs = qs.filter(memberships__tags__contains=[tag]).distinct()

        last_name_initial = (request.query_params.get("last_name_initial") or "").strip()
        if last_name_initial:
            letter = last_name_initial[0].upper()
            if letter.isalpha():
                qs = qs.annotate(_last_name_trim=Trim("last_name")).filter(
                    _last_name_trim__iregex=rf"^\s*{re.escape(letter)}",
                )

        status_filter = (request.query_params.get("status") or "").strip().lower()
        if status_filter == "active":
            qs = qs.filter(memberships__is_active=True).distinct()
        elif status_filter == "inactive":
            # Anyone whose every membership is deactivated.
            qs = qs.exclude(memberships__is_active=True).distinct()

        invite_status = (request.query_params.get("invite_status") or "").strip().lower()
        if invite_status in INVITE_STATUSES:
            # Subject roles are excluded so this list matches the count on the
            # sidebar badge that links here.
            qs = by_invite_status(
                qs.exclude(memberships__role__in=SUBJECT_ROLES).distinct(),
                invite_status,
            )

        qs = qs.select_related("user").prefetch_related(
            "memberships",
            "assignment_group_memberships__group",
        )
        qs = qs.order_by("last_name", "first_name")
        try:
            page_size = max(1, min(int(request.query_params.get("page_size", "100")), 500))
        except (TypeError, ValueError):
            page_size = 100
        try:
            offset = max(0, int(request.query_params.get("offset", "0")))
        except (TypeError, ValueError):
            offset = 0
        total = qs.count()
        items = list(qs[offset : offset + page_size])
        return Response({
            "count": total,
            "offset": offset,
            "page_size": page_size,
            "results": [_serialize_person(p, include_summary=True) for p in items],
        })

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        data = request.data or {}
        first_name = (data.get("first_name") or "").strip()
        last_name = (data.get("last_name") or "").strip()
        if not first_name or not last_name:
            return Response(
                {"detail": "first_name and last_name are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        email = (data.get("email") or "").strip()
        membership_payload = data.get("membership") or None
        if not isinstance(membership_payload, dict):
            return Response(
                {"detail": "A `membership` object is required to create a Person."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Email conflict (Story 55 c9).
        if email:
            existing = Person.all_objects.filter(
                organization=ctx.organization, email__iexact=email,
            ).first()
            if existing is not None:
                return Response(
                    {
                        "detail": "A Person with this email already exists in this org.",
                        "existing_person": _serialize_person(existing, include_memberships=True),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        # Resolve / validate program for the initial Membership.
        program = _resolve_program(ctx, membership_payload.get("program_id"))
        if program is None:
            return Response(
                {"detail": "Valid membership.program_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        role = (membership_payload.get("role") or "").strip()
        if role not in VALID_ROLES:
            return Response(
                {"detail": f"Unknown role {role!r}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        actor = ctx.membership or request.user
        with transaction.atomic():
            person = Person.all_objects.create(
                organization=ctx.organization,
                first_name=first_name,
                last_name=last_name,
                preferred_name=(data.get("preferred_name") or "").strip(),
                email=email,
                preferred_language=(data.get("preferred_language") or "en"),
                external_ids=data.get("external_ids") or {},
            )
            membership = Membership.all_objects.create(
                program=program,
                person=person,
                role=role,
                grade_level=membership_payload.get("grade_level"),
                tags=_normalize_tags(membership_payload.get("tags") or []),
                start_date=membership_payload.get("start_date") or None,
                end_date=membership_payload.get("end_date") or None,
                is_active=membership_payload.get("is_active", True),
                metadata=membership_payload.get("metadata") or {},
            )
            audit_module.created(
                actor, membership, after_state=_membership_snapshot(membership),
            )
            # Staff get a login provisioned automatically; subjects never do.
            if role not in SUBJECT_ROLES:
                ensure_user_for_imported_person(person, membership_role=role)
        return Response(
            _serialize_person(person, include_memberships=True),
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Person detail / patch
# ---------------------------------------------------------------------------


PERSON_PATCH_FIELDS = (
    "first_name",
    "last_name",
    "preferred_name",
    "email",
    "date_of_birth",
    "preferred_language",
    "translation_preference",
    "external_ids",
)


class AdminPeopleDetailView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, person_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        person = _get_person_or_404(ctx, person_id)
        if person is None:
            return _not_found("Person")
        payload = _serialize_person(person, include_memberships=True)
        payload["recent_activity"] = _recent_activity_for_person(ctx, person)
        return Response(payload)

    def patch(self, request, person_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        person = _get_person_or_404(ctx, person_id)
        if person is None:
            return _not_found("Person")
        before = _person_snapshot(person)
        changed: list[str] = []
        for field in PERSON_PATCH_FIELDS:
            if field not in request.data:
                continue
            value = request.data[field]
            if field == "email" and value:
                value = str(value).strip()
                # Conflict guard on email change.
                if value.lower() != (person.email or "").lower():
                    other = Person.all_objects.filter(
                        organization=ctx.organization, email__iexact=value,
                    ).exclude(pk=person.pk).first()
                    if other is not None:
                        return Response(
                            {"detail": "Another Person already has this email."},
                            status=status.HTTP_409_CONFLICT,
                        )
            current = getattr(person, field, None)
            if current == value:
                continue
            setattr(person, field, value)
            changed.append(field)
        if changed:
            person.save(update_fields=changed)
            actor = ctx.membership or request.user
            audit_module.edited(
                actor, person, before, _person_snapshot(person),
                content_type="person",
            )
        return Response(_serialize_person(person, include_memberships=True))


def _get_person_or_404(ctx, person_id) -> Person | None:
    try:
        return Person.all_objects.get(pk=person_id, organization=ctx.organization)
    except (Person.DoesNotExist, ValueError):
        return None


def _not_found(label: str) -> Response:
    return Response(
        {"detail": f"{label} not found in this org."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _recent_activity_for_person(ctx, person: Person) -> list[dict]:
    """Last 30 days of AuditEvent rows tied to this Person's content."""
    since = timezone.now() - timedelta(days=RECENT_ACTIVITY_DAYS)
    membership_ids = list(
        Membership.all_objects.filter(person=person).values_list("id", flat=True),
    )
    qs = AuditEvent.all_objects.filter(
        organization=ctx.organization, created_at__gte=since,
    ).filter(
        # Either the audit row's actor is this Person's Membership, or
        # the content row's PK matches this person/their membership.
        # The cross-cutting filter is intentionally loose; the goal is
        # the "Recent activity" tab feels useful, not exhaustive.
    )
    rows = list(
        qs.filter(
            actor_membership_id__in=membership_ids,
        ).order_by("-created_at")[:50],
    )
    # Plus events about Person's Memberships directly.
    membership_rows = list(
        AuditEvent.all_objects.filter(
            organization=ctx.organization,
            content_type="membership",
            content_id__in=[str(mid) for mid in membership_ids],
            created_at__gte=since,
        ).order_by("-created_at")[:50],
    )
    seen: set = set()
    combined: list[AuditEvent] = []
    for ev in [*rows, *membership_rows]:
        if ev.id in seen:
            continue
        seen.add(ev.id)
        combined.append(ev)
    combined.sort(key=lambda e: e.created_at, reverse=True)
    return [
        {
            "id": str(ev.id),
            "event_type": ev.event_type,
            "content_type": ev.content_type,
            "content_id": ev.content_id,
            "created_at": ev.created_at.isoformat(),
            "is_admin_override": ev.is_admin_override,
            "reason_note": ev.reason_note or "",
        }
        for ev in combined[:RECENT_ACTIVITY_DAYS]
    ]


# ---------------------------------------------------------------------------
# Person -> add Membership
# ---------------------------------------------------------------------------


class AdminPersonMembershipsView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def post(self, request, person_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        person = _get_person_or_404(ctx, person_id)
        if person is None:
            return _not_found("Person")
        program = _resolve_program(ctx, request.data.get("program_id"))
        if program is None:
            return Response(
                {"detail": "Valid program_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        role = (request.data.get("role") or "").strip()
        if role not in VALID_ROLES:
            return Response(
                {"detail": f"Unknown role {role!r}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Membership.all_objects.filter(
            program=program, person=person, role=role,
        ).exists():
            return Response(
                {"detail": "Person already has this (program, role) Membership."},
                status=status.HTTP_409_CONFLICT,
            )
        actor = ctx.membership or request.user
        with transaction.atomic():
            membership = Membership.all_objects.create(
                program=program,
                person=person,
                role=role,
                grade_level=request.data.get("grade_level"),
                tags=_normalize_tags(request.data.get("tags") or []),
                start_date=request.data.get("start_date") or None,
                end_date=request.data.get("end_date") or None,
                is_active=request.data.get("is_active", True),
                metadata=request.data.get("metadata") or {},
            )
            audit_module.created(
                actor, membership, after_state=_membership_snapshot(membership),
            )
        return Response(_serialize_membership(membership), status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Membership patch + deactivate
# ---------------------------------------------------------------------------


MEMBERSHIP_PATCH_FIELDS = (
    "grade_level",
    "tags",
    "start_date",
    "end_date",
    "is_active",
    "metadata",
)


class AdminMembershipDetailView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def patch(self, request, membership_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        membership = _get_membership_or_404(ctx, membership_id)
        if membership is None:
            return _not_found("Membership")
        before = _membership_snapshot(membership)
        changed: list[str] = []
        for field in MEMBERSHIP_PATCH_FIELDS:
            if field not in request.data:
                continue
            value = request.data[field]
            if field == "tags":
                value = _normalize_tags(value or [])
            current = getattr(membership, field, None)
            if current == value:
                continue
            setattr(membership, field, value)
            changed.append(field)
        if changed:
            membership.save(update_fields=changed)
            actor = ctx.membership or request.user
            audit_module.edited(
                actor, membership, before, _membership_snapshot(membership),
            )
        return Response(_serialize_membership(membership))


class AdminMembershipDeactivateView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def post(self, request, membership_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        membership = _get_membership_or_404(ctx, membership_id)
        if membership is None:
            return _not_found("Membership")
        reason = (request.data.get("reason") or "").strip()
        if membership.is_active is False:
            return Response(_serialize_membership(membership))
        before = _membership_snapshot(membership)
        membership.is_active = False
        if not membership.end_date:
            membership.end_date = ctx.today
        membership.save(update_fields=["is_active", "end_date"])
        actor = ctx.membership or request.user
        audit_module.deactivated(
            actor, membership,
            before_state=before, after_state=_membership_snapshot(membership),
            reason=reason,
        )
        return Response(_serialize_membership(membership))


def _get_membership_or_404(ctx, membership_id) -> Membership | None:
    try:
        return Membership.all_objects.select_related("program", "person").get(
            pk=membership_id, program__organization=ctx.organization,
        )
    except (Membership.DoesNotExist, ValueError):
        return None


# ---------------------------------------------------------------------------
# Invite
# ---------------------------------------------------------------------------


class InviteRefusedError(Exception):
    """A person who cannot be invited, with the reason to show the admin."""

    def __init__(self, detail: str, http_status: int):
        super().__init__(detail)
        self.detail = detail
        self.http_status = http_status


def _invite_person(ctx, person: Person, actor, *, scheduled: bool = False) -> bool:
    """Provision a login if needed, email the invitation, stamp ``invited_at``.

    Returns whether the email actually went out. Raises :class:`InviteRefusedError`
    for the states an admin has to fix first (no email, no staff membership,
    conflicting user account).

    ``invited_at`` is stamped even when delivery fails so a bounced invite
    still reads as "invited" rather than silently reverting to "never" — the
    admin has already spent the action and needs to see that.
    """
    if not person.email:
        msg = "Person has no email -- cannot send invitation."
        raise InviteRefusedError(msg, status.HTTP_400_BAD_REQUEST)

    staff_membership = (
        Membership.all_objects.filter(person=person, is_active=True)
        .exclude(role__in=SUBJECT_ROLES)
        .order_by("-created_at")
        .first()
    )
    if staff_membership is None:
        msg = "Person has no active staff membership -- cannot invite."
        raise InviteRefusedError(msg, status.HTTP_400_BAD_REQUEST)

    link = ensure_user_for_imported_person(person, membership_role=staff_membership.role)
    if link.action == UserLinkAction.CONFLICT:
        msg = f"Cannot provision login: {link.message}"
        raise InviteRefusedError(msg, status.HTTP_409_CONFLICT)

    org = ctx.organization
    context = {
        "person": person,
        "organization": org,
        "signin_url": f"https://{org.slug}.bunklogs.net/signin",
        "site_name": "BunkLogs",
    }
    sent = get_email_service().send_email(
        recipients=[person.email],
        subject=f"You're invited to {org.name} on BunkLogs",
        html_content=render_to_string("emails/person_invitation_en.html", context),
        text_content=render_to_string("emails/person_invitation_en.txt", context),
        template_name="person_invitation",
    )

    person.invited_at = timezone.now()
    person.save(update_fields=["invited_at"])

    audit_module.created(
        actor, person,
        after_state={
            "invitation_sent": sent,
            "recipient_email": person.email,
            "user_id": person.user_id,
            "user_link_action": link.action.value,
        },
        content_type="person_invitation",
        metadata={"channel": "email", "scheduled": scheduled},
    )
    return sent


class AdminPersonInviteView(APIView):
    """Provision a login (if needed) and send an invitation email for a Person.

    Ensures the Person has a linked User via the shared campminder link
    helper, then delivers the invitation through the messaging app's
    email service. The audit row records who invited whom and when.
    """

    permission_classes = [IsOrgAdminOrSuperuser]

    def post(self, request, person_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        person = _get_person_or_404(ctx, person_id)
        if person is None:
            return _not_found("Person")

        try:
            sent = _invite_person(
                ctx, person, ctx.membership or request.user,
                scheduled=bool(request.data.get("scheduled")),
            )
        except InviteRefusedError as refusal:
            return Response({"detail": refusal.detail}, status=refusal.http_status)

        if not sent:
            return Response(
                {"detail": "Login provisioned but the invitation email failed to send."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({
            "status": "sent",
            "recipient_email": person.email,
            "user_id": person.user_id,
        })


class AdminPeopleBulkInviteView(APIView):
    """Invite many people at once from a People-page selection.

    Partial success is the normal case — someone in the selection always
    lacks an email — so this reports per-person outcomes with 200 rather
    than failing the whole batch on the first refusal.
    """

    permission_classes = [IsOrgAdminOrSuperuser]

    MAX_BATCH = 200

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        raw_ids = request.data.get("person_ids")
        if not isinstance(raw_ids, list) or not raw_ids:
            return Response(
                {"detail": "person_ids must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(raw_ids) > self.MAX_BATCH:
            return Response(
                {"detail": f"At most {self.MAX_BATCH} people can be invited at once."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        people = {
            p.id: p
            for p in Person.all_objects.filter(
                organization=ctx.organization, id__in=raw_ids,
            )
        }
        actor = ctx.membership or request.user
        sent, skipped = [], []
        for raw_id in raw_ids:
            person = people.get(raw_id)
            if person is None:
                skipped.append({"person_id": raw_id, "reason": "Not found in this organization."})
                continue
            try:
                delivered = _invite_person(ctx, person, actor)
            except InviteRefusedError as refusal:
                skipped.append({
                    "person_id": person.id,
                    "name": person.full_name,
                    "reason": refusal.detail,
                })
                continue
            if delivered:
                sent.append({"person_id": person.id, "name": person.full_name})
            else:
                skipped.append({
                    "person_id": person.id,
                    "name": person.full_name,
                    "reason": "Invitation email failed to send.",
                })

        return Response({
            "sent_count": len(sent),
            "skipped_count": len(skipped),
            "sent": sent,
            "skipped": skipped,
        })
