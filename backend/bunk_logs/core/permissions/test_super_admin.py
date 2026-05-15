"""Unit tests for the ``is_super_admin`` helper.

The helper itself is two lines; these tests exist to pin the contract so a
future refactor can't quietly tighten the gate (e.g. dropping ``is_staff``
support) without a failing test.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model

from bunk_logs.core.permissions import is_super_admin


def test_returns_false_for_none():
    assert is_super_admin(None) is False


def test_returns_false_for_unauthenticated_duck():
    user = SimpleNamespace(is_authenticated=False, is_staff=True, is_superuser=True)
    assert is_super_admin(user) is False


def test_returns_false_for_anonymous_like_user_without_attrs():
    user = SimpleNamespace(is_authenticated=False)
    assert is_super_admin(user) is False


def test_returns_false_for_authenticated_user_with_neither_flag():
    user = SimpleNamespace(is_authenticated=True, is_staff=False, is_superuser=False)
    assert is_super_admin(user) is False


def test_returns_true_for_is_staff_only():
    user = SimpleNamespace(is_authenticated=True, is_staff=True, is_superuser=False)
    assert is_super_admin(user) is True


def test_returns_true_for_is_superuser_only():
    user = SimpleNamespace(is_authenticated=True, is_staff=False, is_superuser=True)
    assert is_super_admin(user) is True


def test_returns_true_when_both_flags_set():
    user = SimpleNamespace(is_authenticated=True, is_staff=True, is_superuser=True)
    assert is_super_admin(user) is True


@pytest.mark.django_db
def test_returns_true_for_real_django_staff_user():
    """Smoke check against an actual Django User instance, not just a duck."""
    user = get_user_model().objects.create_user(
        email="staff@example.com", password="pw", is_staff=True,
    )
    assert is_super_admin(user) is True
    assert user.is_superuser is False
