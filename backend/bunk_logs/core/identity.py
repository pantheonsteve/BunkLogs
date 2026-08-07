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


def active_membership_roles(user) -> list[str]:
    """Distinct active Membership roles for ``user``, across all their orgs.

    Flattened union kept on auth payloads as ``membership_roles`` for
    backwards compatibility; per-org roles live in ``organizations_payload``.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return []
    person_ids = Person.all_objects.filter(user=user).values_list("id", flat=True)
    if not person_ids:
        return []
    return sorted(
        set(
            Membership.all_objects.filter(
                person_id__in=list(person_ids), is_active=True,
            ).values_list("role", flat=True),
        ),
    )


def organizations_payload(user) -> list[dict]:
    """Per-org auth context for the login / session payloads.

    One entry per organization where the user holds a Person, e.g.
    ``{"slug": "tbe", "name": "Temple Beth-El", "capability": "participant",
    "roles": ["madrich"]}``. ``capability`` is the highest RBAC capability
    across the person's active memberships (None when they have none).
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return []
    entries = []
    people = Person.all_objects.filter(user=user).select_related("organization")
    for person in people:
        pairs = Membership.all_objects.filter(
            person=person, is_active=True,
        ).values_list("role", "capability")
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
        })
    return sorted(entries, key=lambda entry: entry["slug"])
