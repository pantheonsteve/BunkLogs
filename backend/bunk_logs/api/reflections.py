from __future__ import annotations

import calendar
import hashlib
from datetime import date
from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Case
from django.db.models import Exists
from django.db.models import IntegerField
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import When
from rest_framework import permissions
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from bunk_logs.core import audit as audit_module
from bunk_logs.core.assignment_resolution import list_required_assignments_for
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment
from bunk_logs.core.models import TranslationRecord
from bunk_logs.core.models import reflection_snapshot
from bunk_logs.core.models import validate_reflection_answers
from bunk_logs.core.permissions import is_super_admin
from bunk_logs.core.program_scope import operational_assignment_groups_qs
from bunk_logs.core.program_scope import operational_author_groups_qs
from bunk_logs.core.program_scope import operational_memberships_qs
from bunk_logs.core.time_utils import get_today
from bunk_logs.core.translation import enqueue_translation_for_reflection


def _person_for_request(request):
    if not getattr(request, "organization", None) or not request.user.is_authenticated:
        return None
    return Person.objects.filter(user=request.user).first()


def _has_tenant_admin(person: Person) -> bool:
    return Membership.objects.filter(person=person, role="admin", is_active=True).exists()


def _privileged_reflection_actor(request) -> bool:
    """Super Admins (``is_staff`` OR ``is_superuser``) bypass author-only mutation gates."""
    return is_super_admin(request.user)


def _template_matches_program(template: ReflectionTemplate, program: Program) -> bool:
    if template.organization_id and template.organization_id != program.organization_id:
        return False
    return not (template.program_type and template.program_type != program.program_type)


def _may_use_template(request, viewer: Person, program: Program, template: ReflectionTemplate) -> None:
    """Raise ValidationError if viewer may not submit using this template on this program."""
    if program.organization_id != viewer.organization_id:
        raise serializers.ValidationError({"program_slug": "Program is not in your organization."})
    if not _template_matches_program(template, program):
        raise serializers.ValidationError({"template": "Template does not apply to this program."})

    if _privileged_reflection_actor(request) or _has_tenant_admin(viewer):
        return

    if template.role:
        allowed = Membership.objects.filter(
            person=viewer,
            program=program,
            role=template.role,
            is_active=True,
        ).exists()
        if not allowed:
            raise serializers.ValidationError(
                {"template": "Your membership role does not match this template."},
            )
        return

    allowed = Membership.objects.filter(person=viewer, program=program, is_active=True).exists()
    if not allowed:
        raise serializers.ValidationError({"program_slug": "No active membership in this program."})


def _validate_language_coverage(schema: dict, lang: str) -> None:
    fields = schema.get("fields")
    if not isinstance(fields, list):
        raise serializers.ValidationError({"language": "Template schema is invalid."})
    for i, field in enumerate(fields):
        if not isinstance(field, dict):
            continue
        loc = f"field index {i}"
        ftype = field.get("type")
        if ftype == "rating_group":
            labels = field.get("scale_labels") or {}
            if lang not in labels:
                raise serializers.ValidationError(
                    {"language": f'Template scale_labels missing "{lang}" ({loc}).'},
                )
            for j, cat in enumerate(field.get("categories") or []):
                if not isinstance(cat, dict):
                    continue
                clabels = cat.get("labels") or {}
                if lang not in clabels:
                    raise serializers.ValidationError(
                        {"language": f'Template category labels missing "{lang}" ({loc}, category {j}).'},
                    )
        elif ftype == "single_rating":
            labels = field.get("scale_labels") or {}
            if lang not in labels:
                raise serializers.ValidationError(
                    {"language": f'Template scale_labels missing "{lang}" ({loc}).'},
                )
        else:
            prompts = field.get("prompts") or {}
            if lang not in prompts:
                raise serializers.ValidationError(
                    {"language": f'Template prompts missing "{lang}" ({loc}).'},
                )


def _localize_schema(schema: dict, lang: str) -> dict:
    out: dict = {"fields": []}
    for field in schema.get("fields") or []:
        if not isinstance(field, dict):
            continue
        f = dict(field)
        ftype = f.get("type")
        if ftype == "rating_group":
            sl = f.get("scale_labels") or {}
            if lang in sl:
                f["scale_labels"] = {lang: sl[lang]}
            cats = []
            for c in f.get("categories") or []:
                if not isinstance(c, dict):
                    cats.append(c)
                    continue
                nc = dict(c)
                lbls = c.get("labels") or {}
                if lang in lbls:
                    nc["labels"] = {lang: lbls[lang]}
                cats.append(nc)
            f["categories"] = cats
        elif ftype == "single_rating":
            sl = f.get("scale_labels") or {}
            if lang in sl:
                f["scale_labels"] = {lang: sl[lang]}
        else:
            pr = f.get("prompts") or {}
            if lang in pr:
                f["prompts"] = {lang: pr[lang]}
        out["fields"].append(f)
    return out


def _roster_roles_for_template(template: ReflectionTemplate) -> tuple[str, ...]:
    """Which ``AssignmentGroupMembership.role_in_group`` values may submit via a group."""
    if template.subject_mode == "self":
        return ("author", "subject")
    return ("author",)


def _sort_self_templates(templates: list[ReflectionTemplate]) -> list[ReflectionTemplate]:
    return sorted(
        templates,
        key=lambda t: (
            0 if t.organization_id else 1,
            0 if (t.cadence or "daily") == "daily" else 1,
            t.name,
        ),
    )


def _self_templates_from_assignments(
    viewer: Person,
    organization,
    program: Program,
    as_of: date,
) -> list[ReflectionTemplate]:
    """Self templates from active required assignments on ``program``."""
    templates: list[ReflectionTemplate] = []
    for assignment in list_required_assignments_for(viewer, organization, program, as_of):
        if assignment.template.subject_mode == "self":
            templates.append(assignment.template)
    return _sort_self_templates(templates)


def _legacy_self_template_for_program(
    viewer: Person,
    program: Program,
) -> ReflectionTemplate | None:
    """Pre-7_21 fallback: newest active template matching membership role."""
    membership = (
        Membership.objects.filter(person=viewer, program=program, is_active=True)
        .order_by("-created_at")
        .first()
    )
    if membership is None:
        return None
    return (
        ReflectionTemplate.objects.filter(role=membership.role, is_active=True)
        .filter(Q(program_type=program.program_type) | Q(program_type__isnull=True))
        .annotate(
            _org_priority=Case(
                When(organization__isnull=True, then=1),
                default=0,
                output_field=IntegerField(),
            ),
        )
        .order_by("_org_priority", "-version")
        .first()
    )


def _resolve_self_summary_template(
    viewer: Person,
    organization,
    program: Program,
    as_of: date,
) -> ReflectionTemplate | None:
    """Self-reflection template for ``my-summary`` — assignment-aware (Step 7_21)."""
    assigned = _self_templates_from_assignments(viewer, organization, program, as_of)
    if assigned:
        return assigned[0]
    return _legacy_self_template_for_program(viewer, program)


def _my_summary_scope(
    viewer: Person,
    organization,
    today: date,
    program_slug: str | None = None,
) -> tuple[Program | None, ReflectionTemplate | None]:
    """Pick (program, template) for the personal history view.

    When no ``program`` query param is given, prefer the program/template of the
    viewer's most recent self-reflection so a submission from /tasks shows up
    immediately even if another membership was created more recently.
    """
    memberships_qs = operational_memberships_qs(viewer, today=today)
    if program_slug:
        memberships_qs = memberships_qs.filter(program__slug=program_slug)
    memberships = list(memberships_qs.order_by("-created_at"))
    if not memberships:
        return None, None

    if program_slug:
        prog = memberships[0].program
        tpl = _resolve_self_summary_template(viewer, organization, prog, today)
        return prog, tpl

    membership_program_ids = {m.program_id for m in memberships}
    latest_self = (
        Reflection.all_objects.filter(
            subject=viewer,
            author=viewer,
            organization=organization,
            template__subject_mode="self",
        )
        .select_related("template", "program")
        .order_by("-submitted_at")
        .first()
    )
    if latest_self and latest_self.program_id in membership_program_ids:
        prog = latest_self.program
        assigned = _self_templates_from_assignments(viewer, organization, prog, today)
        assigned_ids = {t.id for t in assigned}
        if not assigned or latest_self.template_id in assigned_ids:
            return prog, latest_self.template
        return prog, assigned[0]

    for membership in memberships:
        assigned = _self_templates_from_assignments(
            viewer, organization, membership.program, today,
        )
        if assigned:
            return membership.program, assigned[0]

    prog = memberships[0].program
    return prog, _legacy_self_template_for_program(viewer, prog)


def _current_period(today: date, cadence: str) -> tuple[date, date]:
    """Return (period_start, period_end) for the current period based on cadence."""
    if cadence == "daily":
        return today, today
    if cadence == "weekly":
        monday = today - timedelta(days=today.weekday())
        return monday, monday + timedelta(days=6)
    if cadence == "biweekly":
        monday = today - timedelta(days=today.weekday())
        iso_week = monday.isocalendar()[1]
        period_start = monday if iso_week % 2 == 0 else monday - timedelta(weeks=1)
        return period_start, period_start + timedelta(days=13)
    if cadence == "monthly":
        first = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        return first, date(today.year, today.month, last_day)
    return today, today


def _task_id(template_id: int, group_id: int | None, period_start: date) -> str:
    key = f"{template_id}:{group_id or ''}:{period_start.isoformat()}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _assignment_cadence(assignment: TemplateAssignment) -> str:
    if assignment.cadence_override:
        return assignment.cadence_override
    return assignment.template.cadence or "daily"


def _eligible_groups_for_assignment(
    assignment: TemplateAssignment,
    author_agms: list[AssignmentGroupMembership],
) -> list[AssignmentGroup]:
    """Assignment groups the viewer authors that this assignment applies to."""
    tpl = assignment.template
    allowed_types = set(tpl.assignment_group_types or [])
    if assignment.target_type == TemplateAssignment.TargetType.ASSIGNMENT_GROUP:
        group = assignment.assignment_group
        if group is None or not group.is_active:
            return []
        if any(agm.group_id == group.id for agm in author_agms):
            return [group]
        return []
    return [
        agm.group
        for agm in author_agms
        if agm.group.is_active
        and agm.group.program_id == assignment.program_id
        and (not allowed_types or agm.group.group_type in allowed_types)
    ]


def _roster_subjects_data(
    *,
    viewer: Person,
    template: ReflectionTemplate,
    group: AssignmentGroup,
    subject_persons: list[Person],
    period_start: date,
    period_end: date,
) -> list[dict]:
    person_ids = [p.id for p in subject_persons]
    reflections = list(
        Reflection.all_objects.filter(
            template=template,
            assignment_group=group,
            period_start=period_start,
            period_end=period_end,
            subject_id__in=person_ids,
        ).select_related("author"),
    )
    covered_map: dict[int, Reflection] = {}
    for reflection in reflections:
        if reflection.subject_id not in covered_map:
            covered_map[reflection.subject_id] = reflection

    subjects_data = []
    for person in subject_persons:
        reflection = covered_map.get(person.id)
        covered_by_name = None
        if reflection and reflection.author:
            covered_by_name = reflection.author.full_name
        subjects_data.append({
            "person_id": person.id,
            "name": person.full_name,
            "preferred_name": person.preferred_name or person.first_name,
            "covered": bool(reflection),
            "covered_by_me": bool(reflection and reflection.author_id == viewer.id),
            "reflection_id": reflection.id if reflection else None,
            "covered_by_name": covered_by_name,
        })
    return subjects_data


def _subjects_by_group(group_ids: list[int]) -> dict[int, list[Person]]:
    subject_agms = list(
        AssignmentGroupMembership.objects.filter(
            group_id__in=group_ids,
            role_in_group="subject",
            is_active=True,
        ).select_related("person"),
    )
    subjects_by_group: dict[int, list[Person]] = {}
    for sagm in subject_agms:
        subjects_by_group.setdefault(sagm.group_id, []).append(sagm.person)
    return subjects_by_group


def _tasks_from_required_assignments(
    *,
    viewer: Person,
    organization,
    viewer_memberships: list[Membership],
    author_agms: list[AssignmentGroupMembership],
    today: date,
) -> list[dict]:
    """Build my-tasks rows from active TemplateAssignment audience matches."""
    tasks: list[dict] = []
    seen_keys: set[tuple] = set()

    for membership in viewer_memberships:
        program = membership.program
        if program.organization_id != organization.id:
            continue
        for assignment in list_required_assignments_for(
            viewer, organization, program, today,
        ):
            tpl = assignment.template
            cadence = _assignment_cadence(assignment)
            period_start, period_end = _current_period(today, cadence)
            prog_slug = program.slug

            if tpl.subject_mode == "self":
                group = None
                if assignment.target_type == TemplateAssignment.TargetType.ASSIGNMENT_GROUP:
                    group = assignment.assignment_group
                    if group is None or not group.is_active:
                        continue

                group_id = group.id if group else None
                dedupe_key = (tpl.id, group_id, period_start, program.id)
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)

                existing_qs = Reflection.all_objects.filter(
                    author=viewer,
                    subject=viewer,
                    template=tpl,
                    program=program,
                    period_start=period_start,
                    period_end=period_end,
                    is_complete=True,
                )
                if group_id is not None:
                    # Counselor/legacy self-reflections are stored with no group;
                    # cohort assignments still surface group metadata on the task row.
                    existing_qs = existing_qs.filter(
                        Q(assignment_group_id=group_id) | Q(assignment_group__isnull=True),
                    )
                else:
                    existing_qs = existing_qs.filter(assignment_group__isnull=True)
                existing = existing_qs.order_by("-submitted_at").first()

                assignment_group_payload = None
                if group is not None:
                    assignment_group_payload = {
                        "id": group.id,
                        "name": group.name,
                        "group_type": group.group_type,
                    }

                tasks.append({
                    "id": _task_id(tpl.id, group_id, period_start),
                    "template": ReflectionTemplateSummarySerializer(tpl).data,
                    "assignment_group": assignment_group_payload,
                    "subject_mode": "self",
                    "period": {"start": period_start.isoformat(), "end": period_end.isoformat()},
                    "program_slug": prog_slug,
                    "subjects": [],
                    "completion": {
                        "covered": 1 if existing else 0,
                        "total": 1,
                        "my_count": 1 if existing else 0,
                    },
                    "self_status": {
                        "submitted": bool(existing),
                        "reflection_id": existing.id if existing else None,
                        "submitted_at": existing.submitted_at.isoformat() if existing else None,
                    },
                })
                continue

            if tpl.subject_mode in ("single_subject", "multi_subject"):
                groups = _eligible_groups_for_assignment(assignment, author_agms)
                if not groups:
                    continue
                subjects_by_group = _subjects_by_group([g.id for g in groups])
                for group in groups:
                    subject_persons = subjects_by_group.get(group.id, [])
                    if not subject_persons:
                        continue
                    dedupe_key = (tpl.id, group.id, period_start, program.id)
                    if dedupe_key in seen_keys:
                        continue
                    seen_keys.add(dedupe_key)

                    subjects_data = _roster_subjects_data(
                        viewer=viewer,
                        template=tpl,
                        group=group,
                        subject_persons=subject_persons,
                        period_start=period_start,
                        period_end=period_end,
                    )
                    covered_count = sum(1 for s in subjects_data if s["covered"])
                    my_count = sum(1 for s in subjects_data if s["covered_by_me"])
                    tasks.append({
                        "id": _task_id(tpl.id, group.id, period_start),
                        "template": ReflectionTemplateSummarySerializer(tpl).data,
                        "assignment_group": {
                            "id": group.id,
                            "name": group.name,
                            "group_type": group.group_type,
                        },
                        "subject_mode": tpl.subject_mode,
                        "period": {"start": period_start.isoformat(), "end": period_end.isoformat()},
                        "program_slug": prog_slug,
                        "subjects": subjects_data,
                        "completion": {
                            "covered": covered_count,
                            "total": len(subjects_data),
                            "my_count": my_count,
                        },
                        "self_status": None,
                    })
                continue

            if tpl.subject_mode == "group":
                groups = _eligible_groups_for_assignment(assignment, author_agms)
                for group in groups:
                    dedupe_key = (tpl.id, group.id, period_start, program.id)
                    if dedupe_key in seen_keys:
                        continue
                    seen_keys.add(dedupe_key)

                    existing = (
                        Reflection.all_objects.filter(
                            author=viewer,
                            template=tpl,
                            program=program,
                            subject_group=group,
                            period_start=period_start,
                            period_end=period_end,
                        )
                        .first()
                    )
                    tasks.append({
                        "id": _task_id(tpl.id, group.id, period_start),
                        "template": ReflectionTemplateSummarySerializer(tpl).data,
                        "assignment_group": {
                            "id": group.id,
                            "name": group.name,
                            "group_type": group.group_type,
                        },
                        "subject_mode": "group",
                        "period": {"start": period_start.isoformat(), "end": period_end.isoformat()},
                        "program_slug": prog_slug,
                        "subjects": [],
                        "completion": {
                            "covered": 1 if existing else 0,
                            "total": 1,
                            "my_count": 1 if existing else 0,
                        },
                        "self_status": None,
                    })

    return tasks


def _build_periods(today: date, cadence: str) -> list[tuple[date, date]]:
    """Return (period_start, period_end) tuples, most-recent first, for the summary window."""
    if cadence == "daily":
        return [(today - timedelta(days=i), today - timedelta(days=i)) for i in range(14)]
    if cadence == "weekly":
        monday = today - timedelta(days=today.weekday())
        return [
            (monday - timedelta(weeks=i), monday - timedelta(weeks=i) + timedelta(days=6))
            for i in range(4)
        ]
    if cadence == "biweekly":
        monday = today - timedelta(days=today.weekday())
        iso_week = monday.isocalendar()[1]
        period_start = monday if iso_week % 2 == 0 else monday - timedelta(weeks=1)
        return [
            (period_start - timedelta(weeks=i * 2), period_start - timedelta(weeks=i * 2) + timedelta(days=13))
            for i in range(4)
        ]
    if cadence == "monthly":
        periods = []
        y, m = today.year, today.month
        for _ in range(3):
            last = calendar.monthrange(y, m)[1]
            periods.append((date(y, m, 1), date(y, m, last)))
            m -= 1
            if m == 0:
                m, y = 12, y - 1
        return periods
    # on_demand / unknown: treat as a single open window
    return [(today - timedelta(days=13), today)]


class ReflectionTemplateSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReflectionTemplate
        fields = [
            "id",
            "name",
            "slug",
            "cadence",
            "role",
            "program_type",
            "version",
            "languages",
            "description",
            "supports_privacy",
        ]


class ReflectionSerializer(serializers.ModelSerializer):
    template_meta = ReflectionTemplateSummarySerializer(source="template", read_only=True)
    localized_schema = serializers.SerializerMethodField()
    program_slug = serializers.SlugField(write_only=True, required=False)
    answers = serializers.JSONField()
    translation = serializers.SerializerMethodField()

    def get_translation(self, obj):
        """Embed the latest TranslationRecord state for non-English reflections.

        Returns ``None`` for English content so the frontend can short-circuit
        on a single truthy check. Shape matches Story 44's reader-side state
        machine; ``TranslationDisplay.jsx`` consumes it directly without
        additional reshaping.
        """
        language = getattr(obj, "language", None) or "en"
        if language == "en":
            return None
        record = TranslationRecord.latest_for("reflection", obj.pk)
        if record is None:
            return {
                "status": "pending",
                "source_language": language,
                "target_language": "en",
                "translated_text": "",
                "model_id": "",
                "updated_at": None,
                "attempt_count": 0,
            }
        return {
            "id": str(record.id),
            "status": record.status,
            "source_language": record.source_language,
            "target_language": record.target_language,
            "translated_text": record.translated_text,
            "model_id": record.model_id,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            "attempt_count": record.attempt_count,
        }

    def get_localized_schema(self, obj):
        """Localized template schema for the reflection's saved language.

        Lets a read-only viewer render prompts + answers without a second
        round-trip to ``/api/v1/templates/<id>/``. Only returned when the
        instance is fully hydrated (i.e. has a saved template + language).
        """
        template = getattr(obj, "template", None)
        if template is None or not getattr(template, "schema", None):
            return None
        language = getattr(obj, "language", None) or "en"
        return _localize_schema(template.schema, language)
    subject = serializers.PrimaryKeyRelatedField(
        queryset=Person.all_objects.all(),
        allow_null=True,
        required=False,
    )
    subject_group = serializers.PrimaryKeyRelatedField(
        queryset=AssignmentGroup.all_objects.all(),
        allow_null=True,
        required=False,
    )
    assignment_group = serializers.PrimaryKeyRelatedField(
        queryset=AssignmentGroup.all_objects.all(),
        allow_null=True,
        required=False,
    )
    submission_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Reflection
        fields = [
            "id",
            "organization",
            "program",
            "program_slug",
            "subject",
            "subject_group",
            "author",
            "assignment_group",
            "submission_id",
            "template",
            "template_meta",
            "localized_schema",
            "submitted_by",
            "period_start",
            "period_end",
            "answers",
            "language",
            "team_visibility",
            "is_sensitive",
            "submitted_at",
            "updated_at",
            "is_complete",
            "translation",
        ]
        read_only_fields = [
            "id",
            "organization",
            "program",
            "author",
            "submitted_by",
            "submitted_at",
            "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            self.fields["program_slug"].read_only = True
            self.fields["template"].read_only = True
            self.fields["subject"].read_only = True
            self.fields["subject_group"].read_only = True
            self.fields["assignment_group"].read_only = True
            self.fields["submission_id"].read_only = True

    def validate(self, attrs):
        if self.instance is None and not attrs.get("program_slug"):
            raise serializers.ValidationError({"program_slug": "This field is required."})
        language = attrs.get("language", getattr(self.instance, "language", None) or "en")
        template = attrs.get("template", getattr(self.instance, "template", None))
        answers = attrs.get("answers", getattr(self.instance, "answers", None))
        if template is not None and answers is not None:
            try:
                validate_reflection_answers(template.schema, answers)
            except DjangoValidationError as e:
                raise serializers.ValidationError(e.message_dict if hasattr(e, "message_dict") else str(e))
            _validate_language_coverage(template.schema, language)

        tv = attrs.get(
            "team_visibility",
            getattr(self.instance, "team_visibility", None),
        )
        if (
            tv == Reflection.TeamVisibility.SUPERVISORS_ONLY
            and template is not None
            and not template.supports_privacy
        ):
            raise serializers.ValidationError({
                "team_visibility": (
                    "This template does not support the 'supervisors only' "
                    "privacy flag."
                ),
            })
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        org = request.organization
        viewer = _person_for_request(request)
        if viewer is None or org is None:
            msg = "Missing organization or person profile."
            raise serializers.ValidationError({"detail": msg})
        program_slug = validated_data.pop("program_slug")
        try:
            program = Program.objects.get(slug=program_slug)
        except Program.DoesNotExist as e:
            raise serializers.ValidationError({"program_slug": "Program not found."}) from e
        template = validated_data["template"]

        # Determine subject: explicit (roster mode) or self
        provided_subject = validated_data.pop("subject", None)
        provided_ag = validated_data.pop("assignment_group", None)
        provided_sg = validated_data.pop("subject_group", None)

        if provided_ag is not None:
            roster_roles = _roster_roles_for_template(template)
            in_group = AssignmentGroupMembership.all_objects.filter(
                group=provided_ag,
                person=viewer,
                role_in_group__in=roster_roles,
                is_active=True,
            ).exists()
            if not in_group and not _has_tenant_admin(viewer) and not _privileged_reflection_actor(request):
                raise serializers.ValidationError(
                    {"assignment_group": "You are not a member of this group."},
                )
        else:
            _may_use_template(request, viewer, program, template)

        subject = provided_subject if provided_subject is not None else viewer
        validated_data["organization"] = org
        validated_data["program"] = program
        validated_data["subject"] = subject
        validated_data["author"] = viewer
        validated_data["submitted_by"] = request.user
        if provided_ag is not None:
            validated_data["assignment_group"] = provided_ag
        if provided_sg is not None:
            validated_data["subject_group"] = provided_sg

        try:
            instance = Reflection(**validated_data)
            instance.full_clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, "message_dict") else str(e))
        instance.save()
        return instance

    def update(self, instance, validated_data):
        if instance.is_complete:
            raise serializers.ValidationError({"detail": "Completed reflections cannot be updated."})
        validated_data.pop("program_slug", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        try:
            instance.full_clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, "message_dict") else str(e))
        instance.save()
        return instance


class ReflectionPermission(permissions.BasePermission):
    message = "Organization context or permission missing."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request, "organization", None),
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        viewer = _person_for_request(request)
        if viewer is None:
            return False
        return viewer.id in (obj.subject_id, obj.author_id)


class ReflectionViewSet(viewsets.ModelViewSet):
    serializer_class = ReflectionSerializer
    permission_classes = [ReflectionPermission]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Reflection.objects.select_related(
            "subject", "author", "program", "template", "organization",
            "assignment_group", "subject_group",
        )
        return self._filter_query_params(qs)

    # -- audit-trail hooks (Step 7_4) -------------------------------------
    #
    # ``perform_create`` writes audit.created; ``perform_update`` snapshots
    # the row before the in-place mutation and writes audit.edited iff the
    # save actually changed any audit-tracked field. The actor passed to the
    # audit helpers is the request user's most relevant active Membership in
    # the affected program, falling back to the User row when no membership
    # exists (Super Admins acting outside their org admin row).

    def _audit_actor(self, request, instance):
        person = _person_for_request(request)
        if person is None:
            return request.user if request.user.is_authenticated else None
        membership = (
            Membership.objects.filter(
                person=person, program=instance.program, is_active=True,
            )
            .order_by("-created_at")
            .first()
        )
        if membership is not None:
            return membership
        return request.user

    def perform_create(self, serializer):
        instance = serializer.save()
        audit_module.created(
            self._audit_actor(self.request, instance),
            instance,
            after_state=reflection_snapshot(instance),
            content_type="reflection",
        )
        # Auto-translation (Step 7_5): non-English submissions enqueue a
        # Celery task that fills in TranslationRecord.translated_text and
        # flips status from 'pending' to 'completed'. English submissions
        # short-circuit at the helper.
        enqueue_translation_for_reflection(instance)

    def perform_update(self, serializer):
        # Re-fetch from the DB so the snapshot reflects the pre-mutation row.
        # ``serializer.instance`` shares state with the row being patched.
        before = reflection_snapshot(
            Reflection.objects.get(pk=serializer.instance.pk),
        )
        instance = serializer.save()
        after = reflection_snapshot(instance)
        if before != after:
            audit_module.edited(
                self._audit_actor(self.request, instance),
                instance,
                before,
                after,
                content_type="reflection",
            )
        # Re-translate when the answers / language change. The helper
        # revokes the pending Celery task (if any) before enqueueing the
        # fresh one so we don't race two translations against each other.
        if before.get("answers") != after.get("answers") or before.get("language") != after.get("language"):
            enqueue_translation_for_reflection(instance)

    def _filter_query_params(self, qs):
        p = self.request.query_params
        program_slug = (p.get("program") or "").strip()
        if program_slug:
            qs = qs.filter(program__slug=program_slug)
        tid = (p.get("template") or "").strip()
        if tid.isdigit():
            qs = qs.filter(template_id=int(tid))
        ps_after = (p.get("period_start_after") or "").strip()
        ps_before = (p.get("period_start_before") or "").strip()
        if ps_after:
            qs = qs.filter(period_start__gte=ps_after)
        if ps_before:
            qs = qs.filter(period_start__lte=ps_before)
        mrole = (p.get("membership_role") or "").strip()
        if mrole:
            qs = qs.filter(
                Exists(
                    Membership.objects.filter(
                        person_id=OuterRef("subject_id"),
                        program_id=OuterRef("program_id"),
                        role=mrole,
                    ),
                ),
            )
        subject_id = (p.get("subject") or "").strip()
        if subject_id.isdigit():
            qs = qs.filter(subject_id=int(subject_id))
        author_id = (p.get("author") or "").strip()
        if author_id.isdigit():
            qs = qs.filter(author_id=int(author_id))
        ag_id = (p.get("assignment_group") or "").strip()
        if ag_id.isdigit():
            qs = qs.filter(assignment_group_id=int(ag_id))
        return qs

    def _template_for_me_payload(self, tpl: ReflectionTemplate, language: str, program: Program) -> Response:
        try:
            _validate_language_coverage(tpl.schema, language)
        except serializers.ValidationError as e:
            detail = getattr(e, "detail", str(e))
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)
        payload = ReflectionTemplateSummarySerializer(tpl).data
        payload["schema"] = _localize_schema(tpl.schema, language)
        payload["language"] = language
        payload["program_slug"] = program.slug
        return Response(payload)

    @action(detail=True, methods=["post"], url_path="retry-translation")
    def retry_translation(self, request, pk=None):
        """Story 44 manual retry hook for failed translations.

        Allowed when the reflection author OR an org admin requests it,
        and only when the latest TranslationRecord is in a
        ``failed_retryable`` / ``failed_terminal`` state (no point
        re-enqueueing during a pending run). On success returns the
        latest TranslationRecord payload so the client can surface the
        new ``pending`` state without a follow-up GET.
        """
        instance = self.get_object()
        if (instance.language or "en") == "en":
            return Response(
                {"detail": "Reflection is in English; no translation needed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        record = TranslationRecord.latest_for("reflection", instance.pk)
        retryable_statuses = {
            TranslationRecord.Status.FAILED_RETRYABLE,
            TranslationRecord.Status.FAILED_TERMINAL,
        }
        if record is not None and record.status not in retryable_statuses:
            return Response(
                {
                    "detail": (
                        "Translation is not in a retryable state "
                        f"(current status: {record.status})."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )
        # Reset the attempt counter so the fresh enqueue gets the full
        # three-attempt budget per the spec.
        if record is not None:
            TranslationRecord.all_objects.filter(pk=record.pk).update(
                attempt_count=0,
                status=TranslationRecord.Status.PENDING,
                last_error="",
            )
        enqueue_translation_for_reflection(instance)
        return Response(
            self.get_serializer(instance).data, status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=["get"], url_path="template-for-me")
    def template_for_me(self, request):
        viewer = _person_for_request(request)
        if viewer is None:
            return Response({"detail": "Person profile required."}, status=status.HTTP_403_FORBIDDEN)
        program_slug = (request.query_params.get("program") or "").strip()
        language = (request.query_params.get("language") or "en").strip()

        # Direct template ID mode (used by tasks home screen pre-fill)
        template_id_raw = (request.query_params.get("template") or "").strip()
        if template_id_raw.isdigit() and program_slug:
            try:
                prog = Program.objects.get(slug=program_slug)
            except Program.DoesNotExist:
                return Response({"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND)
            if prog.organization_id != viewer.organization_id:
                return Response({"detail": "Program is not in your organization."}, status=status.HTTP_403_FORBIDDEN)
            try:
                tpl = ReflectionTemplate.objects.get(pk=int(template_id_raw), is_active=True)
            except ReflectionTemplate.DoesNotExist:
                return Response({"detail": "Template not found."}, status=status.HTTP_404_NOT_FOUND)
            if tpl.organization_id and tpl.organization_id != viewer.organization_id:
                return Response({"detail": "Template not in your organization."}, status=status.HTTP_403_FORBIDDEN)
            return self._template_for_me_payload(tpl, language, prog)

        elevated = _has_tenant_admin(viewer) or _privileged_reflection_actor(request)

        if elevated and program_slug:
            try:
                prog = Program.objects.get(slug=program_slug)
            except Program.DoesNotExist:
                return Response({"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND)
            if prog.organization_id != viewer.organization_id:
                return Response({"detail": "Program is not in your organization."}, status=status.HTTP_403_FORBIDDEN)
            role_for_tpl = (request.query_params.get("role") or "").strip()
            if not role_for_tpl:
                m_on_prog = (
                    Membership.objects.filter(person=viewer, program=prog, is_active=True)
                    .order_by("-created_at")
                    .first()
                )
                if m_on_prog:
                    role_for_tpl = m_on_prog.role
                else:
                    return Response(
                        {
                            "detail": (
                                "role query parameter is required when you have no active membership on this program."
                            ),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            tpl = (
                ReflectionTemplate.objects.filter(role=role_for_tpl, is_active=True)
                .filter(Q(program_type=prog.program_type) | Q(program_type__isnull=True))
                # Prefer org-specific templates over global fallbacks. Step 7_6
                # ships a global counselor-self-reflection template that orgs
                # may shadow with a customized version; ``org_priority`` is 0
                # for org-scoped rows and 1 for globals, so the ORDER BY puts
                # org-scoped first then latest version within each group.
                .annotate(
                    _org_priority=Case(
                        When(organization__isnull=True, then=1),
                        default=0,
                        output_field=IntegerField(),
                    ),
                )
                .order_by("_org_priority", "-version")
                .first()
            )
            if tpl is None:
                return Response({"detail": "No template for this role."}, status=status.HTTP_404_NOT_FOUND)
            return self._template_for_me_payload(tpl, language, prog)

        memberships = Membership.objects.filter(person=viewer, is_active=True).select_related("program")
        if program_slug:
            memberships = memberships.filter(program__slug=program_slug)
        m = memberships.order_by("-created_at").first()
        if m is None:
            return Response({"detail": "No active membership found."}, status=status.HTTP_404_NOT_FOUND)
        prog = m.program
        tpl = (
            ReflectionTemplate.objects.filter(role=m.role, is_active=True)
            .filter(Q(program_type=prog.program_type) | Q(program_type__isnull=True))
            .annotate(
                _org_priority=Case(
                    When(organization__isnull=True, then=1),
                    default=0,
                    output_field=IntegerField(),
                ),
            )
            .order_by("_org_priority", "-version")
            .first()
        )
        if tpl is None:
            return Response({"detail": "No template for this role."}, status=status.HTTP_404_NOT_FOUND)
        return self._template_for_me_payload(tpl, language, prog)

    @action(detail=False, methods=["get"], url_path="my-summary")
    def my_summary(self, request):
        """Personal reflection completion summary: current period, history, streak, total."""
        viewer = _person_for_request(request)
        if viewer is None:
            return Response({"detail": "Person profile required."}, status=status.HTTP_403_FORBIDDEN)
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=status.HTTP_403_FORBIDDEN)

        program_slug = (request.query_params.get("program") or "").strip()
        today = get_today(org)
        prog, tpl = _my_summary_scope(
            viewer,
            org,
            today,
            program_slug or None,
        )
        if prog is None:
            return Response({"detail": "No active membership found."}, status=status.HTTP_404_NOT_FOUND)
        if tpl is None:
            return Response({"detail": "No template for this role."}, status=status.HTTP_404_NOT_FOUND)
        periods = _build_periods(today, tpl.cadence)
        cutoff = periods[-1][0] if periods else today

        reflections_raw = list(
            Reflection.all_objects.filter(
                organization=org,
                subject=viewer,
                template=tpl,
                program=prog,
                period_end__gte=cutoff,
            ).values(
                "id", "period_start", "period_end", "submitted_at",
                "is_complete", "team_visibility",
            ),
        )

        history = []
        for p_start, p_end in periods:
            ref = next(
                (r for r in reflections_raw if p_start <= r["period_end"] <= p_end),
                None,
            )
            history.append({
                "period_start": p_start.isoformat(),
                "period_end": p_end.isoformat(),
                "submitted": bool(ref and ref["is_complete"]),
                "submitted_at": ref["submitted_at"].isoformat() if ref and ref["submitted_at"] else None,
                "reflection_id": ref["id"] if ref else None,
                "team_visibility": ref["team_visibility"] if ref else None,
            })

        streak = 0
        for entry in history:
            if entry["submitted"]:
                streak += 1
            else:
                break

        total_completed = Reflection.all_objects.filter(
            organization=org,
            subject=viewer,
            template=tpl,
            program=prog,
            is_complete=True,
        ).count()

        return Response({
            "template": ReflectionTemplateSummarySerializer(tpl).data,
            "program": prog.slug,
            "current_period": history[0] if history else None,
            "history": history,
            "streak": streak,
            "total_completed": total_completed,
        })

    @action(detail=False, methods=["get"], url_path="my-tasks")
    def my_tasks(self, request):
        """Return the 'what do I owe today?' task list for the current user."""
        viewer = _person_for_request(request)
        if viewer is None:
            return Response({"detail": "Person profile required."}, status=status.HTTP_403_FORBIDDEN)
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=status.HTTP_403_FORBIDDEN)

        today = get_today(org)

        viewer_memberships = list(
            operational_memberships_qs(viewer, today=today).select_related("program"),
        )
        author_agms = list(
            operational_author_groups_qs(viewer, today=today).select_related("group"),
        )

        tasks = _tasks_from_required_assignments(
            viewer=viewer,
            organization=org,
            viewer_memberships=viewer_memberships,
            author_agms=author_agms,
            today=today,
        )

        cadence_order = {"daily": 0, "weekly": 1, "biweekly": 2, "monthly": 3, "on_demand": 4}

        def _sort_key(t: dict) -> tuple:
            comp = t["completion"]
            incomplete = 0 if comp["covered"] < comp["total"] else 1
            cadence = cadence_order.get(t["template"]["cadence"], 5)
            return (incomplete, cadence, t["template"]["name"])

        tasks.sort(key=_sort_key)
        return Response({"tasks": tasks})

    @action(detail=False, methods=["get"], url_path="supervisor-coverage")
    def supervisor_coverage(self, request):
        """Coverage summary for groups the viewer supervises."""
        viewer = _person_for_request(request)
        if viewer is None:
            return Response({"detail": "Person profile required."}, status=status.HTTP_403_FORBIDDEN)
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=status.HTTP_403_FORBIDDEN)

        today = get_today(org)
        is_admin = _has_tenant_admin(viewer) or _privileged_reflection_actor(request)

        if is_admin:
            groups = list(
                operational_assignment_groups_qs(today=today, organization=org),
            )
        else:
            author_group_ids = list(
                operational_author_groups_qs(viewer, today=today).values_list(
                    "group_id", flat=True,
                ),
            )
            if not author_group_ids:
                return Response({"groups": []})
            groups = list(
                AssignmentGroup.objects.filter(id__in=author_group_ids, is_active=True),
            )

        templates = list(
            ReflectionTemplate.objects.filter(
                Q(organization=org) | Q(organization__isnull=True),
                is_active=True,
                subject_mode__in=["single_subject", "multi_subject", "group"],
            ),
        )

        result_groups = []
        for group in groups:
            allowed_templates = [
                tpl for tpl in templates
                if not tpl.assignment_group_types or group.group_type in tpl.assignment_group_types
            ]
            if not allowed_templates:
                continue

            template_coverage = []
            for tpl in allowed_templates:
                period_start, period_end = _current_period(today, tpl.cadence)

                if tpl.subject_mode in ("single_subject", "multi_subject"):
                    total = AssignmentGroupMembership.all_objects.filter(
                        group=group,
                        role_in_group="subject",
                        is_active=True,
                    ).count()
                    covered = (
                        Reflection.all_objects.filter(
                            template=tpl,
                            assignment_group=group,
                            period_start=period_start,
                            period_end=period_end,
                        )
                        .values("subject")
                        .distinct()
                        .count()
                    )
                    template_coverage.append({
                        "template": ReflectionTemplateSummarySerializer(tpl).data,
                        "period": {"start": period_start.isoformat(), "end": period_end.isoformat()},
                        "covered": covered,
                        "total": total,
                        "percent": round(covered / total * 100) if total else 0,
                    })
                elif tpl.subject_mode == "group":
                    done = Reflection.all_objects.filter(
                        template=tpl,
                        subject_group=group,
                        period_start=period_start,
                        period_end=period_end,
                    ).exists()
                    template_coverage.append({
                        "template": ReflectionTemplateSummarySerializer(tpl).data,
                        "period": {"start": period_start.isoformat(), "end": period_end.isoformat()},
                        "covered": 1 if done else 0,
                        "total": 1,
                        "percent": 100 if done else 0,
                    })

            result_groups.append({
                "id": group.id,
                "name": group.name,
                "group_type": group.group_type,
                "template_coverage": template_coverage,
            })

        return Response({"groups": result_groups})
