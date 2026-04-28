import pytest
from django.db import IntegrityError

from bunk_logs.core.models import Organization


@pytest.mark.django_db
class TestOrganization:
    def test_create_organization(self):
        org = Organization.objects.create(name="Test Camp", slug="test-camp")
        assert org.pk is not None
        assert str(org) == "Test Camp"

    def test_slug_uniqueness_enforced(self):
        Organization.objects.create(name="Camp One", slug="camp-one")
        with pytest.raises(IntegrityError):
            Organization.objects.create(name="Camp One Duplicate", slug="camp-one")

    def test_settings_json_accepts_arbitrary_dict(self):
        payload = {"theme": "dark", "features": ["messaging", "reflections"], "max_users": 500}
        org = Organization.objects.create(name="Rich Camp", slug="rich-camp", settings=payload)
        org.refresh_from_db()
        assert org.settings == payload

    def test_settings_defaults_to_empty_dict(self):
        org = Organization.objects.create(name="Minimal Camp", slug="minimal-camp")
        assert org.settings == {}

    def test_is_active_defaults_to_true(self):
        org = Organization.objects.create(name="Active Camp", slug="active-camp")
        assert org.is_active is True

    def test_ordering_by_name(self):
        Organization.objects.create(name="Zeta Camp", slug="zeta-camp")
        Organization.objects.create(name="Alpha Camp", slug="alpha-camp")
        names = list(Organization.objects.values_list("name", flat=True))
        assert names == sorted(names)
