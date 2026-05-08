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
