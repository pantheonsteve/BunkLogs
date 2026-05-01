from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from asgiref.local import Local

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization

_org_local = Local()


def get_current_organization() -> Organization | None:
    return getattr(_org_local, "organization", None)


def set_current_organization(organization: Organization | None) -> None:
    _org_local.organization = organization


def clear_current_organization() -> None:
    if hasattr(_org_local, "organization"):
        delattr(_org_local, "organization")


@contextmanager
def organization_context(organization: Organization | None):
    previous = get_current_organization()
    set_current_organization(organization)
    try:
        yield
    finally:
        if previous is None:
            clear_current_organization()
        else:
            set_current_organization(previous)
