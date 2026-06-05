"""Flag creation helpers (Step 7_8).

Raise ``core.Flag`` rows when upstream content requests Camper Care triage.
The flagged campers workspace and dashboard badges read these rows only;
group/bunk dashboards surface help requests directly from reflection
answers via :func:`camper_care_help_requested_camper_ids_from`.
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta
from typing import TYPE_CHECKING

from django.core.cache import cache

from bunk_logs.core.models import Flag
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection

if TYPE_CHECKING:
    from bunk_logs.core.models import Program


def _is_truthy_yes_no(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"yes", "true", "1"}
    return False


def reflection_requests_camper_care_help(reflection: Reflection) -> bool:
    """True when this reflection's answers request Camper Care help."""
    if not reflection.subject_id:
        return False
    answers = reflection.answers or {}
    if _is_truthy_yes_no(answers.get("request_camper_care_help")):
        return True
    schema = reflection.template.schema if reflection.template_id else {}
    for field in (schema or {}).get("fields") or []:
        if not isinstance(field, dict):
            continue
        if field.get("dashboard_role") != "help_request_camper_care":
            continue
        key = field.get("key")
        if isinstance(key, str) and _is_truthy_yes_no(answers.get(key)):
            return True
    return False


def _author_membership_for_reflection(reflection: Reflection) -> Membership | None:
    if not reflection.author_id:
        return None
    return (
        Membership.all_objects.filter(
            person_id=reflection.author_id,
            program_id=reflection.program_id,
            is_active=True,
        )
        .order_by("-created_at")
        .first()
    )


def raise_flag_from_camper_reflection(
    reflection: Reflection,
    *,
    raised_by_membership: Membership | None = None,
) -> Flag | None:
    """Create an ACTIVE CC flag for this reflection, idempotently.

    Returns ``None`` when the reflection does not request help. Reuses an
    existing active/followed-up flag for the same reflection trigger.
    """
    if not reflection_requests_camper_care_help(reflection):
        return None

    trigger_id = str(reflection.id)
    existing = (
        Flag.all_objects.filter(
            program_id=reflection.program_id,
            flagged_for_role="camper_care",
            trigger_content_type="reflection",
            trigger_content_id=trigger_id,
        )
        .order_by("-created_at")
        .first()
    )
    if existing is not None:
        if existing.status in (Flag.Status.ACTIVE, Flag.Status.FOLLOWED_UP):
            return existing
        # Resolved/reopened history stays tied to this reflection; do not
        # mint a duplicate ACTIVE row when the flags workspace re-syncs.
        return None

    raiser = raised_by_membership or _author_membership_for_reflection(reflection)
    flag = Flag.all_objects.create(
        organization_id=reflection.organization_id,
        program_id=reflection.program_id,
        subject_camper_id=reflection.subject_id,
        raised_by_membership=raiser,
        flagged_for_role="camper_care",
        trigger_content_type="reflection",
        trigger_content_id=trigger_id,
        status=Flag.Status.ACTIVE,
    )
    bust_camper_care_dashboard_cache_for_program(reflection.program, reflection.period_start)
    return flag


def sync_missing_camper_care_help_flags(
    *,
    program: Program,
    target_date: date | None = None,
    lookback_days: int = 30,
) -> int:
    """Backfill flags for completed reflections that requested Camper Care help.

    When ``target_date`` is set (dashboard date picker), only that camp day is
    scanned. When omitted (flags workspace), scans the last ``lookback_days``
    so older help requests still materialize as flags.

    Idempotent — safe to call on every Camper Care dashboard / flags load.
    """
    reflections = Reflection.all_objects.filter(
        program=program,
        is_complete=True,
        subject_id__isnull=False,
    )
    if target_date is not None:
        reflections = reflections.filter(
            period_start=target_date,
            period_end=target_date,
        )
    else:
        from bunk_logs.core.time_utils import get_today

        today = get_today(program.organization)
        reflections = reflections.filter(
            period_end__gte=today - timedelta(days=lookback_days),
            period_start__lte=today,
        )
    reflections = reflections.select_related("template", "author")

    created = 0
    for reflection in reflections:
        before_ids = set(
            Flag.all_objects.filter(
                program=program,
                trigger_content_type="reflection",
                trigger_content_id=str(reflection.id),
                flagged_for_role="camper_care",
                status__in=(Flag.Status.ACTIVE, Flag.Status.FOLLOWED_UP),
            ).values_list("id", flat=True),
        )
        flag = raise_flag_from_camper_reflection(reflection)
        if flag is not None and flag.id not in before_ids:
            created += 1
    return created


def active_flags_for_program_day(*, program: Program, target_date: date):
    """Unresolved CC flags whose trigger reflection is for ``target_date``.

    Dashboard date navigation is anchored to the camp day on the reflection,
    not the calendar day the ``Flag`` row was created (backfill may create
    flags a day after the reflection was submitted).
    """
    reflection_ids = Reflection.all_objects.filter(
        program=program,
        period_start=target_date,
        period_end=target_date,
    ).values_list("id", flat=True)
    trigger_ids = [str(rid) for rid in reflection_ids]
    if not trigger_ids:
        return Flag.objects.none()
    return Flag.objects.filter(
        program=program,
        flagged_for_role="camper_care",
        status__in=(Flag.Status.ACTIVE, Flag.Status.FOLLOWED_UP),
        trigger_content_type="reflection",
        trigger_content_id__in=trigger_ids,
    )


def flagged_camper_ids_for_date(
    *,
    program: Program,
    target_date: date,
    camper_ids: set[int] | None = None,
) -> set[int]:
    """Subject IDs with an unresolved CC flag for help requested on ``target_date``."""
    qs = active_flags_for_program_day(program=program, target_date=target_date)
    if camper_ids is not None:
        qs = qs.filter(subject_camper_id__in=camper_ids)
    return set(qs.values_list("subject_camper_id", flat=True))


def bust_camper_care_dashboard_cache_for_program(program: Program, target_date: date) -> None:
    """Invalidate cached CC dashboards after flag changes for ``target_date``."""
    org_id = program.organization_id
    person_ids = Membership.all_objects.filter(
        program=program, role="camper_care", is_active=True,
    ).values_list("person_id", flat=True)
    key_date = target_date.isoformat()
    for person_id in person_ids:
        cache.delete(f"camper_care_dashboard:{org_id}:{person_id}:{key_date}")
