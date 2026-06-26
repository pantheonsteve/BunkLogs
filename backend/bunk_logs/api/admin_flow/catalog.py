"""Admin catalog management (configurable Store / RequestType / CatalogItem).

Endpoints under ``/api/v1/admin/catalog/``:

* ``GET  /catalog/tree/``               full nested tree for the editor UI
* ``GET  /catalog/stores/``             list      ``POST`` create
* ``GET/PATCH/DELETE /catalog/stores/<id>/``
* ``GET  /catalog/request-types/``      list      ``POST`` create  (``?store=``)
* ``GET/PATCH/DELETE /catalog/request-types/<id>/``
* ``GET  /catalog/items/``              list      ``POST`` create  (``?request_type=``)
* ``GET/PATCH/DELETE /catalog/items/<id>/``
* ``GET  /catalog/template.csv``        downloadable import template
* ``POST /catalog/import/``             CSV upload (``?mode=preview|commit``)

All reads/writes are scoped to the request org via ``all_objects`` + explicit
``organization=ctx.organization`` filters so a stolen JWT for another org can't
reach this tenant's catalog.
"""

from __future__ import annotations

from django.db import transaction
from django.http import HttpResponse
from django.utils.text import slugify
from rest_framework import status
from rest_framework.parsers import FormParser
from rest_framework.parsers import JSONParser
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.catalog_csv import apply_catalog_import
from bunk_logs.core.catalog_csv import build_catalog_template_csv
from bunk_logs.core.catalog_csv import parse_catalog_csv
from bunk_logs.core.models import CatalogItem
from bunk_logs.core.models import Program
from bunk_logs.core.models import RequestType
from bunk_logs.core.models import Store
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser

from .common import viewer_or_403

# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def _serialize_store(s: Store) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "slug": s.slug,
        "labels": s.labels or {},
        "fulfilling_role": s.fulfilling_role,
        "program_id": s.program_id,
        "is_active": s.is_active,
        "sort_order": s.sort_order,
    }


def _serialize_request_type(rt: RequestType) -> dict:
    return {
        "id": rt.id,
        "store_id": rt.store_id,
        "name": rt.name,
        "slug": rt.slug,
        "labels": rt.labels or {},
        "is_active": rt.is_active,
        "sort_order": rt.sort_order,
    }


def _serialize_item(it: CatalogItem) -> dict:
    return {
        "id": it.id,
        "request_type_id": it.request_type_id,
        "name": it.name,
        "labels": it.labels or {},
        "track_quantity": it.track_quantity,
        "unit": it.unit,
        "is_active": it.is_active,
        "sort_order": it.sort_order,
    }


def _bad(detail: str) -> Response:
    return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)


def _not_found(label: str) -> Response:
    return Response({"detail": f"{label} not found in this org."}, status=status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Tree (read-only convenience for the editor)
# ---------------------------------------------------------------------------


class AdminCatalogTreeView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        stores = list(
            Store.all_objects.filter(organization=ctx.organization).order_by("sort_order", "name"),
        )
        types = list(
            RequestType.all_objects.filter(organization=ctx.organization).order_by("sort_order", "name"),
        )
        items = list(
            CatalogItem.all_objects.filter(organization=ctx.organization).order_by("sort_order", "name"),
        )
        items_by_type: dict[int, list] = {}
        for it in items:
            items_by_type.setdefault(it.request_type_id, []).append(_serialize_item(it))
        types_by_store: dict[int, list] = {}
        for rt in types:
            node = _serialize_request_type(rt)
            node["items"] = items_by_type.get(rt.id, [])
            types_by_store.setdefault(rt.store_id, []).append(node)
        tree = []
        for s in stores:
            node = _serialize_store(s)
            node["request_types"] = types_by_store.get(s.id, [])
            tree.append(node)
        return Response({"stores": tree})


# ---------------------------------------------------------------------------
# Stores
# ---------------------------------------------------------------------------


class AdminStoreListCreateView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        qs = Store.all_objects.filter(organization=ctx.organization).order_by("sort_order", "name")
        return Response({"results": [_serialize_store(s) for s in qs]})

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        data = request.data or {}
        name = (data.get("name") or "").strip()
        if not name:
            return _bad("name is required.")
        role = (data.get("fulfilling_role") or "").strip()
        if role not in dict(Store.FulfillingRole.choices):
            return _bad("fulfilling_role must be 'camper_care' or 'maintenance'.")
        slug = (data.get("slug") or "").strip() or slugify(name)
        program = None
        if data.get("program_id"):
            program = Program.all_objects.filter(
                organization=ctx.organization, pk=data["program_id"],
            ).first()
            if program is None:
                return _not_found("Program")
        if Store.all_objects.filter(organization=ctx.organization, slug=slug).exists():
            return _bad(f"A store with slug {slug!r} already exists.")
        store = Store.all_objects.create(
            organization=ctx.organization,
            program=program,
            name=name,
            slug=slug,
            labels=data.get("labels") or {"en": name},
            fulfilling_role=role,
            is_active=bool(data.get("is_active", True)),
            sort_order=int(data.get("sort_order") or 0),
        )
        return Response(_serialize_store(store), status=status.HTTP_201_CREATED)


class AdminStoreDetailView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def _get(self, ctx, store_id):
        return Store.all_objects.filter(organization=ctx.organization, pk=store_id).first()

    def get(self, request, store_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        store = self._get(ctx, store_id)
        return Response(_serialize_store(store)) if store else _not_found("Store")

    def patch(self, request, store_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        store = self._get(ctx, store_id)
        if store is None:
            return _not_found("Store")
        data = request.data or {}
        changed: list[str] = []
        for field_name in ("name", "slug", "labels", "fulfilling_role", "is_active", "sort_order"):
            if field_name not in data:
                continue
            value = data[field_name]
            if field_name == "fulfilling_role" and value not in dict(Store.FulfillingRole.choices):
                return _bad("fulfilling_role must be 'camper_care' or 'maintenance'.")
            if field_name == "slug":
                value = (value or "").strip() or store.slug
                if value != store.slug and Store.all_objects.filter(
                    organization=ctx.organization, slug=value,
                ).exists():
                    return _bad(f"A store with slug {value!r} already exists.")
            setattr(store, field_name, value)
            changed.append(field_name)
        if "program_id" in data:
            program = None
            if data["program_id"]:
                program = Program.all_objects.filter(
                    organization=ctx.organization, pk=data["program_id"],
                ).first()
                if program is None:
                    return _not_found("Program")
            store.program = program
            changed.append("program")
        if changed:
            store.save(update_fields=[*changed, "updated_at"])
        return Response(_serialize_store(store))

    def delete(self, request, store_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        store = self._get(ctx, store_id)
        if store is None:
            return _not_found("Store")
        store.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Request types
# ---------------------------------------------------------------------------


class AdminRequestTypeListCreateView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        qs = RequestType.all_objects.filter(organization=ctx.organization)
        store_id = request.query_params.get("store")
        if store_id:
            qs = qs.filter(store_id=store_id)
        qs = qs.order_by("sort_order", "name")
        return Response({"results": [_serialize_request_type(rt) for rt in qs]})

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        data = request.data or {}
        name = (data.get("name") or "").strip()
        if not name:
            return _bad("name is required.")
        store = Store.all_objects.filter(
            organization=ctx.organization, pk=data.get("store_id"),
        ).first()
        if store is None:
            return _not_found("Store")
        slug = (data.get("slug") or "").strip() or slugify(name)
        if RequestType.all_objects.filter(store=store, slug=slug).exists():
            return _bad(f"A request type with slug {slug!r} already exists in this store.")
        rt = RequestType.all_objects.create(
            organization=ctx.organization,
            store=store,
            name=name,
            slug=slug,
            labels=data.get("labels") or {"en": name},
            is_active=bool(data.get("is_active", True)),
            sort_order=int(data.get("sort_order") or 0),
        )
        return Response(_serialize_request_type(rt), status=status.HTTP_201_CREATED)


class AdminRequestTypeDetailView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def _get(self, ctx, type_id):
        return RequestType.all_objects.filter(organization=ctx.organization, pk=type_id).first()

    def get(self, request, type_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        rt = self._get(ctx, type_id)
        return Response(_serialize_request_type(rt)) if rt else _not_found("Request type")

    def patch(self, request, type_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        rt = self._get(ctx, type_id)
        if rt is None:
            return _not_found("Request type")
        data = request.data or {}
        changed: list[str] = []
        for field_name in ("name", "slug", "labels", "is_active", "sort_order"):
            if field_name not in data:
                continue
            value = data[field_name]
            if field_name == "slug":
                value = (value or "").strip() or rt.slug
                if value != rt.slug and RequestType.all_objects.filter(
                    store_id=rt.store_id, slug=value,
                ).exists():
                    return _bad(f"A request type with slug {value!r} already exists in this store.")
            setattr(rt, field_name, value)
            changed.append(field_name)
        if changed:
            rt.save(update_fields=[*changed, "updated_at"])
        return Response(_serialize_request_type(rt))

    def delete(self, request, type_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        rt = self._get(ctx, type_id)
        if rt is None:
            return _not_found("Request type")
        rt.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Catalog items
# ---------------------------------------------------------------------------


class AdminCatalogItemListCreateView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        qs = CatalogItem.all_objects.filter(organization=ctx.organization)
        type_id = request.query_params.get("request_type")
        if type_id:
            qs = qs.filter(request_type_id=type_id)
        qs = qs.order_by("sort_order", "name")
        return Response({"results": [_serialize_item(it) for it in qs]})

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        data = request.data or {}
        name = (data.get("name") or "").strip()
        if not name:
            return _bad("name is required.")
        rt = RequestType.all_objects.filter(
            organization=ctx.organization, pk=data.get("request_type_id"),
        ).first()
        if rt is None:
            return _not_found("Request type")
        if CatalogItem.all_objects.filter(request_type=rt, name=name).exists():
            return _bad(f"An item named {name!r} already exists in this request type.")
        it = CatalogItem.all_objects.create(
            organization=ctx.organization,
            request_type=rt,
            name=name,
            labels=data.get("labels") or {"en": name},
            track_quantity=bool(data.get("track_quantity", True)),
            unit=(data.get("unit") or "").strip(),
            is_active=bool(data.get("is_active", True)),
            sort_order=int(data.get("sort_order") or 0),
        )
        return Response(_serialize_item(it), status=status.HTTP_201_CREATED)


class AdminCatalogItemDetailView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def _get(self, ctx, item_id):
        return CatalogItem.all_objects.filter(organization=ctx.organization, pk=item_id).first()

    def get(self, request, item_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        it = self._get(ctx, item_id)
        return Response(_serialize_item(it)) if it else _not_found("Item")

    def patch(self, request, item_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        it = self._get(ctx, item_id)
        if it is None:
            return _not_found("Item")
        data = request.data or {}
        changed: list[str] = []
        for field_name in ("name", "labels", "track_quantity", "unit", "is_active", "sort_order"):
            if field_name not in data:
                continue
            value = data[field_name]
            if field_name == "name":
                value = (value or "").strip() or it.name
                if value != it.name and CatalogItem.all_objects.filter(
                    request_type_id=it.request_type_id, name=value,
                ).exists():
                    return _bad(f"An item named {value!r} already exists in this request type.")
            setattr(it, field_name, value)
            changed.append(field_name)
        if "request_type_id" in data:
            rt = RequestType.all_objects.filter(
                organization=ctx.organization, pk=data["request_type_id"],
            ).first()
            if rt is None:
                return _not_found("Request type")
            it.request_type = rt
            changed.append("request_type")
        if changed:
            it.save(update_fields=[*changed, "updated_at"])
        return Response(_serialize_item(it))

    def delete(self, request, item_id, *args, **kwargs):
        ctx = viewer_or_403(request)
        it = self._get(ctx, item_id)
        if it is None:
            return _not_found("Item")
        it.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# CSV template + import
# ---------------------------------------------------------------------------


class AdminCatalogTemplateView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        viewer_or_403(request)
        filename, csv_text = build_catalog_template_csv()
        response = HttpResponse(csv_text, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class AdminCatalogImportView(APIView):
    """``POST /admin/catalog/import/`` — upload a catalog CSV.

    ``mode=preview`` (default) parses + validates without writing and returns
    the parsed row count + errors. ``mode=commit`` upserts inside a
    transaction. ``deactivate_missing=true`` soft-deletes items absent from
    the CSV (under any touched request type).
    """

    permission_classes = [IsOrgAdminOrSuperuser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        mode = (request.query_params.get("mode") or request.data.get("mode") or "preview").strip().lower()
        deactivate_missing = str(
            request.query_params.get("deactivate_missing")
            or request.data.get("deactivate_missing") or "",
        ).strip().lower() in {"1", "true", "yes"}

        csv_file = request.FILES.get("csv")
        if csv_file is not None:
            try:
                raw = csv_file.read().decode("utf-8-sig")
            except UnicodeDecodeError:
                return _bad("CSV must be UTF-8 encoded.")
        else:
            raw = request.data.get("csv_text") or ""
        if not raw.strip():
            return _bad("CSV file (field 'csv') or 'csv_text' is required.")

        parsed = parse_catalog_csv(raw)
        if mode == "preview" or parsed.errors:
            return Response({
                "mode": "preview",
                "row_count": len(parsed.rows),
                "errors": parsed.errors,
                "valid": not parsed.errors,
            }, status=status.HTTP_200_OK if not parsed.errors else status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            summary = apply_catalog_import(
                ctx.organization, parsed.rows, deactivate_missing=deactivate_missing,
            )
        return Response({"mode": "commit", "row_count": len(parsed.rows), "summary": summary})
