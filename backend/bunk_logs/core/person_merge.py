"""Merge duplicate Person records by re-pointing FKs from loser to winner."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Literal

from django.db import transaction
from django.utils import timezone

from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import CamperDayState
from bunk_logs.core.models import Flag
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.notes.models import Observation
from bunk_logs.notes.models import ObservationArchive
from bunk_logs.notes.models import ObservationReadReceipt
from bunk_logs.notes.models import ObservationRecipient
from bunk_logs.notes.models import ObservationReply
from bunk_logs.notes.models import ObservationSubject


@dataclass
class MergeAction:
    model: str
    description: str
    count: int = 1


@dataclass
class MergePlan:
    winner_id: int
    loser_id: int
    actions: list[MergeAction] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.blockers


def _count(qs) -> int:
    return qs.count()


def plan_person_merge(*, winner: Person, loser: Person, force_user: bool = False) -> MergePlan:
    """Dry-run plan for merging ``loser`` into ``winner``."""
    plan = MergePlan(winner_id=winner.pk, loser_id=loser.pk)

    if winner.organization_id != loser.organization_id:
        plan.blockers.append(
            f"Organization mismatch: winner org={winner.organization_id}, "
            f"loser org={loser.organization_id}",
        )
        return plan

    if winner.pk == loser.pk:
        plan.blockers.append("winner and loser must be different Person records")
        return plan

    winner_cm = str(winner.external_ids.get("campminder_id") or "").strip()
    loser_cm = str(loser.external_ids.get("campminder_id") or "").strip()
    if winner_cm and loser_cm and winner_cm != loser_cm:
        plan.blockers.append(
            f"Both persons have different campminder_id values "
            f"({winner_cm!r} vs {loser_cm!r}); resolve manually first",
        )

    if winner.user_id and loser.user_id and winner.user_id != loser.user_id:
        if force_user:
            plan.actions.append(MergeAction(
                "Person.user",
                f"unlink User {loser.user_id} from loser (keep winner's User {winner.user_id})",
            ))
        else:
            plan.blockers.append(
                f"Both persons are linked to different Users "
                f"({winner.user_id} vs {loser.user_id}); unlink loser or pass --force-user",
            )

    for membership in Membership.all_objects.filter(person=loser):
        conflict = Membership.all_objects.filter(
            program=membership.program,
            person=winner,
            role=membership.role,
        ).exists()
        if conflict:
            plan.actions.append(MergeAction(
                "Membership",
                f"deactivate duplicate {membership.role} on program {membership.program_id}",
            ))
        else:
            plan.actions.append(MergeAction(
                "Membership",
                f"re-point {membership.role} on program {membership.program_id}",
            ))

    for agm in AssignmentGroupMembership.all_objects.filter(person=loser):
        conflict = AssignmentGroupMembership.all_objects.filter(
            group=agm.group,
            person=winner,
            role_in_group=agm.role_in_group,
        ).exists()
        if conflict:
            plan.actions.append(MergeAction(
                "AssignmentGroupMembership",
                f"deactivate duplicate {agm.role_in_group} in group {agm.group_id}",
            ))
        else:
            plan.actions.append(MergeAction(
                "AssignmentGroupMembership",
                f"re-point {agm.role_in_group} in group {agm.group_id}",
            ))

    for label, qs in (
        ("Reflection.subject", Reflection.all_objects.filter(subject=loser)),
        ("Reflection.author", Reflection.all_objects.filter(author=loser)),
    ):
        n = _count(qs)
        if n:
            plan.actions.append(MergeAction(label, f"re-point {n} row(s)", count=n))

    for label, qs in (
        ("Observation.author", Observation.all_objects.filter(author=loser)),
        ("ObservationReply.author", ObservationReply.objects.filter(author=loser)),
    ):
        n = _count(qs)
        if n:
            plan.actions.append(MergeAction(label, f"re-point {n} row(s)", count=n))

    for label, model, fk in (
        ("ObservationSubject", ObservationSubject, "subject"),
        ("ObservationRecipient", ObservationRecipient, "person"),
        ("ObservationReadReceipt", ObservationReadReceipt, "person"),
        ("ObservationArchive", ObservationArchive, "person"),
    ):
        n = _count(model.objects.filter(**{fk: loser}))
        if n:
            plan.actions.append(MergeAction(label, f"re-point or dedupe {n} row(s)", count=n))

    n = _count(CamperDayState.all_objects.filter(camper=loser))
    if n:
        plan.actions.append(MergeAction("CamperDayState", f"re-point or drop {n} row(s)", count=n))

    n = _count(Order.all_objects.filter(subject=loser))
    if n:
        plan.actions.append(MergeAction("Order.subject", f"re-point {n} row(s)", count=n))

    n = _count(Flag.all_objects.filter(subject_camper=loser))
    if n:
        plan.actions.append(MergeAction("Flag", f"re-point {n} row(s)", count=n))

    if not winner.user_id and loser.user_id:
        plan.actions.append(MergeAction("Person.user", f"link User {loser.user_id} to winner"))

    if loser_cm and not winner_cm:
        plan.actions.append(MergeAction(
            "Person.external_ids",
            f"copy campminder_id={loser_cm!r} onto winner",
        ))

    plan.actions.append(MergeAction("Person", f"delete Person {loser.pk}"))
    return plan


@dataclass
class DiscardPlan:
    person_id: int
    actions: list[MergeAction] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    impact_counts: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.blockers


@dataclass
class LoserSpec:
    person_id: int
    strategy: Literal["repoint", "discard"]
    force_user: bool = False


@dataclass
class DedupePlan:
    winner_id: int
    losers: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(entry.get("ok") for entry in self.losers)


def serialize_merge_plan(plan: MergePlan) -> dict:
    return {
        "ok": plan.ok,
        "winner_id": plan.winner_id,
        "loser_id": plan.loser_id,
        "actions": [
            {"model": action.model, "description": action.description, "count": action.count}
            for action in plan.actions
        ],
        "blockers": list(plan.blockers),
    }


def serialize_discard_plan(plan: DiscardPlan) -> dict:
    return {
        "ok": plan.ok,
        "person_id": plan.person_id,
        "actions": [
            {"model": action.model, "description": action.description, "count": action.count}
            for action in plan.actions
        ],
        "blockers": list(plan.blockers),
        "impact_counts": dict(plan.impact_counts),
    }


def person_impact_counts(person: Person) -> dict[str, int]:
    return {
        "reflections_as_subject": _count(Reflection.all_objects.filter(subject=person)),
        "reflections_as_author": _count(Reflection.all_objects.filter(author=person)),
        "observations_as_author": _count(Observation.all_objects.filter(author=person)),
        "observation_replies_as_author": _count(ObservationReply.objects.filter(author=person)),
        "memberships_active": _count(Membership.all_objects.filter(person=person, is_active=True)),
        "group_memberships_active": _count(
            AssignmentGroupMembership.all_objects.filter(person=person, is_active=True),
        ),
        "orders_as_subject": _count(Order.all_objects.filter(subject=person)),
        "flags_as_camper": _count(Flag.all_objects.filter(subject_camper=person)),
    }


def plan_discard_person(*, person: Person, confirm_destructive: bool = False) -> DiscardPlan:
    """Dry-run plan for discarding a duplicate Person without repointing to a winner."""
    plan = DiscardPlan(person_id=person.pk)
    plan.impact_counts = person_impact_counts(person)

    if plan.impact_counts["reflections_as_subject"] > 0 and not confirm_destructive:
        plan.blockers.append(
            f"Person is subject of {plan.impact_counts['reflections_as_subject']} reflection(s); "
            "confirm_destructive required to delete",
        )

    n_memberships = _count(Membership.all_objects.filter(person=person, is_active=True))
    if n_memberships:
        plan.actions.append(MergeAction(
            "Membership",
            f"deactivate {n_memberships} active membership(s)",
            count=n_memberships,
        ))

    n_group = _count(AssignmentGroupMembership.all_objects.filter(person=person, is_active=True))
    if n_group:
        plan.actions.append(MergeAction(
            "AssignmentGroupMembership",
            f"deactivate {n_group} active group membership(s)",
            count=n_group,
        ))

    if person.user_id:
        plan.actions.append(MergeAction("Person.user", f"unlink User {person.user_id}"))

    for label, key in (
        ("Reflection.subject", "reflections_as_subject"),
        ("Reflection.author", "reflections_as_author"),
        ("Observation.author", "observations_as_author"),
        ("ObservationReply.author", "observation_replies_as_author"),
    ):
        count = plan.impact_counts[key]
        if count:
            plan.actions.append(MergeAction(label, f"affected on delete ({count} row(s))", count=count))

    plan.actions.append(MergeAction("Person", f"delete Person {person.pk}"))
    return plan


def _soft_deactivate_memberships(*, person: Person, today) -> None:
    for membership in Membership.all_objects.filter(person=person, is_active=True):
        membership.is_active = False
        if not membership.end_date:
            membership.end_date = today
        membership.save(update_fields=["is_active", "end_date"])

    for agm in AssignmentGroupMembership.all_objects.filter(person=person, is_active=True):
        agm.is_active = False
        if not agm.end_date:
            agm.end_date = today
        agm.save(update_fields=["is_active", "end_date"])


def discard_person(*, person: Person, confirm_destructive: bool = False) -> DiscardPlan:
    """Discard a Person without merging content to a winner."""
    plan = plan_discard_person(person=person, confirm_destructive=confirm_destructive)
    if plan.blockers:
        raise ValueError("; ".join(plan.blockers))

    today = timezone.localdate()
    _soft_deactivate_memberships(person=person, today=today)
    if person.user_id:
        person.user = None
        person.save(update_fields=["user"])
    person.delete()
    return plan


def plan_dedupe(
    *,
    winner: Person,
    loser_specs: list[LoserSpec],
    confirm_destructive: bool = False,
) -> DedupePlan:
    """Dry-run plan for deduping multiple losers into one winner."""
    dedupe = DedupePlan(winner_id=winner.pk)
    for spec in loser_specs:
        if spec.person_id == winner.pk:
            dedupe.losers.append({
                "person_id": spec.person_id,
                "strategy": spec.strategy,
                "ok": False,
                "actions": [],
                "blockers": ["winner cannot also be a loser"],
                "impact_counts": {},
            })
            continue

        try:
            loser = Person.all_objects.get(pk=spec.person_id, organization=winner.organization)
        except Person.DoesNotExist:
            dedupe.losers.append({
                "person_id": spec.person_id,
                "strategy": spec.strategy,
                "ok": False,
                "actions": [],
                "blockers": [f"Person {spec.person_id} not found in org"],
                "impact_counts": {},
            })
            continue

        if spec.strategy == "discard":
            discard_plan = plan_discard_person(
                person=loser,
                confirm_destructive=confirm_destructive,
            )
            dedupe.losers.append({
                "person_id": spec.person_id,
                "strategy": spec.strategy,
                **serialize_discard_plan(discard_plan),
            })
        else:
            merge_plan = plan_person_merge(
                winner=winner,
                loser=loser,
                force_user=spec.force_user,
            )
            entry = serialize_merge_plan(merge_plan)
            entry["person_id"] = spec.person_id
            entry["strategy"] = spec.strategy
            entry["impact_counts"] = person_impact_counts(loser)
            dedupe.losers.append(entry)

    return dedupe


@transaction.atomic
def dedupe_persons(
    *,
    winner: Person,
    loser_specs: list[LoserSpec],
    confirm_destructive: bool = False,
) -> DedupePlan:
    """Apply dedupe for all losers into winner."""
    plan = plan_dedupe(
        winner=winner,
        loser_specs=loser_specs,
        confirm_destructive=confirm_destructive,
    )
    if not plan.ok:
        blockers = [
            blocker
            for entry in plan.losers
            for blocker in entry.get("blockers", [])
        ]
        raise ValueError("; ".join(blockers) if blockers else "dedupe blocked")

    preview = plan
    for spec in loser_specs:
        if spec.person_id == winner.pk:
            continue
        loser = Person.all_objects.get(pk=spec.person_id, organization=winner.organization)
        if spec.strategy == "discard":
            discard_person(person=loser, confirm_destructive=confirm_destructive)
        else:
            merge_persons(winner=winner, loser=loser, force_user=spec.force_user)
            winner.refresh_from_db()

    return preview


def _merge_memberships(*, winner: Person, loser: Person) -> int:
    moved = 0
    for membership in list(Membership.all_objects.filter(person=loser)):
        conflict = Membership.all_objects.filter(
            program=membership.program,
            person=winner,
            role=membership.role,
        ).first()
        if conflict:
            if membership.is_active and not conflict.is_active:
                conflict.is_active = True
                conflict.save(update_fields=["is_active"])
            membership.is_active = False
            membership.save(update_fields=["is_active"])
        else:
            membership.person = winner
            membership.save(update_fields=["person"])
            moved += 1
    return moved


def _merge_assignment_group_memberships(*, winner: Person, loser: Person) -> int:
    moved = 0
    for agm in list(AssignmentGroupMembership.all_objects.filter(person=loser)):
        conflict = AssignmentGroupMembership.all_objects.filter(
            group=agm.group,
            person=winner,
            role_in_group=agm.role_in_group,
        ).first()
        if conflict:
            if agm.is_active and not conflict.is_active:
                conflict.is_active = True
                conflict.save(update_fields=["is_active"])
            agm.is_active = False
            agm.save(update_fields=["is_active"])
        else:
            agm.person = winner
            agm.save(update_fields=["person"])
            moved += 1
    return moved


def _repoint_fk(model, *, field: str, winner: Person, loser: Person) -> int:
    return model.objects.filter(**{field: loser}).update(**{field: winner})


def _merge_observation_m2m(*, model, fk: str, winner: Person, loser: Person) -> int:
    moved = 0
    for row in list(model.objects.filter(**{fk: loser})):
        observation_id = row.observation_id
        if model.objects.filter(observation_id=observation_id, **{fk: winner}).exists():
            row.delete()
        else:
            setattr(row, fk, winner)
            row.save(update_fields=[fk])
            moved += 1
    return moved


def _merge_camper_day_states(*, winner: Person, loser: Person) -> int:
    moved = 0
    for state in list(CamperDayState.all_objects.filter(camper=loser)):
        if CamperDayState.all_objects.filter(
            organization=state.organization,
            camper=winner,
            date=state.date,
        ).exists():
            state.delete()
        else:
            state.camper = winner
            state.save(update_fields=["camper"])
            moved += 1
    return moved


@transaction.atomic
def merge_persons(
    *,
    winner: Person,
    loser: Person,
    force_user: bool = False,
) -> MergePlan:
    """Merge ``loser`` into ``winner``. Raises ValueError when blocked."""
    plan = plan_person_merge(winner=winner, loser=loser, force_user=force_user)
    if plan.blockers:
        raise ValueError("; ".join(plan.blockers))

    if force_user and winner.user_id and loser.user_id and winner.user_id != loser.user_id:
        loser.user = None
        loser.save(update_fields=["user"])

    _merge_memberships(winner=winner, loser=loser)
    _merge_assignment_group_memberships(winner=winner, loser=loser)
    Reflection.all_objects.filter(subject=loser).update(subject=winner)
    Reflection.all_objects.filter(author=loser).update(author=winner)
    Observation.all_objects.filter(author=loser).update(author=winner)
    ObservationReply.objects.filter(author=loser).update(author=winner)
    _merge_observation_m2m(model=ObservationSubject, fk="subject", winner=winner, loser=loser)
    _merge_observation_m2m(model=ObservationRecipient, fk="person", winner=winner, loser=loser)
    _merge_observation_m2m(model=ObservationReadReceipt, fk="person", winner=winner, loser=loser)
    _merge_observation_m2m(model=ObservationArchive, fk="person", winner=winner, loser=loser)
    _merge_camper_day_states(winner=winner, loser=loser)
    Order.all_objects.filter(subject=loser).update(subject=winner)
    Flag.all_objects.filter(subject_camper=loser).update(subject_camper=winner)

    if not winner.user_id and loser.user_id:
        winner.user = loser.user
        loser.user = None
        loser.save(update_fields=["user"])

    merged_ids = {**loser.external_ids, **winner.external_ids}
    if merged_ids != winner.external_ids:
        winner.external_ids = merged_ids
    for attr in ("email", "preferred_name", "date_of_birth"):
        if not getattr(winner, attr) and getattr(loser, attr):
            setattr(winner, attr, getattr(loser, attr))

    winner.save()
    loser.delete()
    return plan
