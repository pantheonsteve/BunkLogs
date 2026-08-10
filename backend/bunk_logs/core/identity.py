"""Resolve the Person record for a User within an organization.

Since ``Person.user`` became a ForeignKey (one Person per org per human),
"the Person for this user" is only unambiguous within a tenant. This is the
single shared lookup; request-path callers get the ambient organization from
the multi-tenant middleware via ``get_current_organization()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bunk_logs.core.context import get_current_organization
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.program_scope import is_program_operational
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization

# Highest-to-lowest precedence when summarizing a person's memberships in an
# org down to a single capability for the auth payload.
_CAPABILITY_PRECEDENCE = (
    "admin",
    "program_lead",
    "supervisor",
    "domain_specialist",
    "participant",
)


def person_for_user(user, *, organization: Organization | None = None) -> Person | None:
    """Return the Person linked to ``user`` in ``organization``.

    Falls back to the ambient tenant context when no organization is passed.
    Without any org in scope, resolves only when the user has exactly one
    linked Person; multi-org users must be resolved within a tenant.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    org = organization if organization is not None else get_current_organization()
    qs = Person.all_objects.filter(user=user)
    if org is not None:
        return qs.filter(organization=org).first()
    people = list(qs[:2])
    if len(people) == 1:
        return people[0]
    return None


def _operationally_scoped_memberships(person: Person) -> list[Membership]:
    """Active memberships for ``person``, preferring ones on a running program.

    People accumulate Memberships across sessions/programs (e.g. a Session 1
    ``leadership_team`` role that's never explicitly deactivated after the
    person is reassigned as ``unit_head`` for Session 2). Auth payloads must
    reflect the person's CURRENT job, not every role they've ever held --
    otherwise a stale higher-priority role permanently shadows their real,
    current role in the frontend's priority-ordered home routing
    (``MEMBERSHIP_ROLE_HOME_PATHS``).

    Falls back to all active memberships when none sit on an operational
    program (e.g. the gap between sessions) so people aren't locked out of
    their roles during off-season windows.
    """
    memberships = list(
        Membership.all_objects.filter(person=person, is_active=True)
        .select_related("program"),
    )
    today = get_today(person.organization)
    operational = [
        m for m in memberships if is_program_operational(m.program, today=today)
    ]
    return operational or memberships


def active_membership_roles(user) -> list[str]:
    """Distinct active Membership roles for ``user``, across all their orgs.

    Flattened union kept on auth payloads as ``membership_roles`` for
    backwards compatibility; per-org roles live in ``organizations_payload``.
    Scoped per-org to operationally-running programs where possible (see
    :func:`_operationally_scoped_memberships`).
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return []
    people = Person.all_objects.filter(user=user).select_related("organization")
    roles: set[str] = set()
    for person in people:
        roles.update(m.role for m in _operationally_scoped_memberships(person))
    return sorted(roles)


def _program_types_for(person: Person, memberships: list[Membership]) -> list[str]:
    """Program types in play for ``person``, for org-shape decisions in the UI.

    Read from the memberships the caller already loaded (they carry
    ``select_related("program")``), so the common path costs no extra query.
    A person between memberships would otherwise report nothing, so fall back
    to the org's active programs -- same signal ``_default_rollover_for`` uses
    to tell a religious school apart from a camp.
    """
    types = {m.program.program_type for m in memberships if m.program_id}
    if not types:
        types = set(
            Program.all_objects.filter(
                organization=person.organization, is_active=True,
            ).values_list("program_type", flat=True),
        )
    return sorted(t for t in types if t)


def organizations_payload(user) -> list[dict]:
    """Per-org auth context for the login / session payloads.

    One entry per organization where the user holds a Person, e.g.
    ``{"slug": "tbe", "name": "Temple Beth-El", "capability": "participant",
    "roles": ["madrich"], "program_types": ["religious_school"]}``.
    ``capability`` is the highest RBAC capability across the person's active,
    operationally-scoped memberships (None when they have none). See
    :func:`_operationally_scoped_memberships`. ``program_types`` drives which
    product surfaces the frontend shows (camp ops vs religious school).
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return []
    entries = []
    people = Person.all_objects.filter(user=user).select_related("organization")
    for person in people:
        memberships = _operationally_scoped_memberships(person)
        pairs = [(m.role, m.capability) for m in memberships]
        roles = sorted({role for role, _ in pairs})
        capabilities = {cap for _, cap in pairs}
        capability = next(
            (c for c in _CAPABILITY_PRECEDENCE if c in capabilities), None,
        )
        entries.append({
            "slug": person.organization.slug,
            "name": person.organization.name,
            "capability": capability,
            "roles": roles,
            "program_types": _program_types_for(person, memberships),
        })
    return sorted(entries, key=lambda entry: entry["slug"])
