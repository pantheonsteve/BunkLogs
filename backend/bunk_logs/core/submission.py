"""Idempotent client-submission helpers for network-tolerant POST endpoints."""

from django.db import IntegrityError
from django.db import transaction


def idempotent_create(
    manager,
    *,
    program,
    client_submission_id,
    create_fn,
):
    """Insert via ``create_fn`` or return an existing row on replay/race.

    Lookup key is ``(program, client_submission_id)``. Concurrent duplicate
    POSTs that pass a pre-insert read both hit the unique constraint; we
    catch :class:`IntegrityError` and return the winner row with
    ``created=False`` instead of surfacing HTTP 500.

    ``create_fn`` runs inside ``transaction.atomic()`` and must return the
    saved model instance. Validation errors should raise, not return Response.
    """
    base = getattr(manager, "all_objects", manager)
    if not client_submission_id or program is None:
        with transaction.atomic():
            return create_fn(), True

    lookup = {"program": program, "client_submission_id": client_submission_id}
    existing = base.filter(**lookup).first()
    if existing is not None:
        return existing, False

    try:
        with transaction.atomic():
            return create_fn(), True
    except IntegrityError:
        existing = base.filter(**lookup).first()
        if existing is None:
            raise
        return existing, False
