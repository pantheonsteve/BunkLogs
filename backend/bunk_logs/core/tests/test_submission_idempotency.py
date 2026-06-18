"""Tests for idempotent_create race-safe submission helper."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.db import IntegrityError

from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.submission import idempotent_create


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Idem Camp", slug="idem-camp")


@pytest.fixture
def program(org):
    from datetime import date

    return Program.all_objects.create(
        organization=org,
        name="Idem Camp Summer 2026",
        slug="summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def template(org, program):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        program_type=program.program_type,
        name="Self",
        slug="counselor-self",
        schema={"fields": []},
        is_active=True,
    )


@pytest.mark.django_db
def test_idempotent_create_replay_returns_existing(program, org, template):
    csid = uuid.uuid4()
    today = program.start_date

    def _create():
        return Reflection.all_objects.create(
            organization=org,
            program=program,
            template=template,
            period_start=today,
            period_end=today,
            answers={},
            is_complete=True,
            client_submission_id=csid,
        )

    first, created_first = idempotent_create(
        Reflection, program=program, client_submission_id=csid, create_fn=_create,
    )
    second, created_second = idempotent_create(
        Reflection, program=program, client_submission_id=csid, create_fn=_create,
    )

    assert created_first is True
    assert created_second is False
    assert first.pk == second.pk
    assert Reflection.all_objects.filter(client_submission_id=csid).count() == 1


@pytest.mark.django_db
def test_idempotent_create_integrity_error_returns_existing(program, org, template):
    csid = uuid.uuid4()
    today = program.start_date
    existing = Reflection.all_objects.create(
        organization=org,
        program=program,
        template=template,
        period_start=today,
        period_end=today,
        answers={},
        is_complete=True,
        client_submission_id=csid,
    )

    def _raise_integrity():
        raise IntegrityError("duplicate key")

    with patch.object(Reflection.all_objects, "filter") as mock_filter:
        mock_qs = mock_filter.return_value
        mock_qs.first.side_effect = [None, existing]

        row, created = idempotent_create(
            Reflection,
            program=program,
            client_submission_id=csid,
            create_fn=_raise_integrity,
        )

    assert created is False
    assert row.pk == existing.pk
