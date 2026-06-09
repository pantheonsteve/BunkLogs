"""Admin People dedupe — preview and apply Person merges from the UI."""

from __future__ import annotations

from typing import Any

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core import audit as audit_module
from bunk_logs.core.models import Person
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser
from bunk_logs.core.person_merge import LoserSpec
from bunk_logs.core.person_merge import dedupe_persons
from bunk_logs.core.person_merge import plan_dedupe

from .common import viewer_or_403
from .people import _get_person_or_404
from .people import _not_found
from .people import _person_snapshot
from .people import _serialize_person


def _parse_loser_specs(raw: Any) -> tuple[list[LoserSpec] | None, str | None]:
    if not isinstance(raw, list) or not raw:
        return None, "losers must be a non-empty list"

    specs: list[LoserSpec] = []
    for item in raw:
        if not isinstance(item, dict):
            return None, "each loser entry must be an object"
        person_id = item.get("person_id")
        strategy = (item.get("strategy") or "repoint").strip().lower()
        if not isinstance(person_id, int):
            return None, "each loser must include integer person_id"
        if strategy not in {"repoint", "discard"}:
            return None, f"invalid strategy {strategy!r}; use repoint or discard"
        specs.append(LoserSpec(
            person_id=person_id,
            strategy=strategy,  # type: ignore[arg-type]
            force_user=bool(item.get("force_user")),
        ))
    return specs, None


def _parse_payload(data: dict) -> tuple[int | None, list[LoserSpec] | None, bool, str | None, str | None]:
    winner_id = data.get("winner_id")
    if not isinstance(winner_id, int):
        return None, None, False, None, "winner_id is required"

    loser_specs, loser_err = _parse_loser_specs(data.get("losers"))
    if loser_err:
        return None, None, False, None, loser_err

    reason = (data.get("reason") or "").strip()
    confirm_destructive = bool(data.get("confirm_destructive"))
    return winner_id, loser_specs, confirm_destructive, reason, None


def _build_response(*, ctx, winner: Person, loser_specs: list[LoserSpec], plan, ok: bool) -> dict:
    loser_ids = [spec.person_id for spec in loser_specs]
    persons = {
        p.id: _serialize_person(p, include_memberships=True)
        for p in Person.all_objects.filter(
            pk__in=[winner.pk, *loser_ids],
            organization=ctx.organization,
        )
    }
    return {
        "ok": ok,
        "winner_id": winner.pk,
        "winner": persons.get(winner.pk),
        "losers": [persons.get(spec.person_id) for spec in loser_specs if persons.get(spec.person_id)],
        "plans": plan.losers,
    }


class AdminPeopleDedupePreviewView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        data = request.data or {}
        winner_id, loser_specs, confirm_destructive, _, err = _parse_payload(data)
        if err:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)

        winner = _get_person_or_404(ctx, winner_id)
        if winner is None:
            return _not_found("Person")

        plan = plan_dedupe(
            winner=winner,
            loser_specs=loser_specs,
            confirm_destructive=confirm_destructive,
        )
        payload = _build_response(
            ctx=ctx,
            winner=winner,
            loser_specs=loser_specs,
            plan=plan,
            ok=plan.ok,
        )
        if not plan.ok:
            return Response(payload, status=status.HTTP_409_CONFLICT)
        return Response(payload)


class AdminPeopleDedupeApplyView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        data = request.data or {}
        winner_id, loser_specs, confirm_destructive, reason, err = _parse_payload(data)
        if err:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)
        if not reason:
            return Response({"detail": "reason is required."}, status=status.HTTP_400_BAD_REQUEST)

        winner = _get_person_or_404(ctx, winner_id)
        if winner is None:
            return _not_found("Person")

        preview = plan_dedupe(
            winner=winner,
            loser_specs=loser_specs,
            confirm_destructive=confirm_destructive,
        )
        if not preview.ok:
            payload = _build_response(
                ctx=ctx,
                winner=winner,
                loser_specs=loser_specs,
                plan=preview,
                ok=False,
            )
            return Response(payload, status=status.HTTP_409_CONFLICT)

        before = _person_snapshot(winner)
        actor = ctx.membership or request.user

        try:
            with transaction.atomic():
                applied = dedupe_persons(
                    winner=winner,
                    loser_specs=loser_specs,
                    confirm_destructive=confirm_destructive,
                )
                winner.refresh_from_db()
                audit_module.override_edit(
                    actor,
                    winner,
                    before,
                    _person_snapshot(winner),
                    reason=reason,
                    content_type="person_dedupe",
                    metadata={
                        "winner_id": winner.pk,
                        "loser_specs": [
                            {
                                "person_id": spec.person_id,
                                "strategy": spec.strategy,
                                "force_user": spec.force_user,
                            }
                            for spec in loser_specs
                        ],
                        "plans": applied.losers,
                    },
                )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        winner = _get_person_or_404(ctx, winner_id)
        payload = _build_response(
            ctx=ctx,
            winner=winner,
            loser_specs=loser_specs,
            plan=applied,
            ok=True,
        )
        payload["winner"] = _serialize_person(winner, include_memberships=True)
        return Response(payload)
