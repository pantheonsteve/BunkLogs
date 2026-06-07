from __future__ import annotations

from django.utils.text import slugify
from rest_framework import permissions
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import RosterImportLog
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser


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

    program_name = serializers.CharField(source="program.name", read_only=True)
    parent_name = serializers.CharField(source="parent.name", read_only=True, allow_null=True)
    parent_id = serializers.PrimaryKeyRelatedField(source="parent", read_only=True, allow_null=True)

    class Meta:
        model = AssignmentGroup
        fields = [
            "id",
            "organization",
            "program",
            "program_name",
            "name",
            "slug",
            "group_type",
            "parent",
            "parent_id",
            "parent_name",
            "is_active",
            "created_at",
            "updated_at",
        ]


class AssignmentGroupWriteSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=AssignmentGroup.all_objects.all(),
        required=False,
        allow_null=True,
    )
    program = serializers.PrimaryKeyRelatedField(
        queryset=Program.all_objects.all(),
    )

    class Meta:
        model = AssignmentGroup
        fields = ["name", "slug", "group_type", "program", "parent", "metadata", "is_active"]

    def validate(self, attrs):
        request = self.context.get("request")
        org = getattr(request, "organization", None)
        program = attrs.get("program")
        if org and program and program.organization_id != org.pk:
            raise serializers.ValidationError({"program": "Program must belong to your organization."})
        parent = attrs.get("parent")
        if parent and org and parent.organization_id != org.pk:
            raise serializers.ValidationError({"parent": "Parent group must belong to your organization."})
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        org = request.organization
        if not validated_data.get("slug"):
            validated_data["slug"] = slugify(validated_data.get("name", ""))[:100]
        return AssignmentGroup.all_objects.create(organization=org, **validated_data)

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class MembershipAddSerializer(serializers.Serializer):
    person_id = serializers.IntegerField()
    role_in_group = serializers.ChoiceField(choices=AssignmentGroupMembership.ROLES_IN_GROUP)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate_person_id(self, value):
        request = self.context.get("request")
        org = getattr(request, "organization", None)
        qs = Person.all_objects.filter(pk=value)
        if org:
            qs = qs.filter(organization=org)
        if not qs.exists():
            msg = "Person not found in this organization."
            raise serializers.ValidationError(msg)
        return value


class RosterImportLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RosterImportLog
        fields = [
            "id",
            "importer_type",
            "status",
            "csv_filename",
            "summary",
            "started_at",
            "completed_at",
        ]


class AssignmentGroupPermission(permissions.BasePermission):
    message = "Organization context required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request, "organization", None),
        )


class AssignmentGroupViewSet(viewsets.ModelViewSet):
    permission_classes = [AssignmentGroupPermission]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "add_membership", "remove_membership", "import_roster"):
            return [AssignmentGroupPermission(), IsOrgAdminOrSuperuser()]
        return [AssignmentGroupPermission()]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AssignmentGroupSerializer
        if self.action in ("create", "update", "partial_update"):
            return AssignmentGroupWriteSerializer
        return AssignmentGroupListSerializer

    def get_queryset(self):
        qs = AssignmentGroup.objects.select_related("organization", "program", "parent")
        params = self.request.query_params

        program_param = (params.get("program") or "").strip()
        if program_param:
            if program_param.isdigit():
                qs = qs.filter(program_id=int(program_param))
            else:
                qs = qs.filter(program__slug=program_param)

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

    def destroy(self, request, *args, **kwargs):
        group = self.get_object()
        has_reflections = Reflection.all_objects.filter(
            assignment_group=group,
        ).exists() or Reflection.all_objects.filter(
            subject_group=group,
        ).exists()
        if has_reflections:
            return Response(
                {"detail": "Cannot delete a group that has reflections referencing it."},
                status=status.HTTP_409_CONFLICT,
            )
        group.is_active = False
        group.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

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

    @action(detail=True, methods=["post"], url_path="memberships")
    def add_membership(self, request, pk=None):
        group = self.get_object()
        serializer = MembershipAddSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        person = Person.all_objects.get(pk=data["person_id"])
        membership, created = AssignmentGroupMembership.all_objects.get_or_create(
            group=group,
            person=person,
            role_in_group=data["role_in_group"],
            defaults={
                "is_active": True,
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date"),
                "metadata": data.get("metadata", {}),
            },
        )
        if not created and not membership.is_active:
            membership.is_active = True
            membership.save(update_fields=["is_active"])

        out = AssignmentGroupMembershipSerializer(membership)
        return Response(out.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["delete"], url_path=r"memberships/(?P<membership_id>\d+)")
    def remove_membership(self, request, pk=None, membership_id=None):
        group = self.get_object()
        try:
            membership = AssignmentGroupMembership.all_objects.get(pk=membership_id, group=group)
        except AssignmentGroupMembership.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        hard_delete = request.query_params.get("hard", "").lower() in ("1", "true", "yes")
        if hard_delete:
            membership.delete()
        else:
            membership.is_active = False
            membership.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post"],
        url_path="import-roster",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_roster(self, request, pk=None):
        group = self.get_object()
        csv_file = request.FILES.get("file")
        if not csv_file:
            return Response({"detail": "A CSV file is required."}, status=status.HTTP_400_BAD_REQUEST)

        importer_type = request.data.get("importer_type", "campminder")
        if importer_type not in ("campminder", "tbe_shulcloud"):
            return Response(
                {"detail": f"Unknown importer_type: {importer_type!r}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reconcile = request.data.get("reconcile", "false").lower() in ("1", "true", "yes")
        csv_content = csv_file.read().decode("utf-8")

        log = RosterImportLog.all_objects.create(
            organization=group.organization,
            program=group.program,
            importer_type=importer_type,
            initiated_by=request.user if request.user.is_authenticated else None,
            status="pending",
            csv_filename=csv_file.name,
        )

        from bunk_logs.core.tasks import import_roster_task
        import_roster_task.delay(
            log_id=log.pk,
            csv_content=csv_content,
            importer_type=importer_type,
            options={"reconcile": reconcile},
        )

        return Response(
            {"task_id": log.pk, "log_id": log.pk, "status": log.status},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=["get"], url_path=r"import-logs/(?P<log_id>\d+)")
    def import_log_status(self, request, log_id=None):
        try:
            log = RosterImportLog.objects.get(pk=log_id)
        except RosterImportLog.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(RosterImportLogSerializer(log).data)
