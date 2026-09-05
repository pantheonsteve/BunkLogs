"""Shared constants for the TBE client-test sandbox.

Lives in the real ``tbe`` Organization as program ``client-test`` so testers
can sign in at ``tbe.bunklogs.net`` (subdomain routing). Cleanup matches
these emails / the Person ``external_ids.source`` tag only.
"""

from __future__ import annotations

from typing import Any

ORG_SLUG = "tbe"
PROGRAM_SLUG = "client-test"
PROGRAM_NAME_SUFFIX = "Client Test"
PERSON_SOURCE = "tbe_client_test"
EMAIL_DOMAIN = "bunklogs.test"

MADRICH_TEMPLATE_SLUG = "tbe-madrich-3-2-1-weekly"
FACULTY_TEMPLATE_SLUG = "faculty-self-reflection"

ADMIN: dict[str, str] = {
    "email": f"test-admin@{EMAIL_DOMAIN}",
    "first_name": "TEST",
    "last_name": "Admin",
}

FACULTY: list[dict[str, str]] = [
    {
        "email": f"test-faculty-1@{EMAIL_DOMAIN}",
        "first_name": "TEST",
        "last_name": "Faculty One",
        "classroom": "grade-3",
    },
    {
        "email": f"test-faculty-2@{EMAIL_DOMAIN}",
        "first_name": "TEST",
        "last_name": "Faculty Two",
        "classroom": "grade-5",
    },
]

MADRICHIM: list[dict[str, Any]] = [
    {
        "email": f"test-madrich-8@{EMAIL_DOMAIN}",
        "first_name": "TEST",
        "last_name": "Madrich Eight",
        "grade": 8,
        "classroom": "grade-3",
    },
    {
        "email": f"test-madrich-9@{EMAIL_DOMAIN}",
        "first_name": "TEST",
        "last_name": "Madrich Nine",
        "grade": 9,
        "classroom": "grade-3",
    },
    {
        "email": f"test-madrich-10@{EMAIL_DOMAIN}",
        "first_name": "TEST",
        "last_name": "Madrich Ten",
        "grade": 10,
        "classroom": "grade-5",
    },
    {
        "email": f"test-madrich-11@{EMAIL_DOMAIN}",
        "first_name": "TEST",
        "last_name": "Madrich Eleven",
        "grade": 11,
        "classroom": "grade-5",
    },
]

STUDENTS: list[dict[str, str]] = [
    {
        "email": f"test-student-a@{EMAIL_DOMAIN}",
        "first_name": "TEST",
        "last_name": "Student A",
        "classroom": "grade-3",
    },
    {
        "email": f"test-student-b@{EMAIL_DOMAIN}",
        "first_name": "TEST",
        "last_name": "Student B",
        "classroom": "grade-3",
    },
    {
        "email": f"test-student-c@{EMAIL_DOMAIN}",
        "first_name": "TEST",
        "last_name": "Student C",
        "classroom": "grade-3",
    },
    {
        "email": f"test-student-d@{EMAIL_DOMAIN}",
        "first_name": "TEST",
        "last_name": "Student D",
        "classroom": "grade-3",
    },
    {
        "email": f"test-student-e@{EMAIL_DOMAIN}",
        "first_name": "TEST",
        "last_name": "Student E",
        "classroom": "grade-5",
    },
    {
        "email": f"test-student-f@{EMAIL_DOMAIN}",
        "first_name": "TEST",
        "last_name": "Student F",
        "classroom": "grade-5",
    },
    {
        "email": f"test-student-g@{EMAIL_DOMAIN}",
        "first_name": "TEST",
        "last_name": "Student G",
        "classroom": "grade-5",
    },
    {
        "email": f"test-student-h@{EMAIL_DOMAIN}",
        "first_name": "TEST",
        "last_name": "Student H",
        "classroom": "grade-5",
    },
]

CLASSROOMS: list[dict[str, str]] = [
    {"key": "grade-3", "slug": "test-classroom-grade-3", "name": "TEST Classroom Grade 3"},
    {"key": "grade-5", "slug": "test-classroom-grade-5", "name": "TEST Classroom Grade 5"},
]


def login_emails() -> list[str]:
    return [ADMIN["email"], *[f["email"] for f in FACULTY], *[m["email"] for m in MADRICHIM]]


def all_sandbox_emails() -> list[str]:
    return [*login_emails(), *[s["email"] for s in STUDENTS]]
