"""Observation read visibility (Step 7_23).

Layers the SubjectNote read model with three additions:

    readable = ( author )
        OR ( explicitly tagged recipient )
        OR ( role hierarchy covers ANY tagged subject, gated by sensitivity )

The author and recipient legs are unconditional (recipients were filtered by
the authoring-time sensitivity gate, so they always cleared). The hierarchy leg
is intersected with the org sensitivity map. "Covers ANY subject" means the read
``Q`` ORs across the ``subjects`` M2M, so a multi-subject observation is visible
to either subject's hierarchy.
"""

from __future__ import annotations

from django.db.models import Q

from bunk_logs.core.permissions.subject_note_read import _supervised_subject_ids
from bunk_logs.core.permissions.subject_note_read import _viewer_capability
from bunk_logs.core.permissions.super_admin import is_super_admin

# Sensitivity tiers, ordered low -> high.
SENSITIVITY_TIERS = ["normal", "sensitive", "domain", "confidential"]

# Code default mirrors NOTE_VIS_BY_CAP with sensitivity tier names. Orgs may
# override per capability via Organization.settings["observations"]["view_by_capability"].
DEFAULT_VIEW_BY_CAPABILITY: dict[str, set[str]] = {
    "admin": {"normal", "sensitive", "domain", "confidential"},
    "program_lead": {"normal", "sensitive", "domain"},
    "domain_specialist": {"normal", "sensitive", "domain"},
    "supervisor": {"normal", "sensitive"},
    "participant": set(),
}


def view_by_capability_for_org(org) -> dict[str, set[str]]:
    """Merged capability -> viewable-tiers map: org settings overlay code defaults."""
    merged = {cap: set(tiers) for cap, tiers in DEFAULT_VIEW_BY_CAPABILITY.items()}
    settings = getattr(org, "settings", None) or {}
    overrides = (settings.get("observations") or {}).get("view_by_capability") or {}
    for cap, tiers in overrides.items():
        if cap in merged and isinstance(tiers, (list, set, tuple)):
            merged[cap] = {t for t in tiers if t in SENSITIVITY_TIERS}
    return merged


def capability_clears(capability: str | None, sensitivity: str, org) -> bool:
    """True if ``capability`` may view observations at ``sensitivity`` for ``org``."""
    if capability is None:
        return False
    return sensitivity in view_by_capability_for_org(org).get(capability, set())


def observation_read_q(viewer_person, org, user) -> Q:
    """Return a ``Q`` filter for Observations the viewer may read.

    Callers should ``.distinct()`` the result — the recipient and subject legs
    join across to-many relations and can multiply rows.
    """
    if is_super_admin(user):
        return Q()
    if viewer_person is None:
        return Q(pk__in=[])

    vis_map = view_by_capability_for_org(org)
    authored = Q(author=viewer_person)
    recipient = Q(recipients__person=viewer_person)
    cap = _viewer_capability(viewer_person, org)
    hierarchy = Q(pk__in=[])

    if cap in ("admin", "program_lead", "domain_specialist"):
        tiers = vis_map.get(cap, set())
        hierarchy = Q(sensitivity__in=tiers) if tiers else Q(pk__in=[])
    elif cap in ("supervisor", "participant"):
        supervisor_tiers = vis_map.get("supervisor", set())
        supervised_ids = _supervised_subject_ids(viewer_person)
        # A subject can always see their own subject_visible observations.
        hierarchy = Q(subject_links__subject_id=viewer_person.id, subject_visible=True)
        if supervised_ids and supervisor_tiers:
            hierarchy |= Q(
                subject_links__subject_id__in=supervised_ids,
                sensitivity__in=supervisor_tiers,
            )

    return authored | recipient | hierarchy


def filter_observations_readable(qs, viewer_person, org, user):
    """Filter an Observation queryset to rows the viewer may read."""
    if is_super_admin(user):
        return qs
    if viewer_person is None:
        return qs.none()
    return qs.filter(observation_read_q(viewer_person, org, user)).distinct()


__all__ = [
    "DEFAULT_VIEW_BY_CAPABILITY",
    "SENSITIVITY_TIERS",
    "capability_clears",
    "filter_observations_readable",
    "observation_read_q",
    "view_by_capability_for_org",
]
