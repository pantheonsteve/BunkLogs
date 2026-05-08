"""Permission helpers for the core multi-tenant API.

Re-exports the legacy DRF permission classes plus the visibility helper so
existing ``from bunk_logs.core.permissions import IsOrgAdminOrSuperuser`` style
imports keep working alongside the new ``visibility`` module.
"""

from bunk_logs.core.permissions.drf import IsOrgAdminOrSuperuser
from bunk_logs.core.permissions.drf import _is_org_admin
from bunk_logs.core.permissions.drf import _person_for_request
from bunk_logs.core.permissions.visibility import author_group_ids_with_descendants
from bunk_logs.core.permissions.visibility import has_supervisor_role
from bunk_logs.core.permissions.visibility import is_org_admin
from bunk_logs.core.permissions.visibility import reflections_visible_to

__all__ = [
    "IsOrgAdminOrSuperuser",
    "_is_org_admin",
    "_person_for_request",
    "author_group_ids_with_descendants",
    "has_supervisor_role",
    "is_org_admin",
    "reflections_visible_to",
]
