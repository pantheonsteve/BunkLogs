"""DRF filter backends for multi-tenant content APIs."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import F
from django.db.models import Q
from django.db.models import QuerySet
from rest_framework.filters import BaseFilterBackend

from bunk_logs.core.content_visibility import reflection_content_type
from bunk_logs.core.content_visibility import reflection_is_private
from bunk_logs.core.content_visibility import viewer_can_read
from bunk_logs.core.models import Membership
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
        return queryset
