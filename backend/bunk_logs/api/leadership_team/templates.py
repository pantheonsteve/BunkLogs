"""LT-scoped template builder API (Step 7_12 PR B — Story 51).

Endpoints under ``/api/v1/leadership-team/templates/``:

* ``GET    /``              — list templates visible to the viewer.
* ``POST   /``              — create a new template at ``status='draft'``.
* ``GET    /<id>/``         — retrieve a single template.
* ``PATCH  /<id>/``         — edit-in-place if no responses (or
                              ``?force_new_version=true`` to bump version
                              regardless); creates a new version when
                              responses exist.
* ``DELETE /<id>/``         — permanently delete a template with no
                              responses (any status). Templates that
                              already have submissions must be archived
                              instead so answers are preserved.
* ``POST   /<id>/publish/``   — ``draft -> published`` after validation.
* ``POST   /<id>/unpublish/`` — ``published -> draft`` (no responses allowed).
* ``POST   /<id>/clone/``   — clone any visible template as a new draft;
                              no version chain back to the source.
* ``POST   /<id>/archive/`` — ``published -> archived`` (preserves
                              historical reflections).

Permission: ``leadership_team`` role + ``program_lead`` capability
(reuses ``viewer_or_403``). Templates are visible if:

* the viewer's organization owns them, OR
* a co-supervisor of the viewer is the author (we approximate this as
  any LT in the same program — fine for Tier 1).

Lifecycle parity: every write updates ``is_active`` in lockstep with
``status`` so the existing admin template CRUD and old code that filters
on ``is_active`` keep working through a rollback.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.templates import ReflectionTemplateSerializer
from bunk_logs.core import audit
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment
from bunk_logs.core.validators.template_schema import check_field_key_hints
from bunk_logs.core.validators.template_schema import validate_template_schema

from .common import viewer_or_403

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization


# ---------------------------------------------------------------------------
# Visibility
# ---------------------------------------------------------------------------


def _lt_template_queryset(org: Organization, *, include_global: bool = True):
    """Templates this LT can list: own-org + (optionally) global.

    Co-supervisors share an org and a program, so a single ``filter`` by
    organization covers the visibility model for Tier 1. Status filter
    is applied later to allow ``?status=draft`` etc.
    """
    base = ReflectionTemplate.all_objects.select_related(
        "organization", "parent_template",
    )
    if include_global:
        return base.filter(Q(organization=org) | Q(organization__isnull=True))
    return base.filter(organization=org)


def _serialize(
    template: ReflectionTemplate,
    request,
    *,
    active_assignment_count: int | None = None,
    reflection_count: int | None = None,
) -> dict[str, Any]:
    """Wrap the shared serializer + attach status + field-key warnings.

    ``active_assignment_count`` is the number of TemplateAssignments in
    the viewer's org currently scheduled/active for this template. Set
    by the list endpoint via a single GROUP BY query so the library can
    show "N active assignments" without an N+1 fetch.
    """
    data = dict(ReflectionTemplateSerializer(template, context={"request": request}).data)
    data["status"] = template.status
    org = getattr(request, "organization", None)
    data["field_key_warnings"] = check_field_key_hints(template.schema or {}, org)
    if active_assignment_count is not None:
        data["active_assignment_count"] = active_assignment_count
    if reflection_count is not None:
        data["reflection_count"] = reflection_count
    return data


def _audit_template(*, request, template: ReflectionTemplate, action: str, **extra) -> None:
    """Thin audit-trail wrapper.

    Lifecycle template events are recorded as ``state_changed`` rows
    (``before_state="<old>" -> after_state="<new>"``) for publish/archive
    and as ``created`` rows for new drafts/versions/clones.
    """
    user = getattr(request, "user", None)
    metadata = {
        "lt_action": action,
        "status": template.status,
        "version": template.version,
        "slug": template.slug,
        **extra,
    }
    if action in ("publish", "archive"):
        audit.state_changed(
            actor=user,
            content=template,
            before_state=extra.get("from_status", "draft"),
            after_state=template.status,
            content_type="reflection_template",
            metadata=metadata,
        )
    else:
        audit.created(
            actor=user,
            content=template,
            content_type="reflection_template",
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# List + create
# ---------------------------------------------------------------------------


class LeadershipTeamTemplateListCreateView(APIView):
    """``GET`` to list templates, ``POST`` to create a new draft."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        qs = _lt_template_queryset(ctx.organization).order_by("-created_at")

        status_q = (request.query_params.get("status") or "").strip().lower()
        if status_q in {"draft", "published", "archived"}:
            qs = qs.filter(status=status_q)

        role_q = (request.query_params.get("role") or "").strip()
        if role_q:
            qs = qs.filter(role=role_q)

        templates = list(qs[:200])
        template_ids = [t.pk for t in templates]
        assignment_counts: dict[int, int] = {}
        reflection_counts: dict[int, int] = {}
        if template_ids:
            assignment_counts_qs = (
                TemplateAssignment.all_objects.filter(
                    organization=ctx.organization,
                    template_id__in=template_ids,
                    status__in=(
                        TemplateAssignment.Status.SCHEDULED,
                        TemplateAssignment.Status.ACTIVE,
                    ),
                )
                .values("template_id")
                .annotate(n=models.Count("id"))
            )
            assignment_counts = {row["template_id"]: row["n"] for row in assignment_counts_qs}
            reflection_counts_qs = (
                Reflection.all_objects.filter(template_id__in=template_ids)
                .values("template_id")
                .annotate(n=models.Count("id"))
            )
            reflection_counts = {row["template_id"]: row["n"] for row in reflection_counts_qs}
        return Response(
            {
                "templates": [
                    _serialize(
                        t,
                        request,
                        active_assignment_count=assignment_counts.get(t.pk, 0),
                        reflection_count=reflection_counts.get(t.pk, 0),
                    )
                    for t in templates
                ],
            },
        )

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        payload = dict(request.data) if isinstance(request.data, dict) else {}

        slug = (payload.get("slug") or "").strip()
        name = (payload.get("name") or "").strip()
        if not slug or not name:
            msg = "name and slug are required."
            raise ValidationError(msg)

        existing_version = (
            ReflectionTemplate.all_objects
            .filter(organization=ctx.organization, slug=slug)
            .order_by("-version")
            .values_list("version", flat=True)
            .first()
        )
        next_version = (existing_version or 0) + 1

        tpl = ReflectionTemplate(
            organization=ctx.organization,
            program_type=payload.get("program_type"),
            role=payload.get("role"),
            name=name,
            slug=slug,
            description=payload.get("description", ""),
            cadence=payload.get("cadence", "daily"),
            schema=payload.get("schema") or {"fields": []},
            languages=payload.get("languages") or ["en"],
            version=next_version,
            status=ReflectionTemplate.Status.DRAFT,
            is_active=False,
            subject_mode=payload.get("subject_mode", "self"),
            assignment_scope=payload.get("assignment_scope", "none"),
            assignment_group_types=payload.get("assignment_group_types") or [],
            author_role_filter=payload.get("author_role_filter") or [],
            subject_role_filter=payload.get("subject_role_filter") or [],
            subject_visible=bool(payload.get("subject_visible", False)),
            supports_privacy=bool(payload.get("supports_privacy", False)),
            required_per_subject_per_period=int(
                payload.get("required_per_subject_per_period", 1),
            ),
        )
        try:
            tpl.full_clean()
        except DjangoValidationError as exc:
            raise ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else str(exc),
            ) from exc
        tpl.save()
        _audit_template(request=request, template=tpl, action="create_draft")
        return Response(_serialize(tpl, request), status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Detail + update
# ---------------------------------------------------------------------------


class LeadershipTeamTemplateDetailView(APIView):
    """``GET`` / ``PATCH`` for a single LT-visible template."""

    permission_classes = [IsAuthenticated]

    def _get_template(self, request, pk: int) -> ReflectionTemplate:
        ctx = viewer_or_403(request)
        try:
            tpl = _lt_template_queryset(ctx.organization).get(pk=pk)
        except ReflectionTemplate.DoesNotExist as exc:
            raise NotFound from exc
        return tpl

    def _check_writable(self, ctx, template: ReflectionTemplate) -> None:
        if template.organization_id is None:
            msg = "Global templates cannot be edited. Clone into your org first."
            raise PermissionDenied(msg)
        if template.organization_id != ctx.organization.pk:
            raise NotFound

    def get(self, request, pk: int, *args, **kwargs):
        tpl = self._get_template(request, pk)
        reflection_count = Reflection.all_objects.filter(template=tpl).count()
        return Response(_serialize(tpl, request, reflection_count=reflection_count))

    def delete(self, request, pk: int, *args, **kwargs):
        """``DELETE /<id>/`` — permanently remove a template with no responses.

        Any status (draft, published, or archived) may be deleted when no
        Reflection rows exist. Once staff have submitted answers, archive
        the template instead so historical data is preserved.
        """
        ctx = viewer_or_403(request)
        tpl = self._get_template(request, pk)
        self._check_writable(ctx, tpl)
        if Reflection.all_objects.filter(template=tpl).exists():
            msg = (
                "Cannot delete a template that already has responses. "
                "Archive it instead to retire the form while keeping answers."
            )
            raise ValidationError(msg)
        _audit_template(request=request, template=tpl, action="delete")
        tpl.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, pk: int, *args, **kwargs):
        ctx = viewer_or_403(request)
        tpl = self._get_template(request, pk)
        self._check_writable(ctx, tpl)

        force_new = (request.query_params.get("force_new_version") or "").lower() == "true"
        has_responses = Reflection.all_objects.filter(template=tpl).exists()

        if has_responses or force_new:
            return self._create_version(request, tpl)
        return self._edit_in_place(request, tpl)

    @staticmethod
    def _edit_in_place(request, tpl: ReflectionTemplate) -> Response:
        serializer = ReflectionTemplateSerializer(
            tpl, data=request.data, partial=True, context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        data = _serialize(instance, request)
        data["created_new_version"] = False
        _audit_template(request=request, template=instance, action="edit_in_place")
        return Response(data)

    @staticmethod
    def _create_version(request, old: ReflectionTemplate) -> Response:
        """Bump version + 1, optionally archive old (Story 51 c6)."""
        patch = request.data
        new_schema = patch.get("schema", old.schema)
        new_languages = patch.get("languages", old.languages)
        try:
            validate_template_schema(new_schema, new_languages or [])
        except DjangoValidationError as exc:
            raise ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else str(exc),
            ) from exc

        new_version = (
            ReflectionTemplate.all_objects.filter(
                organization=old.organization, slug=old.slug,
            )
            .order_by("-version")
            .values_list("version", flat=True)
            .first()
            or old.version
        ) + 1

        new_tpl = ReflectionTemplate(
            organization=old.organization,
            program_type=patch.get("program_type", old.program_type),
            role=patch.get("role", old.role),
            name=patch.get("name", old.name),
            slug=old.slug,
            description=patch.get("description", old.description),
            cadence=patch.get("cadence", old.cadence),
            schema=new_schema,
            languages=new_languages,
            status=ReflectionTemplate.Status.DRAFT,
            is_active=False,
            version=new_version,
            parent_template=old,
            subject_mode=patch.get("subject_mode", old.subject_mode),
            assignment_scope=patch.get("assignment_scope", old.assignment_scope),
            assignment_group_types=list(
                patch.get("assignment_group_types", old.assignment_group_types or []),
            ),
            author_role_filter=list(
                patch.get("author_role_filter", old.author_role_filter or []),
            ),
            subject_role_filter=list(
                patch.get("subject_role_filter", old.subject_role_filter or []),
            ),
            subject_visible=patch.get("subject_visible", old.subject_visible),
            supports_privacy=patch.get("supports_privacy", old.supports_privacy),
            required_per_subject_per_period=patch.get(
                "required_per_subject_per_period",
                old.required_per_subject_per_period,
            ),
        )
        try:
            new_tpl.full_clean()
        except DjangoValidationError as exc:
            raise ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else str(exc),
            ) from exc
        new_tpl.save()
        data = _serialize(new_tpl, request)
        data["created_new_version"] = True
        _audit_template(request=request, template=new_tpl, action="create_version")
        return Response(data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Lifecycle actions: publish / clone / archive
# ---------------------------------------------------------------------------


class _BaseLifecycleView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, request, pk: int) -> tuple[Any, ReflectionTemplate]:
        ctx = viewer_or_403(request)
        try:
            tpl = _lt_template_queryset(ctx.organization).get(pk=pk)
        except ReflectionTemplate.DoesNotExist as exc:
            raise NotFound from exc
        return ctx, tpl


class LeadershipTeamTemplatePublishView(_BaseLifecycleView):
    """``POST /<id>/publish/`` — ``draft -> published`` with validation."""

    def post(self, request, pk: int, *args, **kwargs):
        ctx, tpl = self._get(request, pk)
        if tpl.organization_id != ctx.organization.pk:
            msg = "Cannot publish a template that doesn't belong to your org."
            raise PermissionDenied(msg)
        if tpl.status == ReflectionTemplate.Status.ARCHIVED:
            msg = "Archived templates cannot be re-published."
            raise ValidationError(msg)

        warnings: list[dict[str, Any]] = []
        schema = tpl.schema or {}
        languages = tpl.languages or ["en"]
        try:
            validate_template_schema(schema, languages)
        except DjangoValidationError as exc:
            warnings.append({
                "code": "schema",
                "detail": exc.message_dict if hasattr(exc, "message_dict") else str(exc),
            })

        seen_keys: set[str] = set()
        for f in (schema.get("fields") or []):
            if not isinstance(f, dict):
                continue
            k = f.get("key")
            if isinstance(k, str):
                if k in seen_keys:
                    warnings.append({"code": "duplicate_key", "key": k})
                seen_keys.add(k)
                prompts = f.get("prompts") or {}
                for lang in languages:
                    if not (prompts.get(lang) or "").strip():
                        warnings.append({
                            "code": "missing_prompt",
                            "key": k,
                            "language": lang,
                        })

        if any(w["code"] in {"schema", "duplicate_key"} for w in warnings):
            return Response(
                {"status": tpl.status, "warnings": warnings},
                status=status.HTTP_409_CONFLICT,
            )

        prior_status = tpl.status
        with transaction.atomic():
            tpl.status = ReflectionTemplate.Status.PUBLISHED
            tpl.is_active = True
            tpl.save(update_fields=["status", "is_active"])
        _audit_template(
            request=request, template=tpl, action="publish",
            from_status=prior_status,
        )

        body = _serialize(tpl, request)
        body["warnings"] = warnings
        return Response(body)


class LeadershipTeamTemplateUnpublishView(_BaseLifecycleView):
    """``POST /<id>/unpublish/`` — ``published -> draft`` (reverts publication).

    Allowed only when there are no existing Reflection responses for the
    template.  This keeps the semantics clean: once people have submitted
    answers to a template it should be archived rather than silently
    reverted, because active assignments may still reference it.
    """

    def post(self, request, pk: int, *args, **kwargs):
        ctx, tpl = self._get(request, pk)
        if tpl.organization_id != ctx.organization.pk:
            msg = "Cannot unpublish a template that doesn't belong to your org."
            raise PermissionDenied(msg)
        if tpl.status != ReflectionTemplate.Status.PUBLISHED:
            msg = "Only published templates can be unpublished."
            raise ValidationError(msg)
        if Reflection.all_objects.filter(template=tpl).exists():
            msg = (
                "Cannot unpublish a template that already has responses. "
                "Archive it instead."
            )
            raise ValidationError(msg)
        with transaction.atomic():
            tpl.status = ReflectionTemplate.Status.DRAFT
            tpl.is_active = False
            tpl.save(update_fields=["status", "is_active"])
        _audit_template(request=request, template=tpl, action="unpublish")
        return Response(_serialize(tpl, request))


class LeadershipTeamTemplateArchiveView(_BaseLifecycleView):
    """``POST /<id>/archive/`` — ``published -> archived`` (preserves data)."""

    def post(self, request, pk: int, *args, **kwargs):
        ctx, tpl = self._get(request, pk)
        if tpl.organization_id != ctx.organization.pk:
            msg = "Cannot archive a template that doesn't belong to your org."
            raise PermissionDenied(msg)
        if tpl.status == ReflectionTemplate.Status.DRAFT:
            msg = "Draft templates have no archived state; delete them instead."
            raise ValidationError(msg)
        prior_status = tpl.status
        with transaction.atomic():
            tpl.status = ReflectionTemplate.Status.ARCHIVED
            tpl.is_active = False
            tpl.save(update_fields=["status", "is_active"])
        _audit_template(
            request=request, template=tpl, action="archive",
            from_status=prior_status,
        )
        return Response(_serialize(tpl, request))


class LeadershipTeamTemplateCloneView(_BaseLifecycleView):
    """``POST /<id>/clone/`` — clone (global or own-org) as a new draft."""

    def post(self, request, pk: int, *args, **kwargs):
        ctx, source = self._get(request, pk)

        next_version = (
            ReflectionTemplate.all_objects
            .filter(organization=ctx.organization, slug=source.slug)
            .order_by("-version")
            .values_list("version", flat=True)
            .first()
            or 0
        ) + 1

        clone = ReflectionTemplate(
            organization=ctx.organization,
            program_type=source.program_type,
            role=source.role,
            name=source.name,
            slug=source.slug,
            description=source.description,
            cadence=source.cadence,
            schema=copy.deepcopy(source.schema or {}),
            languages=list(source.languages or []),
            status=ReflectionTemplate.Status.DRAFT,
            is_active=False,
            version=next_version,
            parent_template=None,
            subject_mode=source.subject_mode,
            assignment_scope=source.assignment_scope,
            assignment_group_types=list(source.assignment_group_types or []),
            author_role_filter=list(source.author_role_filter or []),
            subject_role_filter=list(source.subject_role_filter or []),
            subject_visible=source.subject_visible,
            supports_privacy=source.supports_privacy,
            required_per_subject_per_period=source.required_per_subject_per_period,
        )
        try:
            clone.full_clean()
        except DjangoValidationError as exc:
            raise ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else str(exc),
            ) from exc
        clone.save()
        _audit_template(
            request=request, template=clone, action="clone", source_id=source.pk,
        )
        return Response(_serialize(clone, request), status=status.HTTP_201_CREATED)
