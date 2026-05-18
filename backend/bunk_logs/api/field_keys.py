"""FieldKey registry API — canonical field keys for cross-template reporting."""
from __future__ import annotations

from django.db.models import Q
from rest_framework import permissions
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response

from bunk_logs.core.models import FieldKey
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser
from bunk_logs.core.permissions import _is_org_admin
from bunk_logs.core.permissions import _person_for_request
from bunk_logs.core.permissions import is_super_admin


class FieldKeySerializer(serializers.ModelSerializer):
    is_global = serializers.SerializerMethodField()

    class Meta:
        model = FieldKey
        fields = [
            "id",
            "organization",
            "key",
            "display_name",
            "description",
            "expected_field_type",
            "expected_dashboard_role",
            "is_global",
            "created_at",
        ]
        read_only_fields = ["id", "organization", "is_global", "created_at"]

    def get_is_global(self, obj: FieldKey) -> bool:
        return obj.organization_id is None


class _AuthenticatedWithOrg(permissions.BasePermission):
    message = "Authentication and organization context required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request, "organization", None),
        )


def _key_in_use(key: str, org) -> bool:
    """Return True if any template visible to `org` references this field key in its schema."""
    templates = ReflectionTemplate.all_objects.filter(
        Q(organization=org) | Q(organization__isnull=True),
    )
    for tpl in templates.only("schema"):
        fields = (tpl.schema or {}).get("fields", [])
        if any(isinstance(f, dict) and f.get("key") == key for f in fields):
            return True
    return False


class FieldKeyViewSet(viewsets.ModelViewSet):
    serializer_class = FieldKeySerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [_AuthenticatedWithOrg()]
        return [IsOrgAdminOrSuperuser()]

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        if org is None:
            return FieldKey.all_objects.none()

        if is_super_admin(self.request.user):
            qs = FieldKey.all_objects.select_related("organization")
        else:
            qs = FieldKey.all_objects.select_related("organization").filter(
                Q(organization=org) | Q(organization__isnull=True),
            )

        q = (self.request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(key__istartswith=q)

        return qs

    def get_object(self):
        obj = super().get_object()
        org = getattr(self.request, "organization", None)
        if is_super_admin(self.request.user):
            return obj
        if obj.organization_id is not None and obj.organization_id != (org.pk if org else None):
            from rest_framework.exceptions import NotFound

            raise NotFound
        return obj

    def create(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=status.HTTP_403_FORBIDDEN)

        if not is_super_admin(request.user):
            person = _person_for_request(request)
            if not _is_org_admin(person):
                return Response(
                    {"detail": "Organization admin membership required."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data
        key = validated.get("key", "").strip()

        if FieldKey.all_objects.filter(organization=org, key=key).exists():
            return Response(
                {"key": [f'A key "{key}" already exists for this organization.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance = FieldKey(organization=org, **validated)
        instance.save()
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        org = getattr(request, "organization", None)

        if not is_super_admin(request.user):
            if instance.organization_id is None:
                from rest_framework.exceptions import PermissionDenied

                msg = "Global keys can only be edited by a Super Admin."
                raise PermissionDenied(msg)
            if org is None or instance.organization_id != org.pk:
                from rest_framework.exceptions import NotFound

                raise NotFound

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        org = getattr(request, "organization", None)

        if not is_super_admin(request.user):
            if instance.organization_id is None:
                from rest_framework.exceptions import PermissionDenied

                msg = "Global keys can only be deleted by a Super Admin."
                raise PermissionDenied(msg)
            if org is None or instance.organization_id != org.pk:
                from rest_framework.exceptions import NotFound

                raise NotFound

        if _key_in_use(instance.key, org):
            return Response(
                {
                    "detail": (
                        f'Key "{instance.key}" is referenced by one or more templates. '
                        "Remove it from all templates before deleting."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
