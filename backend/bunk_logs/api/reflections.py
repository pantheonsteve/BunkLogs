from __future__ import annotations

from functools import reduce
from operator import or_

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Exists
from django.db.models import OuterRef
from django.db.models import Q
from rest_framework import permissions
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import validate_reflection_answers

WELLNESS_ROLES = frozenset({"camper_care", "health_center", "special_diets"})
LEADERSHIP_ROLES = frozenset({"faculty", "leadership_team"})


def _person_for_request(request):
    if not getattr(request, "organization", None) or not request.user.is_authenticated:
        return None
    return Person.objects.filter(user=request.user).first()


def _has_tenant_admin(person: Person) -> bool:
    return Membership.objects.filter(person=person, role="admin", is_active=True).exists()


def _has_wellness_membership(person: Person) -> bool:
    return Membership.objects.filter(
        person=person,
        role__in=WELLNESS_ROLES,
        is_active=True,
    ).exists()


def _privileged_reflection_actor(request) -> bool:
    return bool(getattr(request.user, "is_superuser", False))


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


def leadership_visibility_q(viewer: Person) -> Q | None:
    memberships = list(
        Membership.objects.filter(
            person=viewer,
            role__in=LEADERSHIP_ROLES,
            is_active=True,
        ),
    )
    if not memberships:
        return None
    program_specs: dict[int, dict] = {}
    for m in memberships:
        pid = m.program_id
        raw = m.metadata.get("assigned_unit_slugs")
        if raw is None:
            raw = m.metadata.get("unit_slugs")
        entry = program_specs.setdefault(pid, {"unrestricted": False, "units": set()})
        if not raw:
            entry["unrestricted"] = True
        else:
            entry["units"].update(str(x) for x in raw)

    q_acc = Q(pk__in=[])
    for pid, spec in program_specs.items():
        if spec["unrestricted"]:
            q_acc |= Q(program_id=pid)
            continue
        unit_slugs = spec["units"]
        if not unit_slugs:
            continue
        person_ids = [
            mem.person_id
            for mem in Membership.all_objects.filter(program_id=pid, is_active=True)
            if str(mem.metadata.get("unit_slug") or "") in unit_slugs
        ]
        if person_ids:
            q_acc |= Q(program_id=pid, subject_id__in=person_ids)
    return q_acc


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
        ]


class ReflectionSerializer(serializers.ModelSerializer):
    template_meta = ReflectionTemplateSummarySerializer(source="template", read_only=True)
    program_slug = serializers.SlugField(write_only=True, required=False)
    answers = serializers.JSONField()

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
            "submitted_by",
            "period_start",
            "period_end",
            "answers",
            "language",
            "submitted_at",
            "updated_at",
            "is_complete",
        ]
        read_only_fields = [
            "id",
            "organization",
            "program",
            "subject",
            "subject_group",
            "author",
            "assignment_group",
            "submission_id",
            "submitted_by",
            "submitted_at",
            "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            self.fields["program_slug"].read_only = True
            self.fields["template"].read_only = True

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
        _may_use_template(request, viewer, program, template)

        validated_data["organization"] = org
        validated_data["program"] = program
        validated_data["subject"] = viewer
        validated_data["author"] = viewer
        validated_data["submitted_by"] = request.user
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
        viewer = _person_for_request(self.request)
        if viewer is None:
            return qs.none()
        if _has_tenant_admin(viewer):
            return self._filter_query_params(qs)

        parts: list[Q] = [Q(subject=viewer), Q(author=viewer)]
        lq = leadership_visibility_q(viewer)
        if lq is not None:
            parts.append(lq)
        if _has_wellness_membership(viewer):
            parts.append(Q(template__role__in=WELLNESS_ROLES))

        expr = reduce(or_, parts)
        return self._filter_query_params(qs.filter(expr).distinct())

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

    @action(detail=False, methods=["get"], url_path="template-for-me")
    def template_for_me(self, request):
        viewer = _person_for_request(request)
        if viewer is None:
            return Response({"detail": "Person profile required."}, status=status.HTTP_403_FORBIDDEN)
        program_slug = (request.query_params.get("program") or "").strip()
        language = (request.query_params.get("language") or "en").strip()
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
                .order_by("-version")
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
            .order_by("-version")
            .first()
        )
        if tpl is None:
            return Response({"detail": "No template for this role."}, status=status.HTTP_404_NOT_FOUND)
        return self._template_for_me_payload(tpl, language, prog)
