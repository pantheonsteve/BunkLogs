"""DRF filter backends for multi-tenant content APIs."""
from __future__ import annotations

from functools import reduce
from operator import or_

from django.contrib.auth import get_user_model
from django.db.models import F
from django.db.models import Q
from django.db.models import QuerySet
from rest_framework.filters import BaseFilterBackend

from bunk_logs.core.content_visibility import ContentType
from bunk_logs.core.content_visibility import MaintenanceNoteVisibility
from bunk_logs.core.content_visibility import reflection_content_type
from bunk_logs.core.content_visibility import reflection_is_private
from bunk_logs.core.content_visibility import viewer_can_read
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Note
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.permissions.visibility import is_org_admin
from bunk_logs.core.permissions.visibility import reflections_visible_to

User = get_user_model()


def _person_for_user(user) -> Person | None:
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return Person.all_objects.filter(user=user).first()


def _viewer_roles(person: Person, program_id: int | None = None) -> frozenset[str]:
    qs = Membership.all_objects.filter(person=person, is_active=True)
    if program_id is not None:
        qs = qs.filter(program_id=program_id)
    return frozenset(qs.values_list("role", flat=True))


def _supervised_subject_ids_for(person: Person, org_id: int) -> set[int]:
    """Camper Person IDs reachable from ``person``'s Supervision rows.

    Resolves both ``MEMBERSHIP`` and ``BUNK`` targets to the set of
    subject Persons rostered into the resulting bunks (today). Used by
    :func:`_note_visibility_q` so a UH can see non-sensitive notes
    about campers in their supervised bunks even though the
    role-audience table alone wouldn't add ``unit_head`` to the
    specialist-note audience.
    """
    from datetime import date as _date

    from bunk_logs.core.models import AssignmentGroupMembership as AGM_  # noqa: N814 — module-private alias
    from bunk_logs.core.models import Supervision

    today = _date.today()
    sups = Supervision.all_objects.filter(
        supervisor_membership__person=person,
        supervisor_membership__is_active=True,
        start_date__lte=today,
        supervisor_membership__program__organization_id=org_id,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))

    bunk_ids: set[int] = set()
    person_ids: set[int] = set()
    for s in sups.select_related("target_membership", "target_bunk").only(
        "target_type", "target_membership__person_id", "target_bunk_id",
    ):
        if s.target_type == "bunk" and s.target_bunk_id:
            bunk_ids.add(s.target_bunk_id)
        elif s.target_type == "membership" and s.target_membership_id:
            pid = getattr(s.target_membership, "person_id", None)
            if pid:
                person_ids.add(pid)

    if person_ids:
        # Persons supervised via Membership target -> their authored bunks.
        bunk_ids.update(
            AGM_.all_objects.filter(
                person_id__in=person_ids,
                role_in_group="author",
                is_active=True,
                group__is_active=True,
            ).values_list("group_id", flat=True),
        )

    if not bunk_ids:
        return set()

    return set(
        AGM_.all_objects.filter(
            group_id__in=bunk_ids,
            role_in_group="subject",
            is_active=True,
        ).values_list("person_id", flat=True),
    )


def _note_visibility_q(person: Person, org_id: int) -> Q | None:
    """Build OR-of-Q filter for notes visible to person (excludes author path)."""
    admin = is_org_admin(person) if person else False
    if admin:
        return Q(organization_id=org_id)

    parts: list[Q] = [Q(author=person)]
    programs = Membership.all_objects.filter(
        person=person, is_active=True, program__organization_id=org_id,
    ).values_list("program_id", flat=True).distinct()

    # Supervision-based visibility for non-sensitive specialist + camper-care
    # notes about subjects in the viewer's supervised bunks. Sensitive
    # variants still flow through the role-table check below.
    supervised_subject_ids = _supervised_subject_ids_for(person, org_id)
    if supervised_subject_ids:
        parts.append(Q(
            subject_id__in=supervised_subject_ids,
            note_type__in=(Note.NoteType.SPECIALIST, Note.NoteType.CAMPER_CARE),
            is_sensitive=False,
        ))

    for program_id in programs:
        roles = _viewer_roles(person, program_id)
        for note_type, sensitive in (
            (Note.NoteType.CAMPER_CARE, False),
            (Note.NoteType.CAMPER_CARE, True),
            (Note.NoteType.SPECIALIST, False),
            (Note.NoteType.SPECIALIST, True),
        ):
            ct = (
                ContentType.CAMPER_CARE_NOTE
                if note_type == Note.NoteType.CAMPER_CARE
                else ContentType.SPECIALIST_NOTE
            )
            if viewer_can_read(
                roles, ct, is_sensitive=sensitive, is_org_admin=False,
            ):
                parts.append(Q(
                    program_id=program_id,
                    note_type=note_type,
                    is_sensitive=sensitive,
                ))

        for mode in MaintenanceNoteVisibility:
            ct = ContentType.MAINTENANCE_TICKET_NOTE
            if viewer_can_read(
                roles, ct, maintenance_visibility=mode, is_org_admin=False,
            ):
                parts.append(Q(
                    program_id=program_id,
                    note_type=Note.NoteType.MAINTENANCE,
                    maintenance_visibility=mode.value,
                ))

    if len(parts) == 1:
        return parts[0]
    return reduce(or_, parts)


def notes_visible_to(
    user,
    queryset: QuerySet[Note] | None = None,
) -> QuerySet[Note]:
    if queryset is None:
        queryset = Note.objects.all()

    if user is None or not getattr(user, "is_authenticated", False):
        return queryset.none()

    person = _person_for_user(user)
    if person is None:
        return queryset.none()

    org_id = person.organization_id
    expr = _note_visibility_q(person, org_id)
    if expr is None:
        return queryset.none()
    return queryset.filter(organization_id=org_id).filter(expr).distinct()


def reflections_visible_for_user(
    user,
    queryset: QuerySet[Reflection] | None = None,
) -> QuerySet[Reflection]:
    """Full reflection visibility: assignment paths + content-type role table."""
    if queryset is None:
        queryset = Reflection.objects.all()
    return apply_reflection_content_visibility(
        user, reflections_visible_to(user, queryset),
    )


def apply_reflection_content_visibility(
    user,
    queryset: QuerySet[Reflection],
) -> QuerySet[Reflection]:
    """Layer table-based private/sensitive role gates on top of reflections_visible_to."""
    person = _person_for_user(user)
    if person is None or is_org_admin(user):
        return queryset

    # Private LT/Admin *self*-reflections (author == subject): admin-only audience.
    # Counselor-authored rows on an LT template keep normal supervisor visibility.
    if "admin" not in _viewer_roles(person):
        queryset = queryset.exclude(
            Q(
                template__subject_mode="self",
                template__role__in=("leadership_team", "admin"),
                team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
                author_id=F("subject_id"),
            )
            & ~Q(author=person),
        )

    # is_sensitive on reflections (specialist/camper-care shaped entries stored as reflections).
    sensitive_refs = queryset.filter(is_sensitive=True).exclude(author=person)
    if sensitive_refs.exists():
        to_hide: list[int] = []
        for ref in sensitive_refs.select_related("template", "program"):
            ct = reflection_content_type(ref)
            roles = _viewer_roles(person, ref.program_id)
            if not viewer_can_read(
                roles,
                ct,
                is_sensitive=True,
                is_private=reflection_is_private(ref),
                is_author=False,
                is_org_admin=False,
            ):
                to_hide.append(ref.pk)
        if to_hide:
            queryset = queryset.exclude(pk__in=to_hide)

    return queryset


class RoleVisibilityFilterBackend(BaseFilterBackend):
    """Filter content querysets by the requesting user's membership roles."""

    def filter_queryset(self, request, queryset, view):
        model = getattr(queryset, "model", None)
        if model is Reflection:
            qs = reflections_visible_to(request.user, queryset)
            return apply_reflection_content_visibility(request.user, qs)
        if model is Note:
            return notes_visible_to(request.user, queryset)
        return queryset
