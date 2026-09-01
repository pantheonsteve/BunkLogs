"""Tests for the generic spreadsheet roster source (student bulk upload).

Covers the ``import_people_roster`` command plus the admin preview/commit
endpoints that wrap it. The invariant under test: a blank ``role`` cell
becomes ``student``, and students land as group subjects with no login.
"""
from __future__ import annotations

import io
import textwrap
from datetime import date
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import RosterImportLog

User = get_user_model()

# Maya has an email but no role: she must still resolve to a student with no
# login, which is the whole point of the generic source.
ROSTER_CSV = """
First Name,Last Name,Email,Role,Grade,Class
Maya,Rosen,maya.rosen@example.org,,7,Grade 7A
Daniel,Katz,,student,7,Grade 7A
Sarah,Levine,sarah.levine@example.org,faculty,,Grade 7A
"""


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Sheet School", slug="sheet-school")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Sheet School 2026",
        slug="sheet-2026",
        program_type="religious_school",
        start_date=date(2026, 9, 1),
        end_date=date(2027, 6, 15),
    )


def _run(tmp_path, content: str, org_slug="sheet-school", program_slug="sheet-2026", **kwargs):
    csv_path = tmp_path / "roster.csv"
    csv_path.write_text(textwrap.dedent(content).strip())
    out = StringIO()
    call_command(
        "import_people_roster",
        csv_path=str(csv_path),
        org_slug=org_slug,
        program_slug=program_slug,
        stdout=out,
        **kwargs,
    )
    return out


class TestImportPeopleRosterCommand:
    def test_blank_role_becomes_a_student_subject_without_a_login(
        self, tmp_path, org, program,
    ):
        _run(tmp_path, ROSTER_CSV)

        maya = Person.all_objects.get(organization=org, last_name="Rosen")
        assert maya.user_id is None
        membership = Membership.all_objects.get(program=program, person=maya)
        assert membership.role == "student"
        assert membership.capability == "participant"
        assert membership.grade_level == 7

        classroom = AssignmentGroup.all_objects.get(program=program, name="Grade 7A")
        assert classroom.group_type == "classroom"
        assert AssignmentGroupMembership.all_objects.get(
            group=classroom, person=maya,
        ).role_in_group == "subject"

    def test_staff_rows_still_get_a_login_and_author_placement(
        self, tmp_path, org, program,
    ):
        _run(tmp_path, ROSTER_CSV)

        sarah = Person.all_objects.get(organization=org, last_name="Levine")
        assert sarah.user_id is not None
        classroom = AssignmentGroup.all_objects.get(program=program, name="Grade 7A")
        assert AssignmentGroupMembership.all_objects.get(
            group=classroom, person=sarah,
        ).role_in_group == "author"

    def test_rerunning_the_same_csv_is_a_noop(self, tmp_path, org, program):
        _run(tmp_path, ROSTER_CSV)
        _run(tmp_path, ROSTER_CSV)

        assert Person.all_objects.filter(organization=org).count() == 3
        assert Membership.all_objects.filter(program=program).count() == 3
        assert AssignmentGroup.all_objects.filter(program=program).count() == 1
        assert AssignmentGroupMembership.all_objects.count() == 3

        log = RosterImportLog.all_objects.filter(program=program).first()
        assert log.importer_type == "spreadsheet"
        assert log.status == "completed"
        assert log.summary["persons_created"] == 0

    def test_unknown_role_and_missing_name_are_skipped_with_warnings(
        self, tmp_path, org, program,
    ):
        out = _run(tmp_path, """
            first_name,last_name,role
            Nora,Fine,wizard
            ,Nameless,student
        """)

        output = out.getvalue()
        assert "unknown role 'wizard'" in output
        assert "missing first_name or last_name" in output
        assert Person.all_objects.filter(organization=org).count() == 0

    def test_group_is_optional(self, tmp_path, org, program):
        _run(tmp_path, """
            first_name,last_name
            Solo,Student
        """)

        person = Person.all_objects.get(organization=org, last_name="Student")
        assert Membership.all_objects.get(person=person).role == "student"
        assert not AssignmentGroup.all_objects.filter(program=program).exists()


class TestSpreadsheetImportEndpoints:
    PREVIEW = "/api/v1/admin/people/import/preview/"
    COMMIT = "/api/v1/admin/people/import/commit/"
    TEMPLATE = "/api/v1/admin/people/import/template/"

    @pytest.fixture
    def admin_user(self, org, program):
        user = User.objects.create_user(email="sheet-admin@example.com", password="pw")
        person = Person.all_objects.create(
            organization=org, first_name="Ad", last_name="Min", user=user,
        )
        Membership.all_objects.create(
            program=program, person=person, role="admin", is_active=True,
        )
        return user

    @pytest.fixture
    def api(self, admin_user):
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=admin_user)
        return client

    def _upload(self, api, url, org, program, content=ROSTER_CSV):
        payload = textwrap.dedent(content).strip().encode("utf-8")
        upload = io.BytesIO(payload)
        upload.name = "roster.csv"
        with organization_context(org):
            return api.post(
                url,
                {"source": "spreadsheet", "program_slug": program.slug, "csv": upload},
                format="multipart",
                HTTP_X_ORGANIZATION_SLUG=org.slug,
            )

    def test_preview_classifies_students_as_add_without_a_login(
        self, api, org, program,
    ):
        r = self._upload(api, self.PREVIEW, org, program)
        assert r.status_code == 200, r.content
        body = r.json()
        assert body["summary"]["add"] == 3
        maya = next(row for row in body["rows"] if row["full_name"] == "Maya Rosen")
        assert maya["role"] == "student"
        assert maya["classification"] == "add"
        assert maya["user_link_action"] == "skipped_camper"
        # Preview writes nothing (only the admin fixture's own Person exists).
        assert not Person.all_objects.filter(last_name="Rosen").exists()

    def test_commit_writes_the_roster(self, api, org, program):
        r = self._upload(api, self.COMMIT, org, program)
        assert r.status_code == 200, r.content
        assert r.json()["log"]["summary"]["persons_created"] == 3
        assert Membership.all_objects.filter(
            program=program, role="student",
        ).count() == 2

    def test_template_download_defaults_role_to_student(self, api, org):
        with organization_context(org):
            r = api.get(
                self.TEMPLATE,
                {"source": "spreadsheet", "variant": "students"},
                HTTP_X_ORGANIZATION_SLUG=org.slug,
            )
        assert r.status_code == 200, r.content
        body = r.content.decode("utf-8")
        header, *rows = body.strip().splitlines()
        assert header.startswith("first_name,last_name,preferred_name,email,role")
        # The first sample row leaves role blank on purpose.
        assert rows[0].startswith("Maya,Rosen,,,,7,")
