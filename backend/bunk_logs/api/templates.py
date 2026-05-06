"""Template CRUD API — create, read, update, delete, and clone ReflectionTemplates."""
from __future__ import annotations

import copy

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser
from bunk_logs.core.permissions import _is_org_admin
from bunk_logs.core.permissions import _person_for_request


class ReflectionTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReflectionTemplate
        fields = [
            "id",
            "organization",
            "program_type",
            "role",
            "name",
            "slug",
            "description",
            "cadence",
            "schema",
            "languages",
            "is_active",
            "version",
            "parent_template",
            "created_at",
        ]
        read_only_fields = ["id", "organization", "version", "parent_template", "created_at"]

    def validate(self, attrs):
        schema = attrs.get("schema", getattr(self.instance, "schema", None))
        languages = attrs.get("languages", getattr(self.instance, "languages", None) or [])
        if schema is not None:
            from bunk_logs.core.validators.template_schema import validate_template_schema

            try:
                validate_template_schema(schema, languages)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(
                    exc.message_dict if hasattr(exc, "message_dict") else str(exc),
                )
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        org = request.organization
        validated_data["organization"] = org
        validated_data.setdefault("version", 1)
        try:
            instance = ReflectionTemplate(**validated_data)
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else str(exc),
            )
        instance.save()
        return instance


class _AuthenticatedWithOrg(permissions.BasePermission):
    """Baseline: authenticated + org context present (for list/retrieve)."""

    message = "Authentication and organization context required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request, "organization", None),
        )


class ReflectionTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = ReflectionTemplateSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [_AuthenticatedWithOrg()]
        return [IsOrgAdminOrSuperuser()]

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        if org is None:
            return ReflectionTemplate.all_objects.none()

        qs = ReflectionTemplate.all_objects.select_related("organization", "parent_template")

        # Super admins see everything; regular users see own org + global
        if not self.request.user.is_superuser:
            from django.db.models import Q

            qs = qs.filter(Q(organization=org) | Q(organization__isnull=True))

        params = self.request.query_params

        role = (params.get("role") or "").strip()
        if role:
            qs = qs.filter(role=role)

        program_type = (params.get("program_type") or "").strip()
        if program_type:
            qs = qs.filter(program_type=program_type)

        is_active_str = (params.get("is_active") or "").strip().lower()
        if is_active_str in ("true", "1"):
            qs = qs.filter(is_active=True)
        elif is_active_str in ("false", "0"):
            qs = qs.filter(is_active=False)

        include_global_str = (params.get("include_global") or "true").strip().lower()
        if include_global_str in ("false", "0") and not self.request.user.is_superuser:
            qs = qs.filter(organization=org)

        return qs

    def get_object(self):
        """Return 404 (not 403) when accessing objects outside the current org."""
        obj = super().get_object()
        org = getattr(self.request, "organization", None)
        if self.request.user.is_superuser:
            return obj
        if obj.organization_id is not None and obj.organization_id != (org.pk if org else None):
            from rest_framework.exceptions import NotFound

            raise NotFound
        return obj

    def _check_edit_permission(self, instance: ReflectionTemplate) -> None:
        """Raise 404 for cross-org edits; 403 for global-template edits by non-superusers."""
        org = getattr(self.request, "organization", None)
        if self.request.user.is_superuser:
            return
        if instance.organization_id is None:
            from rest_framework.exceptions import PermissionDenied

            msg = "Global templates cannot be edited directly. Clone the template to your org first."
            raise PermissionDenied(msg)
        if org is None or instance.organization_id != org.pk:
            from rest_framework.exceptions import NotFound

            raise NotFound

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        self._check_edit_permission(instance)

        force_new = request.query_params.get("force_new_version", "").lower() == "true"
        has_responses = Reflection.all_objects.filter(template=instance).exists()

        if has_responses or force_new:
            return self._create_version(instance, request)
        return self._edit_in_place(instance, request)

    def _edit_in_place(self, instance: ReflectionTemplate, request) -> Response:
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        data = dict(serializer.data)
        data["created_new_version"] = False
        return Response(data)

    def _create_version(self, old: ReflectionTemplate, request) -> Response:
        """Duplicate the template at version+1, apply the patch, deactivate old if requested."""
        patch = request.data
        new_schema = patch.get("schema", old.schema)
        new_languages = patch.get("languages", old.languages)

        from bunk_logs.core.validators.template_schema import validate_template_schema

        try:
            validate_template_schema(new_schema, new_languages)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else str(exc),
            )

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
            is_active=patch.get("is_active", True),
            version=new_version,
            parent_template=old,
        )
        try:
            new_tpl.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else str(exc),
            )
        new_tpl.save()

        if patch.get("deactivate_previous", False):
            old.is_active = False
            old.save(update_fields=["is_active"])

        serializer = self.get_serializer(new_tpl)
        data = dict(serializer.data)
        data["created_new_version"] = True
        return Response(data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self._check_edit_permission(instance)
        if Reflection.all_objects.filter(template=instance).exists():
            return Response(
                {"detail": "Cannot delete a template that has reflections. Deactivate it instead."},
                status=status.HTTP_409_CONFLICT,
            )
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="clone")
    def clone(self, request, pk=None):
        """Clone a global or org template into the current org as a new draft."""
        source = self.get_object()
        org = getattr(request, "organization", None)
        if org is None:
            return Response(
                {"detail": "Organization context required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Only admins / superusers can clone (handled by get_permissions for non-list actions)
        person = _person_for_request(request)
        if not request.user.is_superuser and not _is_org_admin(person):
            return Response(
                {"detail": "Organization admin membership required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        new_version = (
            ReflectionTemplate.all_objects.filter(
                organization=org, slug=source.slug,
            )
            .order_by("-version")
            .values_list("version", flat=True)
            .first()
        )
        new_version = (new_version or 0) + 1

        clone = ReflectionTemplate(
            organization=org,
            program_type=source.program_type,
            role=source.role,
            name=source.name,
            slug=source.slug,
            description=source.description,
            cadence=source.cadence,
            schema=copy.deepcopy(source.schema),
            languages=list(source.languages),
            is_active=False,
            version=new_version,
            parent_template=source,
        )
        try:
            clone.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else str(exc),
            )
        clone.save()

        serializer = self.get_serializer(clone)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
