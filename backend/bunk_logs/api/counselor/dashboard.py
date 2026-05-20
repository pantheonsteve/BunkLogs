"""``GET /api/v1/counselor/dashboard/`` — Story 2 + Story 9 (all set).

Returns the three-section payload the counselor mobile app paints below
the date header: camper reflections coverage, self-reflection state, and
open requests.

State computation:

- ``camper_reflections``: count of campers (excluding off-camp) with a
  submitted reflection for today's period.
- ``self_reflection``: viewer's own daily self-reflection for today, with
  ``day_off`` treated as "complete" (Story 5 criterion 3).
- ``requests``: open Orders + MaintenanceTickets the viewer or any
  co-counselor submitted on the viewer's bunks (decision C4).

All-set (Story 9 criterion 1) is true iff both camper-reflections and
self-reflection sections are "complete". The Requests section is reactive,
not required, and does NOT affect all-set (Story 9 criterion 2).

Caching: a 30-second per-(org, viewer, day) TTL covers the cross-counselor
freshness contract in Story 2 criterion 5. Read endpoints don't bust the
cache; write endpoints in 7_6c will bump the per-viewer version key.
"""

from __future__ import annotations

import hashlib
from datetime import date as date_type  # noqa: TC003 - used in helper type hints

from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.state_machine import OrderStateMachine
from bunk_logs.core.time_utils import get_org_timezone
from bunk_logs.core.time_utils import get_rollover_hour

from .common import bunk_camper_persons
from .common import camper_reflection_template
from .common import co_counselor_person_ids
from .common import counselor_self_template
from .common import is_day_off_answer
from .common import latest_camper_reflection_per_subject
from .common import latest_self_reflection
from .common import off_camp_camper_ids
from .common import viewer_bunk_groups
from .common import viewer_or_403

DASHBOARD_CACHE_TTL_SECONDS = 30
OPEN_STATUSES: tuple[str, ...] = (OrderStateMachine.NEW, OrderStateMachine.IN_PROGRESS)


def _section_state(*, covered: int, total: int) -> str:
    if total == 0:
        return "complete"
    if covered == 0:
        return "none"
    if covered >= total:
        return "complete"
    return "in_progress"


def _cache_key(viewer_id: int, organization_id: int, today: date_type) -> str:
    raw = f"counselor_dashboard:{organization_id}:{viewer_id}:{today.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:48]


class CounselorDashboardView(APIView):
    """Three-section counselor dashboard payload."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        org = ctx.organization
        today = ctx.today

        # Honor an opt-out for tests + ops debugging. Production clients never
        # set this; the dashboard auto-refreshes on a 30s interval.
        skip_cache = request.query_params.get("nocache") in {"1", "true"}
        cache_key = _cache_key(viewer.id, org.id, today)
        if not skip_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

        # Pick the viewer's "primary" program. Counselors in v1 are scoped to
        # one program; if a person has multiple active memberships we take the
        # most recent so the dashboard at least renders.
        primary_membership = (
            Membership.objects.filter(person=viewer, is_active=True)
            .select_related("program")
            .order_by("-created_at")
            .first()
        )
        if primary_membership is None or primary_membership.program is None:
            payload = self._empty_payload(today, org)
            cache.set(cache_key, payload, DASHBOARD_CACHE_TTL_SECONDS)
            return Response(payload)
        program = primary_membership.program

        bunks = viewer_bunk_groups(viewer)
        camper_section = self._camper_section(org, program, viewer, bunks, today)
        self_section = self._self_section(viewer, org, program, today)
        requests_section = self._requests_section(org, program, viewer, bunks)

        all_set = (
            camper_section["state"] == "complete"
            and self_section["state"] == "complete"
        )

        payload = {
            "today": today.isoformat(),
            "rollover_hour": get_rollover_hour(org),
            "timezone": str(get_org_timezone(org)),
            "program": {
                "id": program.id,
                "slug": program.slug,
                "name": program.name,
            },
            "all_set": all_set,
            "sections": {
                "camper_reflections": camper_section,
                "self_reflection": self_section,
                "requests": requests_section,
            },
        }
        cache.set(cache_key, payload, DASHBOARD_CACHE_TTL_SECONDS)
        return Response(payload)

    def _empty_payload(self, today: date_type, org) -> dict:
        return {
            "today": today.isoformat(),
            "rollover_hour": get_rollover_hour(org),
            "timezone": str(get_org_timezone(org)),
            "program": None,
            "all_set": False,
            "sections": {
                "camper_reflections": {
                    "state": "complete",
                    "covered": 0,
                    "total": 0,
                    "off_camp": 0,
                    "bunk_count": 0,
                },
                "self_reflection": {
                    "state": "complete",
                    "submitted": False,
                    "reflection_id": None,
                    "submitted_at": None,
                    "is_day_off": False,
                    "editable": False,
                    "template": None,
                },
                "requests": {
                    "state": "none",
                    "open_count": 0,
                    "by_type": {"camper_care": 0, "maintenance": 0},
                },
            },
        }

    def _camper_section(self, org, program, viewer: Person, bunks, today) -> dict:
        if not bunks:
            return {
                "state": "complete",
                "covered": 0,
                "total": 0,
                "off_camp": 0,
                "bunk_count": 0,
            }

        roster_by_bunk = bunk_camper_persons(bunks)
        all_camper_ids: set[int] = set()
        for campers in roster_by_bunk.values():
            all_camper_ids.update(p.id for p in campers)

        off_camp_ids = off_camp_camper_ids(org, today, camper_ids=all_camper_ids)
        expected_ids = all_camper_ids - off_camp_ids
        total = len(expected_ids)

        template = camper_reflection_template(org, program)
        if template is None or total == 0:
            return {
                "state": "complete",
                "covered": 0,
                "total": total,
                "off_camp": len(off_camp_ids),
                "bunk_count": len(bunks),
            }

        # Daily cadence by definition for the bunk roster template — period
        # collapses to (today, today) without needing the cadence helper.
        reflections = latest_camper_reflection_per_subject(
            template, bunks, today, today,
        )
        covered = sum(1 for sid in expected_ids if sid in reflections)

        return {
            "state": _section_state(covered=covered, total=total),
            "covered": covered,
            "total": total,
            "off_camp": len(off_camp_ids),
            "bunk_count": len(bunks),
        }

    def _self_section(self, viewer: Person, org, program: Program, today) -> dict:
        template = counselor_self_template(viewer, org, program)
        if template is None:
            # No counselor self-reflection template configured — section is
            # implicitly "complete" so it doesn't block all-set.
            return {
                "state": "complete",
                "submitted": False,
                "reflection_id": None,
                "submitted_at": None,
                "is_day_off": False,
                "editable": False,
                "template": None,
            }

        reflection = latest_self_reflection(viewer, template, today, today)
        submitted = reflection is not None
        return {
            "state": "complete" if submitted else "none",
            "submitted": submitted,
            "reflection_id": reflection.id if reflection else None,
            "submitted_at": reflection.submitted_at.isoformat() if reflection and reflection.submitted_at else None,
            "is_day_off": is_day_off_answer(reflection),
            "editable": submitted,
            "template": {
                "id": template.id,
                "slug": template.slug,
                "name": template.name,
                "version": template.version,
            },
        }

    def _requests_section(self, org, program, viewer: Person, bunks) -> dict:
        # "My + my co-counselors' open requests" (decision C4). Without bunks
        # the viewer has no co-counselors; they still see their own requests.
        co_ids = co_counselor_person_ids(viewer, bunks)
        eligible_person_ids = list(co_ids | {viewer.id})

        # ``submitted_by`` is a Membership FK; gather the membership IDs for
        # any of the eligible Persons in this program. We do this in one
        # round-trip and reuse for both Orders and Maintenance tickets.
        eligible_membership_ids = list(
            Membership.all_objects.filter(
                person_id__in=eligible_person_ids,
                program=program,
            ).values_list("id", flat=True),
        )
        if not eligible_membership_ids:
            return {
                "state": "none",
                "open_count": 0,
                "by_type": {"camper_care": 0, "maintenance": 0},
            }

        camper_care_count = Order.all_objects.filter(
            organization=org,
            program=program,
            submitted_by_id__in=eligible_membership_ids,
            status__in=OPEN_STATUSES,
        ).count()
        maintenance_count = MaintenanceTicket.all_objects.filter(
            organization=org,
            program=program,
            submitted_by_id__in=eligible_membership_ids,
            status__in=OPEN_STATUSES,
        ).count()

        total = camper_care_count + maintenance_count
        return {
            # Requests section never reports "complete" (Story 9 criterion 2).
            "state": "in_progress" if total else "none",
            "open_count": total,
            "by_type": {
                "camper_care": camper_care_count,
                "maintenance": maintenance_count,
            },
        }
