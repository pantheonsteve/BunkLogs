"""Catalog resolution helpers shared by the counselor write flows.

Centralizes "what items can this org/program pick from?" and "turn a
submitted line-item payload into validated RequestLineItem kwargs" so the
camper-care and maintenance endpoints agree on the same rules.

Reads use ``all_objects`` + explicit org filters (the request already carries
org context, but these helpers are also called from places without it).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q
from rest_framework import serializers

from bunk_logs.core.models import CatalogItem
from bunk_logs.core.models import OrderItemSuggestion
from bunk_logs.core.models import Store

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program


def active_items_for_role(organization, program, role):
    """Active CatalogItems whose store has ``fulfilling_role == role``.

    Stores scoped to a specific program are included only when that program
    matches; org-wide stores (``program IS NULL``) always apply.
    """
    stores = Store.all_objects.filter(
        organization=organization, fulfilling_role=role, is_active=True,
    )
    if program is not None:
        stores = stores.filter(Q(program__isnull=True) | Q(program=program))
    else:
        stores = stores.filter(program__isnull=True)
    store_ids = list(stores.values_list("id", flat=True))
    return (
        CatalogItem.all_objects.filter(
            organization=organization,
            is_active=True,
            request_type__store_id__in=store_ids,
        )
        .select_related("request_type", "request_type__store")
        .order_by("sort_order", "name")
    )


def camper_care_item_options(organization: Organization, program: Program | None) -> list[dict]:
    """Autocomplete options for the camper-care request form.

    Reads the configurable catalog first. Falls back to legacy
    ``OrderItemSuggestion`` rows for the program when no Camper Care catalog
    items are configured yet, so programs that haven't been migrated keep
    their curated list working.
    """
    options = [
        {"id": str(it.id), "label": it.name, "sort_order": it.sort_order}
        for it in active_items_for_role(organization, program, "camper_care")
    ]
    if options or program is None:
        return options
    return [
        {"id": None, "label": s.label, "sort_order": s.sort_order}
        for s in OrderItemSuggestion.all_objects.filter(
            program=program, is_active=True,
        ).order_by("sort_order", "label")
    ]


def maintenance_options(organization: Organization, program: Program | None) -> dict:
    """Maintenance store config grouped by request type for the ticket form.

    Returns request types with their items; ``track_quantity`` lets the client
    render services (single pick) vs consumables (with a quantity input).
    """
    items = active_items_for_role(organization, program, "maintenance")
    by_type: dict[int, dict] = {}
    for it in items:
        rt = it.request_type
        bucket = by_type.setdefault(rt.id, {
            "id": rt.id,
            "name": rt.name,
            "slug": rt.slug,
            "sort_order": rt.sort_order,
            "items": [],
        })
        bucket["items"].append({
            "id": str(it.id),
            "label": it.name,
            "track_quantity": it.track_quantity,
            "unit": it.unit,
            "sort_order": it.sort_order,
        })
    request_types = sorted(by_type.values(), key=lambda r: (r["sort_order"], r["name"]))
    return {"request_types": request_types}


def resolve_line_items(
    organization,
    program,
    role: str,
    lines: list[dict] | None,
    *,
    legacy_item: str = "",
    legacy_note: str = "",
) -> list[dict]:
    """Validate a line-item payload into RequestLineItem kwargs.

    ``lines`` come from :class:`RequestLineItemSerializer`. Each ``item_id``
    must reference an active catalog item for this org + role (else 400). When
    ``lines`` is empty and ``legacy_item`` is given, a single line is built
    from it (matched to a catalog item by exact name when possible).

    Returns a list of dicts with keys ``item`` (CatalogItem | None),
    ``item_label``, ``quantity``, ``note``.
    """
    valid = {it.id: it for it in active_items_for_role(organization, program, role)}
    by_name = {it.name.casefold(): it for it in valid.values()}

    resolved: list[dict] = []
    if lines:
        for line in lines:
            item_id = line.get("item_id")
            item = None
            if item_id:
                item = valid.get(int(item_id))
                if item is None:
                    msg = f"Unknown or inactive catalog item id {item_id}."
                    raise serializers.ValidationError({"line_items": msg})
            label = item.name if item else (line.get("item_label") or "").strip()
            if not label:
                msg = "Each line item needs item_id or item_label."
                raise serializers.ValidationError({"line_items": msg})
            resolved.append({
                "item": item,
                "item_label": label[:120],
                "quantity": int(line.get("quantity") or 1),
                "note": line.get("note") or "",
            })
        return resolved

    label = (legacy_item or "").strip()
    if label:
        resolved.append({
            "item": by_name.get(label.casefold()),
            "item_label": label[:120],
            "quantity": 1,
            "note": legacy_note or "",
        })
    return resolved
