"""Shared TemplateAssignment-aware resolution for per-role dashboards (Step 7_21).

What this module does
---------------------
Per-role ``common.py`` files used to query ``ReflectionTemplate`` directly
with hard-coded filters. After Step 7_21 those helpers delegate to
``resolve_template_for`` here, which finds the active
``TemplateAssignment`` whose template matches the requested
(subject_mode, cadence, role) shape. That makes "which template applies
to this dashboard" a configuration choice the Leadership Team can drive
instead of a code-baked default.

Why a separate module
---------------------
- Every role's dashboard now needs the same resolver; keeping it in one
  place prevents drift between roles.
- ``resolve_members`` (the LT API's audience materializer) lives here
  too so the assignments API and the dashboards share one source of
  truth.

Key invariant
-------------
The resolver returns ``None`` when no matching assignment is active —
callers must handle that (the legacy hard-coded helpers also could
return ``None``).
"""

from __future__ import annotations

from datetime import date  # noqa: TC003 — used in keyword-only annotations
from typing import TYPE_CHECKING

from django.db.models import Case
from django.db.models import IntegerField
from django.db.models import Q
from django.db.models import When

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import TemplateAssignment

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Person
    from bunk_logs.core.models import Program
    from bunk_logs.core.models import ReflectionTemplate


__all__ = [
    "active_assignments_for",
    "list_optional_assignments_for",
    "list_required_assignments_for",
    "resolve_members",
    "resolve_template_for",
]


_ACTIVE_STATUSES = (
    TemplateAssignment.Status.ACTIVE,
    TemplateAssignment.Status.SCHEDULED,
)


# ---------------------------------------------------------------------------
# Membership resolution (moved from api/leadership_team/assignments.py)
# ---------------------------------------------------------------------------


def resolve_members(assignment: TemplateAssignment, as_of: date):
    """Return the Memberships that an assignment applies to on ``as_of``.

    * ``role``: dynamic — current active Memberships in the program with
      that role.
    * ``individuals``: static snapshot from
      ``target_payload['membership_ids']``, filtered to currently active
      so a deactivated member silently drops.
    * ``tag_group``: dynamic — Memberships whose ``tags`` JSON contains
      the given tag.
    * ``assignment_group``: dynamic — Memberships whose role is in
      ``template.author_role_filter`` AND who are active authors in the
      group.
    """
    payload = assignment.target_payload or {}
    base = Membership.all_objects.filter(
        program=assignment.program, is_active=True,
    )
    target_type = assignment.target_type
    if target_type == TemplateAssignment.TargetType.ROLE:
        role = payload.get("role")
        return base.filter(role=role) if role else base.none()
    if target_type == TemplateAssignment.TargetType.INDIVIDUALS:
        ids = payload.get("membership_ids") or []
        if not isinstance(ids, list):
            return base.none()
        return base.filter(pk__in=ids)
    if target_type == TemplateAssignment.TargetType.TAG_GROUP:
        tag = payload.get("tag")
        if not tag:
            return base.none()
        return base.filter(tags__contains=[tag])
    if target_type == TemplateAssignment.TargetType.ASSIGNMENT_GROUP:
        group_id = assignment.assignment_group_id
        if not group_id:
            return base.none()
        author_roles = assignment.template.author_role_filter or []
        if not author_roles:
            return base.none()
        author_person_ids = AssignmentGroupMembership.all_objects.filter(
            group_id=group_id,
            role_in_group="author",
            is_active=True,
        ).values_list("person_id", flat=True)
        return base.filter(
            person_id__in=author_person_ids, role__in=author_roles,
        )
    return base.none()


# ---------------------------------------------------------------------------
# Active assignment filter (no template matching yet)
# ---------------------------------------------------------------------------


def _active_assignments_base_qs(
    *, organization: Organization, program: Program, as_of: date,
):
    """Active+in-window TemplateAssignment rows for (org, program) on ``as_of``.

    "Active" means ``status='active'`` OR a ``'scheduled'`` row whose
    ``start_date`` has been reached — both are treated as live so the
    LT can pre-stage an assignment that flips on automatically.
    """
    return TemplateAssignment.all_objects.filter(
        organization=organization,
        program=program,
        status__in=_ACTIVE_STATUSES,
        start_date__lte=as_of,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=as_of))


def _viewer_membership_ids(
    viewer: Person, program: Program, *, role: str | None = None,
) -> set[int]:
    qs = Membership.all_objects.filter(
        person=viewer, program=program, is_active=True,
    )
    if role:
        qs = qs.filter(role=role)
    return set(qs.values_list("id", flat=True))


def _viewer_in_audience(
    assignment: TemplateAssignment,
    viewer: Person,
    *,
    program: Program,
    target_role: str | None,
) -> bool:
    """Whether ``viewer`` falls inside an assignment's resolved audience.

    Mirrors the cases in ``resolve_members`` but answers a yes/no
    question for one Person without materializing the full queryset.
    When ``target_role`` is given, also requires the viewer to have an
    active Membership with that role in the program.
    """
    if target_role is not None:
        viewer_role_ids = _viewer_membership_ids(
            viewer, program, role=target_role,
        )
        if not viewer_role_ids:
            return False
    payload = assignment.target_payload or {}
    target_type = assignment.target_type
    if target_type == TemplateAssignment.TargetType.ROLE:
        role = payload.get("role")
        if not role:
            return False
        viewer_roles = set(
            Membership.all_objects.filter(
                person=viewer, program=program, is_active=True,
            ).values_list("role", flat=True),
        )
        return role in viewer_roles
    if target_type == TemplateAssignment.TargetType.INDIVIDUALS:
        ids = payload.get("membership_ids") or []
        if not isinstance(ids, list):
            return False
        viewer_membership_ids = _viewer_membership_ids(viewer, program)
        return any(int(i) in viewer_membership_ids for i in ids if i is not None)
    if target_type == TemplateAssignment.TargetType.TAG_GROUP:
        tag = payload.get("tag")
        if not tag:
            return False
        return Membership.all_objects.filter(
            person=viewer,
            program=program,
            is_active=True,
            tags__contains=[tag],
        ).exists()
    if target_type == TemplateAssignment.TargetType.ASSIGNMENT_GROUP:
        group_id = assignment.assignment_group_id
        if not group_id:
            return False
        author_roles = assignment.template.author_role_filter or []
        if not author_roles:
            return False
        return AssignmentGroupMembership.all_objects.filter(
            group_id=group_id,
            person=viewer,
            role_in_group="author",
            is_active=True,
        ).filter(
            Q(person__memberships__role__in=author_roles)
            & Q(person__memberships__program=program)
            & Q(person__memberships__is_active=True),
        ).exists()
    return False


def active_assignments_for(
    *,
    viewer: Person,
    organization: Organization,
    program: Program,
    as_of: date,
    target_role: str | None = None,
    target_assignment_group: AssignmentGroup | None = None,
    require_required: bool = True,
) -> list[TemplateAssignment]:
    """Return active TemplateAssignment rows for a viewer-in-context.

    Filters
    -------
    - status='active' OR ('scheduled' with start_date <= as_of)
    - start_date <= as_of <= end_date (end_date null is open-ended)
    - organization and program match
    - When ``target_role`` is set, restricts to assignments where:
        * target_type='role' and target_payload['role'] matches, OR
        * target_type='individuals' and the viewer's Membership is in
          target_payload['membership_ids'], OR
        * target_type='assignment_group' and the viewer is an author in
          that group whose role is in template.author_role_filter, OR
        * target_type='tag_group' and the viewer's Membership tags
          include the tag.
    - When ``require_required`` is True (default), drops is_required=False
      rows (those land in the Wave 2 optional-form library instead).
    """
    qs = _active_assignments_base_qs(
        organization=organization, program=program, as_of=as_of,
    ).select_related("template")
    if require_required:
        qs = qs.filter(is_required=True)
    if target_assignment_group is not None:
        qs = qs.filter(assignment_group=target_assignment_group)
    out: list[TemplateAssignment] = []
    for assignment in qs:
        if _viewer_in_audience(
            assignment, viewer, program=program, target_role=target_role,
        ):
            out.append(assignment)
    return out


def list_required_assignments_for(
    viewer: Person, organization: Organization, program: Program, as_of: date,
) -> list[TemplateAssignment]:
    """All required, active assignments where the viewer is in the audience."""
    return active_assignments_for(
        viewer=viewer,
        organization=organization,
        program=program,
        as_of=as_of,
        require_required=True,
    )


def list_optional_assignments_for(
    viewer: Person, organization: Organization, program: Program, as_of: date,
) -> list[TemplateAssignment]:
    """Optional (is_required=False), active assignments for the viewer.

    Wave 1 dashboards do not consume this list — it's exposed here for
    symmetry with the required side and is the seed for the Wave 2
    "forms I can also fill out" library.
    """
    qs = _active_assignments_base_qs(
        organization=organization, program=program, as_of=as_of,
    ).filter(is_required=False).select_related("template")
    out: list[TemplateAssignment] = []
    for assignment in qs:
        if _viewer_in_audience(
            assignment, viewer, program=program, target_role=None,
        ):
            out.append(assignment)
    return out


# ---------------------------------------------------------------------------
# Template resolution
# ---------------------------------------------------------------------------


def resolve_template_for(
    *,
    organization: Organization,
    program: Program,
    as_of: date,
    role: str,
    subject_mode: str,
    viewer: Person | None = None,
    cadence: str | None = None,
    assignment_group: AssignmentGroup | None = None,
) -> ReflectionTemplate | None:
    """Return the active ReflectionTemplate for a (role, subject_mode) tuple.

    Replaces the per-role hard-coded ``ReflectionTemplate.all_objects.filter(...)``
    helpers. The caller supplies the static template-shape requirements
    (``subject_mode``, optionally ``cadence``) and the resolver finds the
    ``TemplateAssignment`` whose template matches and whose date window
    contains ``as_of``.

    Parameters
    ----------
    organization, program, as_of
        Tenant context. Only assignments for this (org, program) on
        ``as_of`` are considered.
    role
        The AUTHOR role the template targets. An assignment qualifies
        when either ``template.role == role`` OR
        ``role in template.author_role_filter``. This is the canonical
        match used by every per-role helper.
    subject_mode
        Required match on ``template.subject_mode`` ("self",
        "single_subject", ...). Distinguishes a counselor's self
        template from the camper-reflection template they author.
    viewer
        Currently advisory only — kept in the signature for symmetry
        with ``active_assignments_for`` and so future call sites can
        narrow the resolution to "templates the viewer is in audience
        for" without breaking callers.
    cadence
        Optional cadence match. Compared against ``cadence_override``
        when set on the assignment, falling back to
        ``template.cadence``.
    assignment_group
        When provided, prefers assignments whose ``assignment_group``
        FK matches; falls back to program-wide (target_type='role')
        assignments when no group-specific row exists.

    Returns
    -------
    The matching ``ReflectionTemplate``, or ``None`` when no assignment
    is active. Callers MUST handle the ``None`` case — the legacy
    hard-coded helpers had the same contract.

    Notes
    -----
    Org-shadows-global resolution is preserved: when multiple
    assignments match, the one whose template's ``organization == organization``
    wins over a global (``organization IS NULL``) template, then the
    highest ``template.version`` breaks remaining ties.
    """
    del viewer  # reserved for forward-compat
    qs = _active_assignments_base_qs(
        organization=organization, program=program, as_of=as_of,
    ).filter(
        Q(template__role=role) | Q(template__author_role_filter__contains=[role]),
        template__subject_mode=subject_mode,
    ).select_related("template")
    if cadence is not None:
        qs = qs.filter(
            Q(cadence_override=cadence)
            | Q(cadence_override__isnull=True, template__cadence=cadence)
            | Q(cadence_override="", template__cadence=cadence),
        )
    if assignment_group is not None:
        # Prefer a group-specific assignment, but accept a program-wide
        # (target_type='role') fallback so an LT can ship a single role
        # assignment without per-bunk rows.
        qs = qs.filter(
            Q(assignment_group=assignment_group)
            | Q(
                assignment_group__isnull=True,
                target_type=TemplateAssignment.TargetType.ROLE,
            ),
        )
    qs = qs.annotate(
        _org_priority=Case(
            When(template__organization=organization, then=0),
            When(template__organization__isnull=True, then=1),
            default=2,
            output_field=IntegerField(),
        ),
        _group_priority=Case(
            When(assignment_group__isnull=False, then=0),
            default=1,
            output_field=IntegerField(),
        ),
    ).order_by("_org_priority", "_group_priority", "-template__version")
    assignment = qs.first()
    return assignment.template if assignment else None
