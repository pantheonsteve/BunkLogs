"""Read-only guard for the deprecated legacy camp models (strangler-fig step 6_1).

The single-tenant hierarchy (Session, Unit, Cabin, Bunk, UnitStaffAssignment,
CounselorBunkAssignment, Camper, CamperBunkAssignment, BunkLog, StaffLog and the
legacy ``orders`` app) is frozen. Crane Lake now runs on the multi-tenant ``core``
models; these tables remain readable for historical reporting but must not accept
new writes in production.

Enforcement is controlled by ``settings.BUNKLOGS_LEGACY_READ_ONLY`` (default False,
set True in production). This keeps local dev seeding, test fixtures, and one-off
migration/backfill commands working while blocking accidental writes in prod.

Note: bulk ``QuerySet.update()`` / ``QuerySet.delete()`` and FK cascade deletes
bypass ``Model.save()`` / ``Model.delete()`` by design, so operational tooling such
as ``scrub_pii`` and user-deletion cascades continue to function.
"""
from __future__ import annotations

from django.conf import settings


class LegacyModelReadOnlyError(RuntimeError):
    """Raised when code tries to write a deprecated legacy model in read-only mode."""


def legacy_writes_blocked() -> bool:
    return bool(getattr(settings, "BUNKLOGS_LEGACY_READ_ONLY", False))


def guard_legacy_write(instance: object) -> None:
    if legacy_writes_blocked():
        msg = (
            f"{type(instance).__name__} is a deprecated legacy model and is read-only. "
            "New data must be written to the multi-tenant core models."
        )
        raise LegacyModelReadOnlyError(msg)


class LegacyReadOnlyModelMixin:
    """Mixin for deprecated legacy models: blocks instance save/delete in read-only mode.

    Add as the first base class. Models with their own ``save()``/``delete()`` should
    also call :func:`guard_legacy_write` at the top so they fail fast.
    """

    def save(self, *args, **kwargs):
        guard_legacy_write(self)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        guard_legacy_write(self)
        return super().delete(*args, **kwargs)


class LegacyReadOnlyAdminMixin:
    """Admin mixin: renders deprecated legacy models as view-only.

    Add as the first base class of the ModelAdmin. Cooperates with admins whose
    own permission methods call ``super()`` first (they inherit the ``False``).
    """

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        return {}
