from __future__ import annotations

from rest_framework import permissions
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.permissions import is_super_admin


def _normalize_tags(values) -> list[str]:
    """Lowercase, strip, dedupe (preserving order). Reused from admin helper conventions."""
    seen: set[str] = set()
    result: list[str] = []
    for v in values or []:
        if v is None:
            continue
        t = str(v).strip().lower()
        if not t or t in seen:
            continue
        seen.add(t)
        result.append(t)
    return result


def _person_for_request(request) -> Person | None:
    if not getattr(request, "organization", None) or not request.user.is_authenticated:
        return None
    return Person.objects.filter(user=request.user).first()


def _is_org_admin(person: Person | None) -> bool:
    if person is None:
        return False
    return Membership.objects.filter(person=person, role="admin", is_active=True).exists()


class MembershipPermission(permissions.BasePermission):
    """Reads + writes restricted to org admins (and Super Admins) inside an org context.

    See ``bunk_logs.core.permissions.is_super_admin`` for the Super Admin
    definition (``is_staff`` OR ``is_superuser``).
    """

    message = "Organization admin membership or Super Admin status required."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and getattr(request, "organization", None)):
            return False
        if is_super_admin(request.user):
            return True
        return _is_org_admin(_person_for_request(request))

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class MembershipSerializer(serializers.ModelSerializer):
    tags = serializers.JSONField(required=False)
    person_name = serializers.CharField(source="person.full_name", read_only=True)
    person_email = serializers.EmailField(source="person.email", read_only=True)
    program_slug = serializers.SlugField(source="program.slug", read_only=True)
    program_name = serializers.CharField(source="program.name", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "program",
            "program_slug",
            "program_name",
            "person",
            "person_name",
            "person_email",
            "role",
            "capability",
            "grade_level",
            "tags",
            "start_date",
            "end_date",
            "is_active",
            "metadata",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "program",
            "program_slug",
            "program_name",
            "person",
            "person_name",
            "person_email",
            "role",
            "capability",
            "created_at",
        ]

    def validate_tags(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            msg = "tags must be a JSON array of strings."
            raise serializers.ValidationError(msg)
        if not all(isinstance(t, str) for t in value):
            msg = "Every tag must be a string."
            raise serializers.ValidationError(msg)
        return _normalize_tags(value)


class MembershipViewSet(viewsets.ModelViewSet):
    serializer_class = MembershipSerializer
    permission_classes = [MembershipPermission]
    http_method_names = ["get", "patch", "post", "head", "options"]

    def create(self, request, *args, **kwargs):
        from rest_framework.exceptions import MethodNotAllowed

        method = "POST"
        raise MethodNotAllowed(method)

    def get_queryset(self):
        qs = Membership.objects.select_related("program", "program__organization", "person")
        params = self.request.query_params

        program_slug = (params.get("program") or "").strip()
        if program_slug:
            qs = qs.filter(program__slug=program_slug)

        role = (params.get("role") or "").strip()
        if role:
            qs = qs.filter(role=role)

        is_active = (params.get("is_active") or "").strip().lower()
        if is_active in ("true", "1", "yes"):
            qs = qs.filter(is_active=True)
        elif is_active in ("false", "0", "no"):
            qs = qs.filter(is_active=False)

        tag_filter = params.getlist("tag") or []
        for t in tag_filter:
            t_norm = t.strip().lower()
            if t_norm:
                qs = qs.filter(tags__contains=[t_norm])

        search = (params.get("search") or "").strip()
        if search:
            qs = qs.filter(person__last_name__icontains=search) | qs.filter(
                person__first_name__icontains=search,
            ) | qs.filter(person__preferred_name__icontains=search)
            qs = qs.distinct()

        return qs.order_by("person__last_name", "person__first_name")

    @action(detail=False, methods=["post"], url_path="bulk-tag")
    def bulk_tag(self, request):
        """Add or remove a set of tags on a list of membership ids.

        POST body: {
          "operation": "add" | "remove" | "set",
          "membership_ids": [1, 2, 3],
          "tags": ["international", "waterfront"]
        }
        Returns: { updated: int }
        """
        op = (request.data.get("operation") or "").strip().lower()
        if op not in {"add", "remove", "set"}:
            return Response(
                {"operation": 'Must be one of "add", "remove", "set".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ids = request.data.get("membership_ids") or []
        if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
            return Response(
                {"membership_ids": "Must be a list of integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not ids:
            return Response({"updated": 0})

        raw_tags = request.data.get("tags") or []
        if not isinstance(raw_tags, list) or not all(isinstance(t, str) for t in raw_tags):
            return Response(
                {"tags": "Must be a list of strings."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        new_tags = _normalize_tags(raw_tags)
        if op != "set" and not new_tags:
            return Response({"tags": "Provide at least one tag."}, status=status.HTTP_400_BAD_REQUEST)

        qs = self.get_queryset().filter(id__in=ids)
        updated = 0
        for membership in qs:
            current = list(membership.tags or [])
            if op == "add":
                merged = _normalize_tags([*current, *new_tags])
            elif op == "remove":
                remove = set(new_tags)
                merged = [t for t in _normalize_tags(current) if t not in remove]
            else:
                merged = new_tags
            if merged != current:
                membership.tags = merged
                membership.save(update_fields=["tags"])
                updated += 1

        return Response({"updated": updated})
