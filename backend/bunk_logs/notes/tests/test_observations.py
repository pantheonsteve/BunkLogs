"""Tests for the converged Observation models + migrate_observations command (Step 7_23).

Covers model constraints, multi-subject M2M, amendment chains, and the data
migration (per-source counts, sensitivity mapping, dry-run is a no-op,
idempotent re-run, peer notes exported-not-migrated).
"""

from __future__ import annotations

import json

import pytest
from django.core.management import call_command
from django.db import IntegrityError

from bunk_logs.core.models import Note as CoreNote
from bunk_logs.core.models import Person
from bunk_logs.core.models import SubjectNote
from bunk_logs.notes.models import Note as PlatformNote
from bunk_logs.notes.models import NoteAudienceCapture
from bunk_logs.notes.models import NoteReply
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


# ---------------------------------------------------------------------------
# migrate_observations command
# ---------------------------------------------------------------------------
def _subject_note(org, program, author, subject, **kwargs):
    return SubjectNote.all_objects.create(
        organization=org, program=program, author_person=author, subject=subject,
        body=kwargs.pop("body", "snote body"), **kwargs,
    )


def _core_note(org, program, author, subject, note_type, **kwargs):
    return CoreNote.all_objects.create(
        organization=org, program=program, author=author, subject=subject,
        note_type=note_type, body=kwargs.pop("body", "core note body"), **kwargs,
    )


class TestMigrateObservationsDryRun:
    def test_dry_run_writes_nothing(self, org, program, counselor_person, camper):
        _subject_note(org, program, counselor_person, camper)
        call_command("migrate_observations")
        assert Observation.all_objects.count() == 0


class TestMigrateSubjectNotes:
    def test_basic_conversion(self, org, program, counselor_person, camper):
        sn = _subject_note(
            org, program, counselor_person, camper,
            context="swim", visibility="domain_only", subject_visible=True,
        )
        call_command("migrate_observations", apply=True)
        obs = Observation.all_objects.get(legacy_source=f"core.subjectnote:{sn.pk}")
        assert obs.sensitivity == Observation.Sensitivity.DOMAIN
        assert obs.context == "swim"
        assert obs.subject_visible is True
        assert list(ObservationSubject.objects.filter(observation=obs).values_list("subject_id", flat=True)) == [camper.id]
        assert obs.created_at == sn.created_at

    @pytest.mark.parametrize(
        ("visibility", "is_sensitive", "expected"),
        [
            ("team", False, Observation.Sensitivity.NORMAL),
            ("supervisors_only", False, Observation.Sensitivity.SENSITIVE),
            ("domain_only", False, Observation.Sensitivity.DOMAIN),
            ("admin_only", False, Observation.Sensitivity.CONFIDENTIAL),
            ("team", True, Observation.Sensitivity.SENSITIVE),  # clamp up
        ],
    )
    def test_sensitivity_mapping(self, org, program, counselor_person, camper, visibility, is_sensitive, expected):
        sn = _subject_note(org, program, counselor_person, camper, visibility=visibility, is_sensitive=is_sensitive)
        call_command("migrate_observations", apply=True)
        obs = Observation.all_objects.get(legacy_source=f"core.subjectnote:{sn.pk}")
        assert obs.sensitivity == expected

    def test_amendment_chain_preserved(self, org, program, counselor_person, camper):
        original = _subject_note(org, program, counselor_person, camper, body="orig")
        amendment = _subject_note(org, program, counselor_person, camper, body="fix", amendment_of=original)
        call_command("migrate_observations", apply=True)
        obs_orig = Observation.all_objects.get(legacy_source=f"core.subjectnote:{original.pk}")
        obs_amend = Observation.all_objects.get(legacy_source=f"core.subjectnote:{amendment.pk}")
        assert obs_amend.amendment_of_id == obs_orig.pk

    def test_idempotent_rerun(self, org, program, counselor_person, camper):
        _subject_note(org, program, counselor_person, camper)
        call_command("migrate_observations", apply=True)
        call_command("migrate_observations", apply=True)
        assert Observation.all_objects.count() == 1
        assert ObservationSubject.objects.count() == 1


class TestMigrateCoreNotes:
    def test_camper_care_medical_is_domain(self, org, program, counselor_person, camper):
        n = _core_note(org, program, counselor_person, camper, CoreNote.NoteType.CAMPER_CARE, category="medical")
        call_command("migrate_observations", apply=True)
        obs = Observation.all_objects.get(legacy_source=f"core.note:{n.pk}")
        assert obs.sensitivity == Observation.Sensitivity.DOMAIN
        assert obs.context == "camper_care"

    def test_specialist_normal(self, org, program, counselor_person, camper):
        n = _core_note(org, program, counselor_person, camper, CoreNote.NoteType.SPECIALIST, is_sensitive=False)
        call_command("migrate_observations", apply=True)
        obs = Observation.all_objects.get(legacy_source=f"core.note:{n.pk}")
        assert obs.sensitivity == Observation.Sensitivity.NORMAL

    def test_maintenance_not_migrated(self, org, program, counselor_person, camper):
        n = _core_note(org, program, counselor_person, camper, CoreNote.NoteType.MAINTENANCE)
        call_command("migrate_observations", apply=True)
        assert not Observation.all_objects.filter(legacy_source=f"core.note:{n.pk}").exists()


class TestMigratePlatformNotes:
    def test_with_camper_reference_migrates_thread(self, org, program, counselor_person, uh_person, camper):
        note = PlatformNote.all_objects.create(
            organization=org, program=program, author=counselor_person,
            author_role_at_write="counselor", subject="Re: behavior",
            body="Saw something today.", camper_reference=camper,
        )
        NoteAudienceCapture.objects.create(note=note, person=uh_person, option_key="my_unit_head")
        NoteReply.objects.create(note=note, author=uh_person, author_role_at_write="unit_head", body="Thanks")
        call_command("migrate_observations", apply=True)
        obs = Observation.all_objects.get(legacy_source=f"notes.note:{note.pk}")
        assert list(ObservationSubject.objects.filter(observation=obs).values_list("subject_id", flat=True)) == [camper.id]
        assert obs.body.startswith("Re: behavior")
        assert obs.recipients.filter(person=uh_person, option_key="my_unit_head").exists()
        assert obs.replies.count() == 1

    def test_peer_note_exported_not_migrated(self, org, program, counselor_person, tmp_path):
        peer = PlatformNote.all_objects.create(
            organization=org, program=program, author=counselor_person,
            author_role_at_write="counselor", subject="Peer chat", body="No camper here.",
        )
        export_path = tmp_path / "peer.json"
        call_command("migrate_observations", apply=True, export_path=str(export_path))
        assert not Observation.all_objects.filter(legacy_source=f"notes.note:{peer.pk}").exists()
        data = json.loads(export_path.read_text())
        assert any(row["id"] == peer.pk for row in data)
