"""Create or link Django Users for imported Campminder Person rows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from django.contrib.auth import get_user_model

from bunk_logs.core.context import get_current_organization
from bunk_logs.core.models import Person

User = get_user_model()


class UserLinkAction(str, Enum):
    CREATED = "created"
    LINKED = "linked"
    ALREADY_LINKED = "already_linked"
    SKIPPED_NO_EMAIL = "skipped_no_email"
    SKIPPED_CAMPER = "skipped_camper"
    CONFLICT = "conflict"


@dataclass
class UserLinkResult:
    action: UserLinkAction
    user_id: int | None = None
    message: str = ""


def _linked_person_in_org(user, organization) -> Person | None:
    """The Person already linked to ``user`` within ``organization`` (if any).

    Linking one User to Persons in *different* orgs is allowed (multi-org
    staff); a conflict only exists when the User is already attached to a
    different Person in the same org.
    """
    if organization is None:
        return None
    return Person.all_objects.filter(user=user, organization=organization).first()


def preview_user_link(
    *,
    email: str,
    membership_role: str,
    existing_person: Person | None,
) -> UserLinkResult:
    """Dry-run what ``ensure_user_for_imported_person`` would do."""
    email = (email or "").strip()
    if not email:
        return UserLinkResult(UserLinkAction.SKIPPED_NO_EMAIL)
    if membership_role == "camper":
        return UserLinkResult(UserLinkAction.SKIPPED_CAMPER)

    if existing_person is not None and existing_person.user_id:
        return UserLinkResult(
            UserLinkAction.ALREADY_LINKED,
            user_id=existing_person.user_id,
        )

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        return UserLinkResult(UserLinkAction.CREATED)

    organization = (
        existing_person.organization if existing_person is not None
        else get_current_organization()
    )
    linked_person = _linked_person_in_org(user, organization)
    if linked_person is not None and (
        existing_person is None or linked_person.pk != existing_person.pk
    ):
        return UserLinkResult(
            UserLinkAction.CONFLICT,
            user_id=user.id,
            message=(
                f"User {user.id} is already linked to Person {linked_person.id} "
                f"in this organization"
            ),
        )
    return UserLinkResult(UserLinkAction.LINKED, user_id=user.id)


def ensure_user_for_imported_person(
    person: Person,
    *,
    membership_role: str,
) -> UserLinkResult:
    """Create or link a login User when the imported person has an email."""
    email = (person.email or "").strip()
    if not email:
        return UserLinkResult(UserLinkAction.SKIPPED_NO_EMAIL)
    if membership_role == "camper":
        return UserLinkResult(UserLinkAction.SKIPPED_CAMPER)

    if person.user_id:
        return UserLinkResult(
            UserLinkAction.ALREADY_LINKED,
            user_id=person.user_id,
        )

    user = User.objects.filter(email__iexact=email).first()
    if user is not None:
        linked_person = _linked_person_in_org(user, person.organization)
        if linked_person is not None and linked_person.pk != person.pk:
            return UserLinkResult(
                UserLinkAction.CONFLICT,
                user_id=user.id,
                message=(
                    f"User {user.id} is already linked to Person {linked_person.id} "
                    f"in this organization"
                ),
            )
        person.user = user
        person.save(update_fields=["user"])
        return UserLinkResult(UserLinkAction.LINKED, user_id=user.id)

    # Roles/capabilities live on the Membership, not the User.
    user = User(
        email=email,
        first_name=person.first_name,
        last_name=person.last_name,
        is_active=True,
    )
    user.set_unusable_password()
    user.save()
    person.user = user
    person.save(update_fields=["user"])
    return UserLinkResult(UserLinkAction.CREATED, user_id=user.id)
