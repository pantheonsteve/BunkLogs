from __future__ import annotations

from rest_framework import permissions
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Person


class PersonSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ["id", "first_name", "last_name", "preferred_name"]


class AssignmentGroupMembershipSerializer(serializers.ModelSerializer):
    person = PersonSummarySerializer(read_only=True)

    class Meta:
        model = AssignmentGroupMembership
        fields = ["id", "person", "role_in_group", "is_active", "start_date", "end_date", "metadata"]


class AssignmentGroupSerializer(serializers.ModelSerializer):
    memberships = AssignmentGroupMembershipSerializer(many=True, read_only=True)
    parent_id = serializers.PrimaryKeyRelatedField(source="parent", read_only=True)

    class Meta:
        model = AssignmentGroup
        fields = [
            "id",
            "organization",
            "program",
            "name",
            "slug",
            "group_type",
            "parent_id",
            "metadata",
            "is_active",
            "created_at",
            "updated_at",
            "memberships",
        ]
        read_only_fields = fields


class AssignmentGroupListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views (no memberships)."""

    class Meta:
        model = AssignmentGroup
        fields = [
            "id",
            "organization",
            "program",
            "name",
            "slug",
            "group_type",
            "parent",
            "is_active",
            "created_at",
            "updated_at",
        ]


class AssignmentGroupPermission(permissions.BasePermission):
    message = "Organization context required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request, "organization", None),
        )


class AssignmentGroupViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AssignmentGroupPermission]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AssignmentGroupSerializer
        return AssignmentGroupListSerializer

    def get_queryset(self):
        qs = AssignmentGroup.objects.select_related("organization", "program", "parent")
        params = self.request.query_params

        program_slug = (params.get("program") or "").strip()
        if program_slug:
            qs = qs.filter(program__slug=program_slug)

        group_type = (params.get("group_type") or "").strip()
        if group_type:
            qs = qs.filter(group_type=group_type)

        is_active = params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=(is_active.lower() not in ("0", "false", "no")))

        include_descendants = (params.get("include_descendants") or "").lower() == "true"
        parent_id_raw = (params.get("parent") or "").strip()

        if include_descendants and parent_id_raw.isdigit():
            root = AssignmentGroup.all_objects.filter(pk=int(parent_id_raw)).first()
            if root:
                descendant_ids = {root.pk} | {d.pk for d in root.get_descendants()}
                qs = qs.filter(pk__in=descendant_ids)
            else:
                qs = qs.none()
        elif parent_id_raw == "null":
            qs = qs.filter(parent__isnull=True)
        elif parent_id_raw.isdigit():
            qs = qs.filter(parent_id=int(parent_id_raw))

        return qs

    @action(detail=True, methods=["get"], url_path="subjects")
    def subjects(self, request, pk=None):
        group = self.get_object()
        person_ids = (
            AssignmentGroupMembership.all_objects.filter(
                group=group,
                role_in_group="subject",
                is_active=True,
            ).values_list("person_id", flat=True)
        )
        persons = Person.all_objects.filter(pk__in=person_ids).order_by("last_name", "first_name")
        return Response(PersonSummarySerializer(persons, many=True).data)

    @action(detail=True, methods=["get"], url_path="authors")
    def authors(self, request, pk=None):
        group = self.get_object()
        person_ids = (
            AssignmentGroupMembership.all_objects.filter(
                group=group,
                role_in_group="author",
                is_active=True,
            ).values_list("person_id", flat=True)
        )
        persons = Person.all_objects.filter(pk__in=person_ids).order_by("last_name", "first_name")
        return Response(PersonSummarySerializer(persons, many=True).data)
