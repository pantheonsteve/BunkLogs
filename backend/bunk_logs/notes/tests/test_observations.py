"""Tests for the converged Observation models (Step 7_23)."""

from __future__ import annotations

import pytest
from django.db import IntegrityError

from bunk_logs.core.models import Person
from bunk_logs.notes.models import Observation
from bunk_logs.notes.models import ObservationRecipient
from bunk_logs.notes.models import ObservationReply
from bunk_logs.notes.models import ObservationSubject

pytestmark = pytest.mark.django_db


@pytest.fixture
def camper(org):
    return Person.all_objects.create(organization=org, first_name="Cam", last_name="Per")


@pytest.fixture
def camper2(org):
    return Person.all_objects.create(organization=org, first_name="Dana", last_name="Two")


def _obs(org, program, author, **kwargs):
    return Observation.all_objects.create(
        organization=org,
        program=program,
        author=author,
        author_role_at_write=kwargs.pop("author_role_at_write", "counselor"),
        body=kwargs.pop("body", "Body text"),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class TestObservationModel:
    def test_create_defaults(self, org, program, counselor_person):
        obs = _obs(org, program, counselor_person)
        assert obs.pk is not None
        assert obs.sensitivity == Observation.Sensitivity.NORMAL
        assert obs.subject_visible is False
        assert obs.language == "en"

    def test_multi_subject_m2m(self, org, program, counselor_person, camper, camper2):
        obs = _obs(org, program, counselor_person)
        ObservationSubject.objects.create(observation=obs, subject=camper)
        ObservationSubject.objects.create(observation=obs, subject=camper2)
        subject_ids = set(
            ObservationSubject.objects.filter(observation=obs).values_list("subject_id", flat=True),
        )
        assert subject_ids == {camper.id, camper2.id}

    def test_subject_unique_together(self, org, program, counselor_person, camper):
        obs = _obs(org, program, counselor_person)
        ObservationSubject.objects.create(observation=obs, subject=camper)
        with pytest.raises(IntegrityError):
            ObservationSubject.objects.create(observation=obs, subject=camper)

    def test_amendment_chain(self, org, program, counselor_person):
        original = _obs(org, program, counselor_person, body="Original")
        amendment = _obs(org, program, counselor_person, body="Correction", amendment_of=original)
        assert amendment.amendment_of_id == original.pk
        assert list(Observation.all_objects.filter(amendment_of=original)) == [amendment]

    def test_legacy_source_partial_unique(self, org, program, counselor_person):
        _obs(org, program, counselor_person, legacy_source="core.subjectnote:1")
        with pytest.raises(IntegrityError):
            _obs(org, program, counselor_person, legacy_source="core.subjectnote:1")

    def test_legacy_source_blank_not_unique(self, org, program, counselor_person):
        # Two API-created observations (blank provenance) must coexist.
        _obs(org, program, counselor_person)
        _obs(org, program, counselor_person)
        assert Observation.all_objects.filter(legacy_source="").count() == 2

    def test_audit_content_type_label(self, org, program, counselor_person):
        obs = _obs(org, program, counselor_person)
        assert obs._audit_content_type_label() == "observation"


class TestObservationChildren:
    def test_recipient_unique(self, org, program, counselor_person, uh_person):
        obs = _obs(org, program, counselor_person)
        ObservationRecipient.objects.create(observation=obs, person=uh_person, option_key="my_unit_head")
        with pytest.raises(IntegrityError):
            ObservationRecipient.objects.create(observation=obs, person=uh_person)

    def test_reply_ordering(self, org, program, counselor_person, uh_person):
        obs = _obs(org, program, counselor_person)
        r1 = ObservationReply.objects.create(observation=obs, author=uh_person, author_role_at_write="unit_head", body="A")
        r2 = ObservationReply.objects.create(observation=obs, author=uh_person, author_role_at_write="unit_head", body="B")
        assert list(obs.replies.all()) == [r1, r2]
