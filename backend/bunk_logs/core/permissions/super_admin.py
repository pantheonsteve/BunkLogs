"""Canonical "Super Admin" gate for the new RBAC code.

A Super Admin is any authenticated user where ``is_staff`` OR ``is_superuser``
is true. Both flags grant the same bypass-all access (org-scoped reflection
visibility, org-admin endpoints, cross-tenant template / FieldKey
management). This unifies what was historically a ``is_superuser``-only
check on the new RBAC code with the ``is_staff``-based gate the legacy
single-tenant code (and the React frontend) already use.

If we ever need a stricter "platform superuser" tier -- say, "only Django
superusers can edit the global FieldKey registry" -- introduce a separate
helper named ``is_platform_superuser`` so the intent is obvious in code
review. Don't quietly split the two flags here.
"""
from __future__ import annotations


def is_super_admin(user) -> bool:
    """True for ``is_staff`` OR ``is_superuser`` authenticated users.

    Anonymous / unauthenticated / ``None`` users return False.
    Tolerant of duck-typed user objects: missing attributes are treated as
    False rather than raising.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return bool(
        getattr(user, "is_staff", False)
        or getattr(user, "is_superuser", False),
    )
