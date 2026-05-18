"""Reusable DRF permission classes for the core multi-tenant API."""
from __future__ import annotations

from rest_framework import permissions

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.permissions.super_admin import is_super_admin


def _person_for_request(request) -> Person | None:
    if not getattr(request, "organization", None) or not request.user.is_authenticated:
        return None
    return Person.objects.filter(user=request.user).first()


def _is_org_admin(person: Person | None) -> bool:
    if person is None:
        return False
    return Membership.objects.filter(person=person, role="admin", is_active=True).exists()


class IsOrgAdminOrSuperuser(permissions.BasePermission):
    """Allow access only to org admins (active admin Membership) or Super Admins.

    "Super Admin" is the BunkLogs-wide concept of ``is_staff`` OR
    ``is_superuser`` -- see ``bunk_logs.core.permissions.is_super_admin``.
    The class name keeps the legacy ``Superuser`` suffix so downstream
    imports don't churn, but the gate it implements is the broader one.

    Requires an organization context on the request (set by the
    multi-tenant middleware) and an authenticated user.
    """

    message = "Organization admin membership or Super Admin status required."

    def has_permission(self, request, view):
        if not (
            request.user
            and request.user.is_authenticated
            and getattr(request, "organization", None)
        ):
            return False
        if is_super_admin(request.user):
            return True
        return _is_org_admin(_person_for_request(request))

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
