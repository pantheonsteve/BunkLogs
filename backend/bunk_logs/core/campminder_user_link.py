"""Create or link Django Users for imported Campminder Person rows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from django.contrib.auth import get_user_model

from bunk_logs.core.models import Person

User = get_user_model()

MEMBERSHIP_TO_USER_ROLE: dict[str, str] = {
    "admin": User.ADMIN,
    "leadership_team": User.LEADERSHIP,
    "unit_head": User.UNIT_HEAD,
    "counselor": User.COUNSELOR,
    "junior_counselor": User.COUNSELOR,
    "general_counselor": User.COUNSELOR,
    "specialist": User.COUNSELOR,
    "camper_care": User.CAMPER_CARE,
    "health_center": User.CAMPER_CARE,
    "medical": User.CAMPER_CARE,
    "special_diets": User.CAMPER_CARE,
    "kitchen_staff": User.KITCHEN_STAFF,
    "maintenance": User.KITCHEN_STAFF,
    "administrative_staff": User.COUNSELOR,
    "housekeeping": User.KITCHEN_STAFF,
    "madrich": User.COUNSELOR,
    "faculty": User.LEADERSHIP,
}


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

    linked_person = Person.all_objects.filter(user=user).first()
    if linked_person is not None and (
        existing_person is None or linked_person.pk != existing_person.pk
    ):
        return UserLinkResult(
            UserLinkAction.CONFLICT,
            user_id=user.id,
            message=(
                f"User {user.id} is already linked to Person {linked_person.id}"
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
        linked_person = Person.all_objects.filter(user=user).first()
        if linked_person is not None and linked_person.pk != person.pk:
            return UserLinkResult(
                UserLinkAction.CONFLICT,
                user_id=user.id,
                message=(
                    f"User {user.id} is already linked to Person {linked_person.id}"
                ),
            )
        person.user = user
        person.save(update_fields=["user"])
        return UserLinkResult(UserLinkAction.LINKED, user_id=user.id)

    user = User(
        email=email,
        first_name=person.first_name,
        last_name=person.last_name,
        role=MEMBERSHIP_TO_USER_ROLE.get(membership_role, User.COUNSELOR),
        is_active=True,
    )
    user.set_unusable_password()
    user.save()
    person.user = user
    person.save(update_fields=["user"])
    return UserLinkResult(UserLinkAction.CREATED, user_id=user.id)
