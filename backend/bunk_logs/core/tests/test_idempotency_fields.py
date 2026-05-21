"""Tests for the ``client_submission_id`` idempotency fields (Step 7_6).

Story 7 criterion 6 / Story 8 criterion 4 require network-tolerant
submission. The contract is: the client generates a UUID per logical
submission and retries are safe because ``(program, client_submission_id)``
is unique. Multiple null ids are allowed (legacy / server-side rows).
"""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Order
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate


def _seed_org():
    org = Organization.objects.create(name="Camp Org", slug="camp")
    program = Program.all_objects.create(
        organization=org,
        name="Camp Org Summer 2026",
        slug="summer-2026",
        program_type="summer_camp",
        start_date="2026-06-01",
        end_date="2026-08-15",
    )
    return org, program


def _make_template(organization=None) -> ReflectionTemplate:
    return ReflectionTemplate.all_objects.create(
        organization=organization,
        name="Idempotency Test Template",
        slug=f"idem-test-{uuid4().hex[:8]}",
        cadence="daily",
        program_type="summer_camp",
        languages=["en"],
        schema={
            "fields": [
                {
                    "key": "day_off",
                    "type": "yes_no",
                    "prompts": {"en": "Day off?"},
                },
            ],
        },
    )


# ---------------------------------------------------------------------------
# Reflection
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reflection_client_submission_id_unique_per_program():
    org, program = _seed_org()
    template = _make_template()
    person = Person.all_objects.create(
        organization=org, first_name="A", last_name="Counselor",
    )
    submission_id = uuid4()
    Reflection.all_objects.create(
        organization=org,
        program=program,
        subject=person,
        author=person,
        template=template,
        period_start=date(2026, 7, 15),
        period_end=date(2026, 7, 15),
        answers={"day_off": True},
        client_submission_id=submission_id,
    )
    with pytest.raises(IntegrityError):
        Reflection.all_objects.create(
            organization=org,
            program=program,
            subject=person,
            author=person,
            template=template,
            period_start=date(2026, 7, 15),
            period_end=date(2026, 7, 15),
            answers={"day_off": True},
            client_submission_id=submission_id,
        )


@pytest.mark.django_db
def test_reflection_null_client_submission_id_allows_duplicates():
    org, program = _seed_org()
    template = _make_template()
    person = Person.all_objects.create(
        organization=org, first_name="A", last_name="Counselor",
    )
    for _ in range(2):
        Reflection.all_objects.create(
            organization=org,
            program=program,
            subject=person,
            author=person,
            template=template,
            period_start=date(2026, 7, 15),
            period_end=date(2026, 7, 15),
            answers={"day_off": True},
            client_submission_id=None,
        )
    assert Reflection.all_objects.filter(client_submission_id__isnull=True).count() == 2


# ---------------------------------------------------------------------------
# Order (camper-care request)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_order_client_submission_id_unique_per_program():
    org, program = _seed_org()
    submission_id = uuid4()
    Order.all_objects.create(
        organization=org,
        program=program,
        item="Toothbrush",
        client_submission_id=submission_id,
    )
    with pytest.raises(IntegrityError):
        Order.all_objects.create(
            organization=org,
            program=program,
            item="Toothbrush",
            client_submission_id=submission_id,
        )


@pytest.mark.django_db
def test_order_domain_fields_persist():
    org, program = _seed_org()
    row = Order.all_objects.create(
        organization=org,
        program=program,
        item="Sunscreen",
        item_note="Cabin 14 needs extra",
        description="Out of supply",
    )
    row.refresh_from_db()
    assert row.item == "Sunscreen"
    assert row.item_note == "Cabin 14 needs extra"
    assert row.description == "Out of supply"


# ---------------------------------------------------------------------------
# MaintenanceTicket
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_maintenance_ticket_client_submission_id_unique_per_program():
    org, program = _seed_org()
    submission_id = uuid4()
    MaintenanceTicket.all_objects.create(
        organization=org,
        program=program,
        location="Cabin 14",
        category=MaintenanceTicket.Category.PLUMBING,
        description="Clogged sink",
        urgency=MaintenanceTicket.Urgency.NORMAL,
        client_submission_id=submission_id,
    )
    with pytest.raises(IntegrityError):
        MaintenanceTicket.all_objects.create(
            organization=org,
            program=program,
            location="Cabin 14",
            category=MaintenanceTicket.Category.PLUMBING,
            description="Clogged sink",
            urgency=MaintenanceTicket.Urgency.NORMAL,
            client_submission_id=submission_id,
        )


@pytest.mark.django_db
def test_maintenance_ticket_urgent_requires_reason():
    org, program = _seed_org()
    ticket = MaintenanceTicket(
        organization=org,
        program=program,
        location="Cabin 14",
        category=MaintenanceTicket.Category.LEAK,
        description="Water everywhere",
        urgency=MaintenanceTicket.Urgency.URGENT,
        urgent_reason="",
    )
    with pytest.raises(ValidationError):
        ticket.full_clean()

    ticket.urgent_reason = "Ceiling leaking onto bunks"
    ticket.full_clean()
