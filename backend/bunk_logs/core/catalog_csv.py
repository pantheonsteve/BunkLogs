"""CSV import/export for the configurable catalog (Store / RequestType / CatalogItem).

One row == one catalog item. Stores and request types are upserted by name as
rows are processed, so the whole tree can be defined in a single sheet. Spanish
labels are optional per row; English labels default to the canonical name.

Public surface:

* ``CATALOG_IMPORT_COLUMNS`` — canonical header order.
* ``build_catalog_template_csv()`` — downloadable starter template.
* ``parse_catalog_csv(text)`` — parse + validate; returns ``(rows, errors)``.
* ``apply_catalog_import(org, rows, *, deactivate_missing)`` — idempotent upsert.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from django.utils.text import slugify

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization

CATALOG_IMPORT_COLUMNS: tuple[str, ...] = (
    "store",
    "fulfilling_role",
    "request_type",
    "item_name",
    "label_es",
    "track_quantity",
    "unit",
    "sort_order",
    "is_active",
)

VALID_FULFILLING_ROLES = frozenset({"camper_care", "maintenance"})

_TRUE = frozenset({"1", "true", "yes", "y", "t"})
_FALSE = frozenset({"0", "false", "no", "n", "f", ""})


@dataclass
class CatalogRow:
    store: str
    fulfilling_role: str
    request_type: str
    item_name: str
    label_es: str = ""
    track_quantity: bool = True
    unit: str = ""
    sort_order: int = 0
    is_active: bool = True


@dataclass
class ParseResult:
    rows: list[CatalogRow] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _coerce_bool(raw: str, *, default: bool) -> bool:
    value = (raw or "").strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False if value else default
    return default


def build_catalog_template_csv() -> tuple[str, str]:
    """Return ``(filename, csv_text)`` for a downloadable starter template."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CATALOG_IMPORT_COLUMNS)
    writer.writerow([
        "Maintenance", "maintenance", "Maintenance Items Request",
        "Toilet Paper", "Papel higiénico", "true", "roll", "1", "true",
    ])
    writer.writerow([
        "Maintenance", "maintenance", "Maintenance Service Request",
        "Clogged toilet", "Inodoro tapado", "false", "", "1", "true",
    ])
    writer.writerow([
        "Camper Care", "camper_care", "Camper Care Items Request",
        "Toothbrush", "Cepillo de dientes", "true", "", "1", "true",
    ])
    return "catalog_import_template.csv", buf.getvalue()


def parse_catalog_csv(text: str) -> ParseResult:
    """Parse + validate a catalog CSV. Never raises on row-level issues.

    Stores the ``fulfilling_role`` seen for each store so later rows may omit
    it. Validation errors are collected per 1-based data row (header is row 1).
    """
    result = ParseResult()
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        result.errors.append("CSV is empty or has no header row.")
        return result

    normalized_headers = {(h or "").strip().lower() for h in reader.fieldnames}
    required = {"store", "request_type", "item_name"}
    missing = required - normalized_headers
    if missing:
        result.errors.append(
            f"Missing required column(s): {', '.join(sorted(missing))}.",
        )
        return result

    store_roles: dict[str, str] = {}
    for idx, raw in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        store = row.get("store", "")
        request_type = row.get("request_type", "")
        item_name = row.get("item_name", "")
        if not (store or request_type or item_name):
            continue  # blank line
        row_errs: list[str] = []
        if not store:
            row_errs.append("missing store")
        if not request_type:
            row_errs.append("missing request_type")
        if not item_name:
            row_errs.append("missing item_name")

        role = row.get("fulfilling_role", "")
        if role:
            if role not in VALID_FULFILLING_ROLES:
                row_errs.append(
                    f"invalid fulfilling_role {role!r} "
                    f"(expected one of {', '.join(sorted(VALID_FULFILLING_ROLES))})",
                )
            elif store:
                store_roles[store] = role
        elif store and store in store_roles:
            role = store_roles[store]
        elif store and not row_errs:
            row_errs.append(
                f"fulfilling_role required the first time store {store!r} appears",
            )

        sort_raw = row.get("sort_order", "")
        sort_order = 0
        if sort_raw:
            try:
                sort_order = int(sort_raw)
            except ValueError:
                row_errs.append(f"sort_order {sort_raw!r} is not an integer")

        if row_errs:
            result.errors.append(f"Row {idx}: {'; '.join(row_errs)}.")
            continue

        result.rows.append(CatalogRow(
            store=store,
            fulfilling_role=role,
            request_type=request_type,
            item_name=item_name,
            label_es=row.get("label_es", ""),
            track_quantity=_coerce_bool(row.get("track_quantity", ""), default=True),
            unit=row.get("unit", ""),
            sort_order=sort_order,
            is_active=_coerce_bool(row.get("is_active", ""), default=True),
        ))
    return result


def _labels(name: str, label_es: str) -> dict:
    labels = {"en": name}
    if label_es:
        labels["es"] = label_es
    return labels


def apply_catalog_import(
    organization: Organization,
    rows: list[CatalogRow],
    *,
    deactivate_missing: bool = False,
) -> dict:
    """Idempotently upsert Stores / RequestTypes / CatalogItems for ``organization``.

    Keying: Store by ``(organization, slug)``, RequestType by ``(store, slug)``,
    CatalogItem by ``(request_type, name)``. Re-running the same CSV is a no-op.
    When ``deactivate_missing`` is True, catalog items under any touched
    request type that are NOT present in the CSV are marked ``is_active=False``
    (soft delete) rather than removed, preserving line-item history.
    """
    from bunk_logs.core.models import CatalogItem
    from bunk_logs.core.models import RequestType
    from bunk_logs.core.models import Store

    summary = {
        "stores_created": 0,
        "request_types_created": 0,
        "items_created": 0,
        "items_updated": 0,
        "items_deactivated": 0,
    }
    store_cache: dict[str, Store] = {}
    type_cache: dict[tuple[int, str], RequestType] = {}
    seen_item_ids_by_type: dict[int, set[int]] = {}

    for row in rows:
        store_slug = slugify(row.store)
        store = store_cache.get(store_slug)
        if store is None:
            store, created = Store.all_objects.get_or_create(
                organization=organization,
                slug=store_slug,
                defaults={
                    "name": row.store,
                    "fulfilling_role": row.fulfilling_role or Store.FulfillingRole.CAMPER_CARE,
                    "labels": {"en": row.store},
                },
            )
            if created:
                summary["stores_created"] += 1
            elif row.fulfilling_role and store.fulfilling_role != row.fulfilling_role:
                store.fulfilling_role = row.fulfilling_role
                store.save(update_fields=["fulfilling_role"])
            store_cache[store_slug] = store

        type_slug = slugify(row.request_type)
        type_key = (store.id, type_slug)
        request_type = type_cache.get(type_key)
        if request_type is None:
            request_type, created = RequestType.all_objects.get_or_create(
                store=store,
                slug=type_slug,
                defaults={
                    "organization": organization,
                    "name": row.request_type,
                    "labels": {"en": row.request_type},
                },
            )
            if created:
                summary["request_types_created"] += 1
            type_cache[type_key] = request_type
            seen_item_ids_by_type.setdefault(request_type.id, set())

        item, created = CatalogItem.all_objects.get_or_create(
            request_type=request_type,
            name=row.item_name,
            defaults={
                "organization": organization,
                "labels": _labels(row.item_name, row.label_es),
                "track_quantity": row.track_quantity,
                "unit": row.unit,
                "sort_order": row.sort_order,
                "is_active": row.is_active,
            },
        )
        if created:
            summary["items_created"] += 1
        else:
            item.labels = _labels(row.item_name, row.label_es)
            item.track_quantity = row.track_quantity
            item.unit = row.unit
            item.sort_order = row.sort_order
            item.is_active = row.is_active
            item.save(update_fields=[
                "labels", "track_quantity", "unit", "sort_order", "is_active",
            ])
            summary["items_updated"] += 1
        seen_item_ids_by_type.setdefault(request_type.id, set()).add(item.id)

    if deactivate_missing:
        for type_id, seen_ids in seen_item_ids_by_type.items():
            stale = CatalogItem.all_objects.filter(
                request_type_id=type_id, is_active=True,
            ).exclude(id__in=seen_ids)
            summary["items_deactivated"] += stale.update(is_active=False)

    return summary
