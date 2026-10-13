"""Read-only preview of who a form assignment will reach."""

from __future__ import annotations

from rest_framework.exceptions import NotFound
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.form_audience import preview_form_audience
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import ReflectionTemplate

from .common import admin_only_or_403
from .templates import _lt_template_queryset


class LeadershipTeamAudiencePreviewView(APIView):
    """``GET /templates/<id>/audience-preview/`` — writers, subjects, supervisors."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int, *args, **kwargs):
        ctx = admin_only_or_403(request)
        try:
            template = _lt_template_queryset(ctx.organization).get(pk=pk)
        except ReflectionTemplate.DoesNotExist as exc:
            raise NotFound from exc

        target_type = (request.query_params.get("target_type") or "").strip()
        if target_type not in {"role", "assignment_group"}:
            msg = "Choose a role or one or more groups."
            raise ValidationError(msg)

        groups = []
        if target_type == "assignment_group":
            raw = request.query_params.get("groups") or ""
            ids = []
            for part in raw.split(","):
                part = part.strip()
                if part.isdigit():
                    ids.append(int(part))
            if not ids:
                msg = "Choose a group."
                raise ValidationError(msg)
            found = {group.id: group for group in AssignmentGroup.objects.filter(pk__in=ids)}
            if len(found) != len(set(ids)):
                msg = "That group is not in this organization."
                raise NotFound(msg)
            groups = [found[group_id] for group_id in ids]

        return Response(
            preview_form_audience(
                ctx.organization,
                template,
                target_type=target_type,
                role=(request.query_params.get("role") or "").strip(),
                groups=groups,
            ),
        )
