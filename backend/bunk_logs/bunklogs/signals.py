"""Cross-app signals for the legacy ``bunklogs`` app.

Step 7_6g item 2: dual-write each ``StaffLog`` save into ``core.Reflection``.

We hang the dual-write off ``post_save`` rather than overriding
``StaffLog.save()`` so the legacy model stays untouched (per the
"deprecate, don't delete" policy in the migration prompts). The handler:

  * runs in the same transaction as the original save via
    ``transaction.on_commit`` so failures in the mapper never partially
    commit Reflection state for a save that itself rolled back;
  * is best-effort — any exception from the helper is logged at WARNING
    and swallowed so a missing template or membership doesn't break
    counselor-log writes (which Crane Lake operations depend on today);
  * is opt-out via ``settings.BUNKLOGS_DUAL_WRITE_REFLECTION = False``
    for environments where we want to disable the bridge (e.g. data
    migration scripts that import StaffLog rows but already populated
    Reflection directly).

Wiring lives in :mod:`bunk_logs.bunklogs.apps`. Don't import this module
from anywhere else.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from bunk_logs.bunklogs.models import StaffLog

log = logging.getLogger(__name__)


def _dual_write_enabled() -> bool:
    """Honour the kill-switch setting; default ON."""
    return getattr(settings, "BUNKLOGS_DUAL_WRITE_REFLECTION", True)


@receiver(post_save, sender=StaffLog, dispatch_uid="bunklogs.dual_write_reflection")
def dual_write_staff_log_to_reflection(sender, instance, **kwargs):
    """Mirror an inserted/updated ``StaffLog`` onto ``core.Reflection``.

    Note the importer-side guard: when an existing ``StaffLog`` is saved
    by the backfill command itself we don't want the signal to fire a
    second time. The backfill uses
    ``sync_staff_log_to_reflection`` directly without calling
    ``StaffLog.save()``, so that case is naturally avoided. If a future
    code path saves StaffLog inside the mapper, we'd need to wire a
    thread-local skip flag here.
    """
    if not _dual_write_enabled():
        return
    if instance is None or instance.pk is None:
        return

    # Import lazily so app loading doesn't import core.* before its app
    # registry is populated. ``ready()`` connects this receiver after
    # apps are loaded but the function body still executes lazily.
    from bunk_logs.api.counselor.legacy_mapping import sync_staff_log_to_reflection

    def _go():
        try:
            sync_staff_log_to_reflection(instance, emit_audit=True)
        except Exception:
            log.warning(
                "Dual-write StaffLog->Reflection failed for staff_log_id=%s",
                instance.pk,
                exc_info=True,
            )

    # Run on commit so a rolled-back StaffLog.save() doesn't leave a
    # mirrored Reflection behind. ``on_commit`` is a no-op outside of a
    # transaction (e.g. raw script use), which is also what we want.
    transaction.on_commit(_go)
