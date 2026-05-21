from __future__ import annotations

from django.db import models
from django.db.models import Q

from bunk_logs.core.context import get_current_organization


class OrgScopedManager(models.Manager):
    """Default manager: tenant-scoped by ``organization`` FK. Fail-closed when no org context."""

    def get_queryset(self):
        org = get_current_organization()
        qs = super().get_queryset()
        if org is None:
            return qs.none()
        return qs.filter(organization=org)


class MembershipScopedManager(models.Manager):
    """Scope by program.organization (Membership has no direct organization FK)."""

    def get_queryset(self):
        org = get_current_organization()
        qs = super().get_queryset()
        if org is None:
            return qs.none()
        return qs.filter(program__organization=org)


class ProgramScopedManager(models.Manager):
    """Scope by program.organization for models that own a ``program`` FK but no direct ``organization`` FK.

    Same effective filter as :class:`MembershipScopedManager`; named for
    readability at the call sites. Use for ``OrderItemSuggestion`` and
    similar program-owned configuration tables.
    """

    def get_queryset(self):
        org = get_current_organization()
        qs = super().get_queryset()
        if org is None:
            return qs.none()
        return qs.filter(program__organization=org)


class ReflectionTemplateScopedManager(models.Manager):
    """Org-specific rows plus global templates (organization IS NULL)."""

    def get_queryset(self):
        org = get_current_organization()
        qs = super().get_queryset()
        if org is None:
            return qs.none()
        return qs.filter(Q(organization=org) | Q(organization__isnull=True))


class FieldKeyScopedManager(models.Manager):
    """Own-org keys plus global keys (organization IS NULL)."""

    def get_queryset(self):
        org = get_current_organization()
        qs = super().get_queryset()
        if org is None:
            return qs.none()
        return qs.filter(Q(organization=org) | Q(organization__isnull=True))


class AssignmentGroupMembershipScopedManager(models.Manager):
    """Scope by group.organization (AssignmentGroupMembership has no direct organization FK)."""

    def get_queryset(self):
        org = get_current_organization()
        qs = super().get_queryset()
        if org is None:
            return qs.none()
        return qs.filter(group__organization=org)


class SupervisionQuerySet(models.QuerySet):
    """QuerySet for ``core.Supervision`` with the four documented helpers.

    Each helper is a small, composable filter over a tenant-scoped queryset.
    Helpers call into ``all_objects`` for the supplementary reads they need
    (Memberships, AssignmentGroupMemberships) because callers already provide
    a Membership and we don't want to re-route through the request-context org
    filter twice.
    """

    def active(self, *, today=None):
        from django.utils import timezone

        ref = today or timezone.now().date()
        return self.filter(start_date__lte=ref).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=ref),
        )

    def for_supervisor(self, supervisor_membership):
        return self.filter(supervisor_membership=supervisor_membership)

    def bunks_for_uh(self, uh_membership, *, today=None):
        """Transitive: UH -> Counselors -> Bunks (AssignmentGroups).

        Returns the set of AssignmentGroup ids (group_type='bunk') the
        Counselor Persons supervised by ``uh_membership`` author in. The two
        intentional simplifications:

        * we only consider direct ``target_type=MEMBERSHIP`` supervisions
          (UH's never have BUNK / ROLE_IN_PROGRAM supervisions);
        * authorship is taken from ``AssignmentGroupMembership.role_in_group``
          rather than fanning out via Supervision rows for Counselor -> Bunk
          (Counselors aren't supervisors -- per spec they're direct
          assignments, not supervision rows).

        Pass ``today`` to evaluate against a specific date; defaults to the
        current date via ``django.utils.timezone``.
        """
        from bunk_logs.core.models import AssignmentGroup
        from bunk_logs.core.models import AssignmentGroupMembership

        counselor_membership_ids = list(
            self.active(today=today)
            .for_supervisor(uh_membership)
            .filter(target_type="membership", target_membership__isnull=False)
            .values_list("target_membership_id", flat=True),
        )
        if not counselor_membership_ids:
            return AssignmentGroup.all_objects.none()

        # The Membership FK only carries the role, not the Person -> we
        # resolve Persons via a Membership lookup, then their authoring
        # AssignmentGroupMemberships.
        from bunk_logs.core.models import Membership as _Membership

        counselor_person_ids = list(
            _Membership.all_objects.filter(
                pk__in=counselor_membership_ids,
            ).values_list("person_id", flat=True),
        )
        group_ids = AssignmentGroupMembership.all_objects.filter(
            person_id__in=counselor_person_ids,
            role_in_group="author",
            is_active=True,
            group__group_type="bunk",
            group__is_active=True,
        ).values_list("group_id", flat=True)
        return AssignmentGroup.all_objects.filter(
            pk__in=group_ids, is_active=True,
        ).distinct()

    def caseload_campers(self, camper_care_membership, *, today=None):
        """Camper Care -> caseload Bunks -> Campers (Persons).

        Returns the distinct set of Person rows who are 'subject' in any
        AssignmentGroup that this Camper Care Membership has an active BUNK
        Supervision against. Pass ``today`` to pin the active-on date.
        """
        from bunk_logs.core.models import AssignmentGroupMembership
        from bunk_logs.core.models import Person

        bunk_ids = list(
            self.active(today=today)
            .for_supervisor(camper_care_membership)
            .filter(target_type="bunk", target_bunk__isnull=False)
            .values_list("target_bunk_id", flat=True),
        )
        if not bunk_ids:
            return Person.all_objects.none()

        person_ids = AssignmentGroupMembership.all_objects.filter(
            group_id__in=bunk_ids,
            role_in_group="subject",
            is_active=True,
        ).values_list("person_id", flat=True)
        return Person.all_objects.filter(pk__in=person_ids).distinct()

    def team_members(self, supervisor_membership, target_role=None, *, today=None):
        """Role-in-program scope: Memberships matching ``target_role`` in any
        program the supervisor has an active ROLE_IN_PROGRAM Supervision for.

        Pass ``target_role`` to narrow to a single role; otherwise returns
        Memberships matching any role this supervisor has a role-in-program
        Supervision against. ``today`` pins the active-on date.
        """
        from bunk_logs.core.models import Membership as _Membership

        rows = (
            self.active(today=today)
            .for_supervisor(supervisor_membership)
            .filter(target_type="role_in_program")
            .values_list("target_role", "target_program_id")
        )
        pairs = [(r, p) for r, p in rows if r and p]
        if target_role is not None:
            pairs = [(r, p) for r, p in pairs if r == target_role]
        if not pairs:
            return _Membership.all_objects.none()

        from functools import reduce
        from operator import or_

        q = reduce(or_, [Q(role=r, program_id=p) for r, p in pairs])
        return _Membership.all_objects.filter(q, is_active=True).distinct()

    def co_supervisors(self, supervision, *, today=None):
        """Other active supervisions sharing the same target (excluding ``supervision``).

        ``supervision`` may be a Supervision instance or a dict-like with the
        target_type + target fields populated. Returns a queryset of
        Supervision rows. ``today`` pins the active-on date.
        """
        target_type = getattr(supervision, "target_type", None) or supervision.get("target_type")
        target_membership_id = (
            getattr(supervision, "target_membership_id", None)
            or (supervision.get("target_membership_id") if isinstance(supervision, dict) else None)
        )
        target_role = (
            getattr(supervision, "target_role", "")
            or (supervision.get("target_role", "") if isinstance(supervision, dict) else "")
        )
        target_program_id = (
            getattr(supervision, "target_program_id", None)
            or (supervision.get("target_program_id") if isinstance(supervision, dict) else None)
        )
        target_bunk_id = (
            getattr(supervision, "target_bunk_id", None)
            or (supervision.get("target_bunk_id") if isinstance(supervision, dict) else None)
        )

        qs = self.active(today=today).filter(target_type=target_type)
        if target_type == "membership":
            qs = qs.filter(target_membership_id=target_membership_id)
        elif target_type == "role_in_program":
            qs = qs.filter(target_role=target_role, target_program_id=target_program_id)
        elif target_type == "bunk":
            qs = qs.filter(target_bunk_id=target_bunk_id)
        else:
            return qs.none()

        own_pk = getattr(supervision, "pk", None)
        if own_pk is not None:
            qs = qs.exclude(pk=own_pk)
        return qs.distinct()


class SupervisionManager(models.Manager.from_queryset(SupervisionQuerySet)):
    """Tenant-scoped default manager for ``Supervision``.

    Scoped via ``supervisor_membership__program__organization`` to mirror the
    MembershipScopedManager pattern. Use ``Supervision.all_objects`` for
    admin / migration / cross-org reads.
    """

    def get_queryset(self):
        org = get_current_organization()
        qs = super().get_queryset()
        if org is None:
            return qs.none()
        return qs.filter(supervisor_membership__program__organization=org)


class SupervisionEventScopedManager(models.Manager):
    """Tenant-scoped manager for ``SupervisionEvent`` rows (direct org FK)."""

    def get_queryset(self):
        org = get_current_organization()
        qs = super().get_queryset()
        if org is None:
            return qs.none()
        return qs.filter(organization=org)


class AppendOnlyAuditEventQuerySet(models.QuerySet):
    """QuerySet that hard-blocks application-layer mutation of audit rows.

    Per the canonical spec (docs/user_stories/00_cross_cutting/audit_trail.md):
    audit events are write-only / append-only. ``update()`` and ``delete()``
    raise so ViewSets, shell users, and data-migration mistakes all surface
    immediately. Migrations that genuinely need to rewrite history must use
    raw SQL or ``_raw_update`` (see ``AuditEvent.objects.bulk_create`` for
    the documented escape hatch).
    """

    def update(self, **kwargs):
        msg = "AuditEvent rows are append-only; update() is not permitted."
        raise NotImplementedError(msg)

    def delete(self):
        msg = "AuditEvent rows are append-only; delete() is not permitted."
        raise NotImplementedError(msg)


class AuditEventScopedManager(models.Manager.from_queryset(AppendOnlyAuditEventQuerySet)):
    """Tenant-scoped, append-only default manager for ``core.AuditEvent``.

    Scopes by direct ``organization`` FK. ``AuditEvent.all_objects`` (a
    plain ``models.Manager``) preserves the cross-org bypass needed by
    platform-support / migrations, with the same append-only queryset
    methods applied -- see ``AuditEvent``.
    """

    def get_queryset(self):
        org = get_current_organization()
        qs = super().get_queryset()
        if org is None:
            return qs.none()
        return qs.filter(organization=org)


class AuditEventAllManager(models.Manager.from_queryset(AppendOnlyAuditEventQuerySet)):
    """Append-only cross-tenant manager. Use for migrations / platform support."""
