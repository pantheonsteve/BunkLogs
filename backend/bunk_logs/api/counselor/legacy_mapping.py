"""Legacy ``CounselorLog`` (a.k.a. ``StaffLog``) → ``core.Reflection`` mapping.

Step 7_6g shipping checklist item 1: dual-write + backfill. The legacy
``bunklogs.StaffLog`` table is Crane Lake's existing self-reflection
storage. The new multi-tenant counselor flow (steps 7_6a — 7_6f) writes
to ``core.Reflection`` with the seeded ``counselor-self-reflection``
template (migration 0029). Until the legacy admin/UI is fully retired
we want both stores in sync so:

  * the new dashboards (``/counselor`` and the role dashboards) see
    today's submission even when a counselor still writes via the
    legacy admin or an in-flight branch of the old form, and
  * Crane Lake's pre-7_6 history is queryable via the new
    ``GET /counselor/self-reflection/history/`` view from day one.

Both directions converge on the same helper below so the deterministic
``client_submission_id`` UUID5 derivation is shared. That key is what
gives us idempotency across re-runs of the backfill and across signal
firings caused by ``StaffLog.save()`` happening more than once
(e.g. when the legacy admin re-saves the same row).

Field mapping decisions
-----------------------

The seeded counselor-self-reflection schema only declares five fields
(``day_off``, ``overall_day``, ``wins``, ``improvements``, ``concern``)
while the legacy ``StaffLog`` row carries eight (the five core ones plus
``support_level_score``, ``values_reflection``, ``staff_care_support_needed``).
The validator only checks fields that appear in the schema; extra keys
in ``answers`` are kept on the row. We exploit that to lossy-map without
data loss:

  ``day_off``                  → ``answers.day_off`` (direct bool)
  ``day_quality_score``        → ``answers.overall_day`` (direct int 1-5)
  ``elaboration``              → ``answers.concern`` (free text)
  ``wins``, ``improvements``   → empty lists (legacy form didn't ask)
  ``support_level_score``      → ``answers.support_level_score`` (extra key)
  ``values_reflection``        → ``answers.values_reflection`` (extra key)
  ``staff_care_support_needed``→ ``answers.staff_care_support_needed`` (extra key)
  ``staff_log_id``             → ``answers._legacy_staff_log_id`` (provenance)

The "extra key" surfaces are NOT rendered by the new mobile form
(``ReflectionField`` only iterates schema fields) but they ARE preserved
in storage, exported by the admin/audit JSON, and recoverable by the
backfill itself for inspection. That mirrors the "deprecate, don't
delete" pattern we used in earlier migrations (see 6_1).

Skip semantics
--------------

We skip without raising when:

  * ``staff_member`` has no ``Person`` row (unmigrated staff member).
  * The viewer has no active ``counselor``/``junior_counselor``
    Membership (kitchen / leadership logs are handled by future steps).
  * The org doesn't have a counselor-self-reflection template resolved
    by ``counselor_self_template()`` (test fixtures often skip the
    seed migration; production always has it).

Skip-with-reason is logged at INFO so an operator running the backfill
can see why a row was passed over without crashing the bulk run.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db import transaction

from bunk_logs.core import audit as audit_module
from bunk_logs.core.context import organization_context
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import reflection_snapshot

from .common import counselor_self_template

if TYPE_CHECKING:
    from bunk_logs.bunklogs.models import StaffLog
    from bunk_logs.core.models import ReflectionTemplate

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Deterministic client_submission_id derivation
# ---------------------------------------------------------------------------

# Fixed namespace UUID — only used as the seed for ``uuid.uuid5()`` to
# produce stable derived UUIDs. Choosing a hand-picked UUID rather than
# ``uuid.NAMESPACE_OID`` is intentional: anyone grepping the codebase
# for this constant will land here and understand its purpose.
_BACKFILL_NAMESPACE = uuid.UUID("7e1f0007-0000-0000-0000-000000000007")


def client_submission_id_for_staff_log(staff_log_id: int) -> uuid.UUID:
    """Return the stable ``client_submission_id`` for a legacy log row.

    The same ``staff_log_id`` always yields the same UUID, so backfill
    re-runs (or a backfill followed by a stray ``StaffLog.save()`` that
    fires the dual-write signal) deduplicate via the existing
    ``(program, client_submission_id)`` unique constraint instead of
    creating a duplicate Reflection.
    """
    return uuid.uuid5(_BACKFILL_NAMESPACE, f"stafflog:{int(staff_log_id)}")


# ---------------------------------------------------------------------------
# Mapping shape + result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyncResult:
    """What happened when we tried to sync a single ``StaffLog``.

    * ``action`` is the user-facing summary verb: ``"created"``,
      ``"updated"``, ``"unchanged"``, or ``"skipped"``.
    * ``reason`` is set only on ``"skipped"`` so operators have a hint
      in the management-command summary.
    * ``reflection_id`` is the matching ``Reflection.id`` when known
      (always present on created/updated/unchanged).
    """

    action: str
    reason: str = ""
    reflection_id: int | None = None


def _answers_from_staff_log(log_row: StaffLog) -> dict:
    """Project ``StaffLog`` fields onto the seeded counselor template answers."""
    return {
        # Schema-recognised keys: rendered by the new mobile form.
        "day_off": bool(log_row.day_off),
        "overall_day": int(log_row.day_quality_score)
        if log_row.day_quality_score is not None else 0,
        "wins": [],
        "improvements": [],
        "concern": log_row.elaboration or "",
        # Extra keys: not rendered, but preserved for audit + recovery.
        "support_level_score": int(log_row.support_level_score)
        if log_row.support_level_score is not None else None,
        "values_reflection": log_row.values_reflection or "",
        "staff_care_support_needed": bool(log_row.staff_care_support_needed),
        # Provenance.
        "_legacy_staff_log_id": int(log_row.id),
    }


def _resolve_person_and_membership(
    user_id: int,
) -> tuple[Person | None, Membership | None]:
    """Return the viewer's ``Person`` + best counselor ``Membership`` if any.

    "Best" = active ``counselor`` or ``junior_counselor`` Membership,
    newest-first. We do NOT scope by organization slug — legacy
    StaffLog rows don't carry an org, and Crane Lake is the only
    Reflection-emitting tenant for now. If a person ever ends up with
    multiple counselor memberships across orgs, we'd need to revisit.
    """
    person = Person.all_objects.filter(user_id=user_id).first()
    if person is None:
        return None, None
    membership = (
        Membership.all_objects.filter(
            person=person,
            role__in=("counselor", "junior_counselor"),
            is_active=True,
        )
        .select_related("program", "person", "program__organization")
        .order_by("-created_at")
        .first()
    )
    return person, membership


def _resolve_template(
    person: Person, membership: Membership,
) -> ReflectionTemplate | None:
    """Look up the counselor self-reflection template for this person.

    Delegates to :func:`counselor_self_template` so the same resolver
    rules (org-scoped shadowing the global seed) apply. The helper
    internally hits ``Membership.objects`` which is org-scoped via
    :class:`MembershipScopedManager`; the legacy bridge runs outside
    of a request context, so we set the organization explicitly to
    make the scoped manager return real rows. Returns ``None`` when no
    template is configured at all.
    """
    org = membership.program.organization
    program = membership.program
    with organization_context(org):
        return counselor_self_template(person, org, program)


# ---------------------------------------------------------------------------
# Main entry point: idempotent upsert
# ---------------------------------------------------------------------------


def sync_staff_log_to_reflection(
    log_row: StaffLog, *, emit_audit: bool = True,
) -> SyncResult:
    """Idempotently mirror a ``StaffLog`` row onto a ``core.Reflection``.

    Returns a :class:`SyncResult` describing the outcome:

      * **created**: no prior Reflection — inserted a new row.
      * **updated**: a prior Reflection existed (matched by deterministic
        ``client_submission_id``) and its answers/day-off state differed;
        the row was rewritten in place with the new payload.
      * **unchanged**: a prior Reflection existed and was already in
        sync; no DB write.
      * **skipped**: pre-conditions weren't met (see the ``reason``
        field). Common in test fixtures that don't seed Person rows for
        legacy User accounts.

    ``emit_audit=True`` (default) logs the edit through the existing
    audit pipeline so the dashboard's "Edited by" attribution stays
    accurate. The signal path also defaults to True so any spurious
    background write shows up as audited.
    """
    person, membership = _resolve_person_and_membership(log_row.staff_member_id)
    if person is None:
        return SyncResult(
            action="skipped", reason="no_person_for_user",
        )
    if membership is None or membership.program is None:
        return SyncResult(
            action="skipped", reason="no_active_counselor_membership",
        )

    template = _resolve_template(person, membership)
    if template is None:
        return SyncResult(
            action="skipped", reason="no_counselor_template_configured",
        )

    csid = client_submission_id_for_staff_log(log_row.id)
    answers = _answers_from_staff_log(log_row)
    org = membership.program.organization
    program = membership.program

    with transaction.atomic():
        existing = (
            Reflection.all_objects.select_for_update()
            .filter(program=program, client_submission_id=csid)
            .first()
        )
        if existing is not None:
            # Same payload? Bail without a write so we don't churn the
            # ``updated_at`` timestamp on every backfill re-run.
            if (
                existing.answers == answers
                and existing.period_start == log_row.date
                and existing.period_end == log_row.date
                and existing.language == "en"
            ):
                return SyncResult(
                    action="unchanged", reflection_id=existing.id,
                )
            before = reflection_snapshot(existing)
            existing.answers = answers
            existing.period_start = log_row.date
            existing.period_end = log_row.date
            existing.language = "en"
            existing.team_visibility = Reflection.TeamVisibility.TEAM
            existing.is_complete = True
            existing.save()
            after = reflection_snapshot(existing)
            if emit_audit and before != after:
                audit_module.edited(
                    membership, existing, before, after,
                    content_type="reflection",
                )
            return SyncResult(
                action="updated", reflection_id=existing.id,
            )

        # Brand-new mirror — emit a "created" audit event so the new
        # dashboards show the row with proper attribution.
        reflection = Reflection.all_objects.create(
            organization=org,
            program=program,
            subject=person,
            author=person,
            assignment_group=None,
            template=template,
            submitted_by=log_row.staff_member,
            period_start=log_row.date,
            period_end=log_row.date,
            answers=answers,
            language="en",
            team_visibility=Reflection.TeamVisibility.TEAM,
            is_complete=True,
            client_submission_id=csid,
        )
        if emit_audit:
            audit_module.created(
                membership, reflection,
                after_state=reflection_snapshot(reflection),
                content_type="reflection",
            )
        return SyncResult(
            action="created", reflection_id=reflection.id,
        )
