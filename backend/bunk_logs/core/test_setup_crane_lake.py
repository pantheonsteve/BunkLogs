from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command

from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program


@pytest.mark.django_db
def test_setup_crane_lake_creates_org_and_program():
    out = StringIO()
    call_command("setup_crane_lake", stdout=out)

    org = Organization.objects.get(slug="clc")
    assert org.name == "URJ Crane Lake Camp"
    assert org.settings.get("timezone") == "America/New_York"
    assert org.settings.get("locale_default") == "en"
    assert org.is_active is True

    program = Program.all_objects.get(organization=org, slug="summer-2026")
    assert program.name == "Summer 2026"
    assert program.program_type == "summer_camp"
    assert program.start_date == date(2026, 6, 28)
    assert program.end_date == date(2026, 8, 16)


@pytest.mark.django_db
def test_setup_crane_lake_idempotent():
    call_command("setup_crane_lake", stdout=StringIO())
    org_id = Organization.objects.get(slug="clc").pk
    call_command("setup_crane_lake", stdout=StringIO())
    call_command("setup_crane_lake", stdout=StringIO())

    assert Organization.objects.filter(slug="clc").count() == 1
    assert Organization.objects.get(slug="clc").pk == org_id
    assert Program.all_objects.filter(organization_id=org_id, slug="summer-2026").count() == 1


@pytest.mark.django_db
def test_setup_crane_lake_merges_settings_on_existing_org():
    Organization.objects.create(
        name="Old Name",
        slug="clc",
        settings={"custom": "keep_me"},
    )
    call_command("setup_crane_lake", stdout=StringIO())
    org = Organization.objects.get(slug="clc")
    assert org.name == "URJ Crane Lake Camp"
    assert org.settings.get("custom") == "keep_me"
    assert org.settings.get("timezone") == "America/New_York"
