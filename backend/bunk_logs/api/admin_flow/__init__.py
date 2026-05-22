"""Step 7_13 — Admin Flow API namespace.

Mounted at ``/api/v1/admin/`` (see :mod:`bunk_logs.api.urls`). Every view
here is gated by :class:`IsOrgAdminOrSuperuser` from
``bunk_logs.core.permissions`` so a regular operational role cannot reach
the admin surface even with a stolen JWT — the org-scoped membership
lookup still has to pass.

The module is named ``admin_flow`` (not ``admin``) to avoid colliding
with the long-standing :mod:`bunk_logs.api.admin` module that powers the
legacy Django-admin glue. Callers should never import from this package
directly; route discovery in ``api/urls.py`` is the only entry point.
"""
