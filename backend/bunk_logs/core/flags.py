"""Flag creation helpers (Step 7_8).

Thin module that consolidates the call-site contract for raising a
:class:`core.Flag` from another content row. Lives outside ``models.py``
so the model file stays focused on schema; the Specialist note flow
(Step 7_9) and any future role-flow that needs to flag a camper for
Camper Care imports from here.

Each helper writes an audit ``created`` event so the timeline on the
Camper Dashboard surfaces "flag raised" rows alongside state changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import Flag

if TYPE_CHECKING:
    from bunk_logs.core.models import Membership
    from bunk_logs.core.models import Note


def raise_flag_from_specialist_note(
    note: Note,
    *,
    raised_by: Membership | None = None,
    flagged_for_role: str = "camper_care",
) -> Flag:
    """Create an Active Camper-Care flag pointing at ``note``.

    Called by the Specialist note write endpoint (Step 7_9) when the
    submitter ticks the "flag for Camper Care" checkbox. The Specialist
    note must already be persisted (the helper does not infer subject /
    program from a transient instance) so the flag's
    ``trigger_content_id`` resolves cleanly.

    ``raised_by`` defaults to ``note.author``'s active Membership in the
    note's program -- callers may pass an explicit Membership when they
    already have one resolved.
    """
    if note.subject_id is None:
        msg = "Cannot raise a flag from a note without a subject camper."
        raise ValueError(msg)
    if note.program_id is None or note.organization_id is None:
        msg = "Note must be persisted with program + organization before flagging."
        raise ValueError(msg)

    membership = raised_by or _author_membership_for(note)

    with transaction.atomic():
        flag = Flag.all_objects.create(
            organization=note.organization,
            program=note.program,
            subject_camper=note.subject,
            raised_by_membership=membership,
            flagged_for_role=flagged_for_role,
            trigger_content_type="specialist_note",
            trigger_content_id=str(note.id),
            status=Flag.Status.ACTIVE,
        )
        audit_module.created(
            membership,
            flag,
            after_state={
                "subject_camper_id": flag.subject_camper_id,
                "flagged_for_role": flag.flagged_for_role,
                "trigger_content_type": flag.trigger_content_type,
                "trigger_content_id": flag.trigger_content_id,
                "status": flag.status,
            },
            content_type="flag",
        )
    return flag


def _author_membership_for(note: Note):
    """Best-effort active Membership for the note's author in the note's program."""
    from bunk_logs.core.models import Membership

    if note.author_id is None or note.program_id is None:
        return None
    return (
        Membership.all_objects.filter(
            person_id=note.author_id, program_id=note.program_id, is_active=True,
        )
        .order_by("-created_at")
        .first()
    )
