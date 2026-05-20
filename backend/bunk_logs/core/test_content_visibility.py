"""Unit tests for ``content_visibility`` — visibility table contract."""
from __future__ import annotations

import pytest

from bunk_logs.core.content_visibility import ROLE_LABELS
from bunk_logs.core.content_visibility import ContentType
from bunk_logs.core.content_visibility import MaintenanceNoteVisibility
from bunk_logs.core.content_visibility import audience_labels
from bunk_logs.core.content_visibility import audience_roles
from bunk_logs.core.content_visibility import gating_role_label
from bunk_logs.core.content_visibility import viewer_can_read

pytestmark = pytest.mark.django_db


class TestVisibilityTableAudiences:
    """Line-by-line checks against visibility_model.md."""

    def test_camper_reflection_default_audience(self):
        roles = audience_roles(ContentType.CAMPER_REFLECTION)
        assert roles == frozenset({
            "counselor", "unit_head", "camper_care", "leadership_team", "admin",
        })
        assert audience_roles(ContentType.CAMPER_REFLECTION, is_sensitive=True) == roles

    def test_counselor_self_reflection(self):
        assert audience_roles(ContentType.COUNSELOR_SELF_REFLECTION) == frozenset({
            "counselor", "unit_head", "leadership_team", "admin",
        })

    def test_unit_head_self_reflection(self):
        assert audience_roles(ContentType.UNIT_HEAD_SELF_REFLECTION) == frozenset({
            "unit_head", "leadership_team", "admin",
        })

    def test_camper_care_note_sensitive_variant(self):
        default = audience_roles(ContentType.CAMPER_CARE_NOTE)
        assert default == frozenset({"camper_care", "leadership_team", "admin"})
        sensitive = audience_roles(ContentType.CAMPER_CARE_NOTE, is_sensitive=True)
        assert sensitive == frozenset({
            "camper_care", "health_center", "special_diets", "admin",
        })
        assert "counselor" not in sensitive

    def test_specialist_note_sensitive_variant(self):
        default = audience_roles(ContentType.SPECIALIST_NOTE)
        assert "counselor" in default
        sensitive = audience_roles(ContentType.SPECIALIST_NOTE, is_sensitive=True)
        assert "counselor" not in sensitive
        assert "health_center" in sensitive

    def test_specialist_self_reflection(self):
        assert audience_roles(ContentType.SPECIALIST_SELF_REFLECTION) == frozenset({
            "specialist", "leadership_team", "admin",
        })

    def test_maintenance_team_only(self):
        roles = audience_roles(
            ContentType.MAINTENANCE_TICKET_NOTE,
            maintenance_visibility=MaintenanceNoteVisibility.TEAM_ONLY,
        )
        assert roles == frozenset({"maintenance", "admin"})
        assert "counselor" not in roles

    def test_maintenance_submitter_visible(self):
        roles = audience_roles(
            ContentType.MAINTENANCE_TICKET_NOTE,
            maintenance_visibility=MaintenanceNoteVisibility.SUBMITTER_VISIBLE,
        )
        assert "counselor" in roles
        assert "unit_head" in roles

    def test_kitchen_staff_reflection(self):
        assert audience_roles(ContentType.KITCHEN_STAFF_REFLECTION) == frozenset({
            "leadership_team", "admin",
        })

    def test_leadership_team_private(self):
        assert audience_roles(
            ContentType.LEADERSHIP_TEAM_SELF_REFLECTION, is_private=True,
        ) == frozenset({"admin"})

    def test_madrich_reflection(self):
        assert audience_roles(ContentType.MADRICH_REFLECTION) == frozenset({
            "director", "admin",
        })

    def test_admin_self_reflection_private(self):
        assert audience_roles(
            ContentType.ADMIN_SELF_REFLECTION, is_private=True,
        ) == frozenset({"admin"})


class TestAudienceLabels:
    def test_labels_sorted_and_human_readable(self):
        labels = audience_labels(ContentType.COUNSELOR_SELF_REFLECTION)
        assert labels == sorted(labels)
        assert ROLE_LABELS["counselor"] in labels

    def test_sensitive_updates_labels(self):
        default = set(audience_labels(ContentType.SPECIALIST_NOTE))
        sensitive = set(audience_labels(ContentType.SPECIALIST_NOTE, is_sensitive=True))
        assert "Counselor" in default
        assert "Counselor" not in sensitive
        assert "Health Center" in sensitive


class TestViewerCanRead:
    def test_author_always_allowed(self):
        assert viewer_can_read(
            frozenset(), ContentType.SPECIALIST_NOTE, is_sensitive=True, is_author=True,
        )

    def test_admin_always_allowed(self):
        assert viewer_can_read(
            frozenset(), ContentType.SPECIALIST_NOTE, is_sensitive=True, is_org_admin=True,
        )

    def test_counselor_cannot_read_sensitive_specialist_note(self):
        assert not viewer_can_read(
            frozenset({"counselor"}),
            ContentType.SPECIALIST_NOTE,
            is_sensitive=True,
        )

    def test_health_center_reads_sensitive_specialist_note(self):
        assert viewer_can_read(
            frozenset({"health_center"}),
            ContentType.SPECIALIST_NOTE,
            is_sensitive=True,
        )


class TestGatingRoleLabel:
    def test_specialist_note_gates_to_camper_care(self):
        assert gating_role_label(ContentType.SPECIALIST_NOTE) == "Camper Care"
