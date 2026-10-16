"""Data migration: Temple Beth-El gets the reflection completion roster."""
from importlib import import_module

import pytest
from django.apps import apps

from bunk_logs.core.models import Organization


def _run():
    migration = import_module(
        "bunk_logs.core.migrations.0069_reflection_completion_flag",
    )
    migration.enable_reflection_completion(apps, None)


@pytest.mark.django_db
def test_reflection_completion_flag_is_set_for_tbe_only():
    tbe = Organization.objects.create(name="Temple Beth-El", slug="tbe", settings={"timezone": "UTC"})
    clc = Organization.objects.create(name="Crane Lake", slug="clc", settings={})

    _run()
    tbe.refresh_from_db()
    clc.refresh_from_db()
    assert tbe.settings["reflection_completion"] is True
    assert tbe.settings["timezone"] == "UTC"
    assert clc.settings.get("reflection_completion") is not True

    _run()
    tbe.refresh_from_db()
    assert tbe.settings["reflection_completion"] is True
    assert tbe.settings["timezone"] == "UTC"
