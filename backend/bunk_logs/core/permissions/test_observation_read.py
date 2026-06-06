"""Tests for the layered Observation read + sensitivity permissions (Step 7_23).

Covers each read leg (author, recipient, hierarchy), multi-subject OR, the
sensitivity intersection on the hierarchy leg, cross-org isolation, the org
sensitivity-map overlay, and the authoring-time recipient gate.
"""

from __future__ import annotations

from datetime import date

import pytest

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.permissions.observation_authoring import recipients_clearing_sensitivity
from bunk_logs.core.permissions.observation_read import capability_clears
from bunk_logs.core.permissions.observation_read import filter_observations_readable
from bunk_logs.core.permissions.observation_read import view_by_capability_for_org
from bunk_logs.notes.models import Observation
from bunk_logs.notes.models import ObservationRecipient
from bunk_logs.notes.models import ObservationSubject

pytestmark = pytest.mark.django_db

S = Observation.Sensitivity


@pytest.fixture
def org():
    return Organization.objects.create(name="Obs Org", slug="obs-org")


@pytest.fixture
def other_org():
    return Organization.objects.create(name="Obs Other", slug="obs-other")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="Obs Org Summer", slug="obs-summer",
        program_type="summer_camp", start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


def _person(org, first, last="X"):
    return Person.all_objects.create(organization=org, first_name=first, last_name=last)


def _member(program, person, role):
    return Membership.all_objects.create(program=program, person=person, role=role, is_active=True)


def _bunk(org, program, slug="bunk-a"):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program, name=slug, slug=slug, group_type="bunk",
    )


def _author_in(group, person):
    return AssignmentGroupMembership.all_objects.create(
        group=group, person=person, role_in_group="author", is_active=True,
    )


def _subject_in(group, person):
    return AssignmentGroupMembership.all_objects.create(
        group=group, person=person, role_in_group="subject", is_active=True,
    )


def _obs(org, program, author, sensitivity, subjects, *, subject_visible=False):
    obs = Observation.all_objects.create(
        organization=org, program=program, author=author,
        body="b", sensitivity=sensitivity, subject_visible=subject_visible,
    )
    for s in subjects:
        ObservationSubject.objects.create(observation=obs, subject=s)
    return obs


def _readable_ids(viewer, org, user=None):
    # Callers pass an org-scoped queryset (the OrgScopedManager does this in
    # request context); the read Q itself adds no organization filter.
    base = Observation.all_objects.filter(organization=org)
    qs = filter_observations_readable(base, viewer, org, user)
    return set(qs.values_list("id", flat=True))


# ---------------------------------------------------------------------------
# Read legs
# ---------------------------------------------------------------------------
def test_author_reads_own_even_confidential(org, program):
    counselor = _person(org, "Counselor")
    _member(program, counselor, "counselor")
    camper = _person(org, "Camper")
    # Author does not cover the subject, top sensitivity — author leg still wins.
    obs = _obs(org, program, counselor, S.CONFIDENTIAL, [camper])
    assert obs.id in _readable_ids(counselor, org)


def test_recipient_reads_even_confidential(org, program):
    admin = _person(org, "Admin")
    _member(program, admin, "admin")
    counselor = _person(org, "Counselor")
    _member(program, counselor, "counselor")
    camper = _person(org, "Camper")
    obs = _obs(org, program, admin, S.CONFIDENTIAL, [camper])
    ObservationRecipient.objects.create(observation=obs, person=counselor, option_key="specific_person")
    assert obs.id in _readable_ids(counselor, org)


def test_program_lead_covers_subject_reads_domain_not_confidential(org, program):
    lt = _person(org, "LT")
    _member(program, lt, "leadership_team")  # capability=program_lead
    author = _person(org, "Author")
    _member(program, author, "counselor")
    camper = _person(org, "Camper")
    bunk = _bunk(org, program)
    _author_in(bunk, lt)
    _subject_in(bunk, camper)
    domain = _obs(org, program, author, S.DOMAIN, [camper])
    confidential = _obs(org, program, author, S.CONFIDENTIAL, [camper])
    readable = _readable_ids(lt, org)
    assert domain.id in readable
    assert confidential.id not in readable


def test_domain_specialist_covers_subject_reads_sensitive_not_domain(org, program):
    cc = _person(org, "CC")
    _member(program, cc, "camper_care")  # capability=domain_specialist
    author = _person(org, "Author")
    _member(program, author, "counselor")
    camper = _person(org, "Camper")
    bunk = _bunk(org, program)
    _author_in(bunk, cc)
    _subject_in(bunk, camper)
    sensitive = _obs(org, program, author, S.SENSITIVE, [camper])
    domain = _obs(org, program, author, S.DOMAIN, [camper])
    readable = _readable_ids(cc, org)
    assert sensitive.id in readable
    assert domain.id not in readable


def test_supervisor_covers_subject_reads_sensitive_not_confidential(org, program):
    uh = _person(org, "UH")
    _member(program, uh, "unit_head")  # capability=supervisor
    author = _person(org, "Author")
    _member(program, author, "leadership_team")
    camper = _person(org, "Camper")
    bunk = _bunk(org, program)
    _author_in(bunk, uh)
    _subject_in(bunk, camper)
    sensitive = _obs(org, program, author, S.SENSITIVE, [camper])
    confidential = _obs(org, program, author, S.CONFIDENTIAL, [camper])
    readable = _readable_ids(uh, org)
    assert sensitive.id in readable
    assert confidential.id not in readable


def test_non_covering_participant_sees_nothing(org, program):
    outsider = _person(org, "Outsider")
    _member(program, outsider, "counselor")
    author = _person(org, "Author")
    _member(program, author, "admin")
    camper = _person(org, "Camper")
    obs = _obs(org, program, author, S.NORMAL, [camper])
    assert obs.id not in _readable_ids(outsider, org)


def test_multi_subject_or_visible_to_either_hierarchy(org, program):
    author = _person(org, "Author")
    _member(program, author, "admin")
    uh_a = _person(org, "UHA")
    _member(program, uh_a, "unit_head")
    camper_a = _person(org, "CamperA")
    camper_b = _person(org, "CamperB")
    bunk_a = _bunk(org, program, "bunk-a")
    _author_in(bunk_a, uh_a)
    _subject_in(bunk_a, camper_a)
    # uh_a only covers camper_a, but the observation tags both campers.
    obs = _obs(org, program, author, S.NORMAL, [camper_a, camper_b])
    assert obs.id in _readable_ids(uh_a, org)


def test_admin_reads_org_wide_all_tiers(org, program):
    admin = _person(org, "Admin")
    _member(program, admin, "admin")
    author = _person(org, "Author")
    _member(program, author, "counselor")
    camper = _person(org, "Camper")
    obs = _obs(org, program, author, S.CONFIDENTIAL, [camper])
    assert obs.id in _readable_ids(admin, org)


def test_cross_org_isolation(org, other_org, program):
    other_program = Program.all_objects.create(
        organization=other_org, name="Obs Other Summer", slug="other-prog",
        program_type="summer_camp", start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )
    admin_other = _person(other_org, "AdminOther")
    _member(other_program, admin_other, "admin")
    author = _person(org, "Author")
    _member(program, author, "counselor")
    camper = _person(org, "Camper")
    obs = _obs(org, program, author, S.NORMAL, [camper])
    # Admin of another org must not see this org's observation.
    assert obs.id not in _readable_ids(admin_other, other_org)


# ---------------------------------------------------------------------------
# Sensitivity map + org overlay
# ---------------------------------------------------------------------------
def test_capability_clears_defaults(org):
    assert capability_clears("supervisor", "sensitive", org) is True
    assert capability_clears("supervisor", "domain", org) is False
    assert capability_clears("domain_specialist", "domain", org) is False
    assert capability_clears("program_lead", "domain", org) is True
    assert capability_clears("supervisor", "confidential", org) is False
    assert capability_clears("admin", "confidential", org) is True
    assert capability_clears("participant", "normal", org) is False


def test_org_overlay_widens_supervisor(org):
    org.settings = {"observations": {"view_by_capability": {"supervisor": ["normal", "sensitive", "domain"]}}}
    org.save()
    assert "domain" in view_by_capability_for_org(org)["supervisor"]
    assert capability_clears("supervisor", "domain", org) is True


# ---------------------------------------------------------------------------
# Authoring-time recipient gate
# ---------------------------------------------------------------------------
def test_recipients_clearing_sensitivity_filters_by_tier(org, program):
    author = _person(org, "Author")
    _member(program, author, "admin")
    uh = _person(org, "UH")
    _member(program, uh, "unit_head")  # supervisor
    admin2 = _person(org, "Admin2")
    _member(program, admin2, "admin")

    sensitive_ok = set(recipients_clearing_sensitivity(author, org, "sensitive").values_list("id", flat=True))
    assert uh.id in sensitive_ok
    assert admin2.id in sensitive_ok

    confidential_ok = set(recipients_clearing_sensitivity(author, org, "confidential").values_list("id", flat=True))
    assert uh.id not in confidential_ok  # supervisor cannot clear confidential
    assert admin2.id in confidential_ok


def test_recipients_exclude_self(org, program):
    admin = _person(org, "Admin")
    _member(program, admin, "admin")
    ids = set(recipients_clearing_sensitivity(admin, org, "confidential").values_list("id", flat=True))
    assert admin.id not in ids
