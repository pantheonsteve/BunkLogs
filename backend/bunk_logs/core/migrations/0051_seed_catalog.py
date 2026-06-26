"""Seed the configurable catalog for Crane Lake (org slug 'clc') and migrate
any existing OrderItemSuggestion rows into Camper Care catalog items.

Idempotent: re-running is a no-op (get_or_create on stable slugs/names).
Scoped to org slug 'clc' for the matrix seed so preview/TBE environments
aren't populated with Crane Lake's catalog. The OrderItemSuggestion copy is
generic across whatever programs have rows.

Reversible to a no-op (we never delete on reverse — catalog data, once edited
by an admin, must not be silently destroyed by a downgrade).
"""

from __future__ import annotations

from django.db import migrations
from django.utils.text import slugify

# (store_name, fulfilling_role, [(request_type, track_quantity, [items...]), ...])
CATALOG = [
    (
        "Maintenance",
        "maintenance",
        [
            (
                "Maintenance Items Request",
                True,
                [
                    "Toilet Paper", "Paper Towels", "Garbage Bags", "Shower Curtain",
                    "Hand Soap", "Cleaning Spray", "Sponge", "Mop head", "Mop stick",
                    "Broom", "Dustpan", "Cleaning wipes", "Plunger", "Toilet Brush",
                    "Lightbulb",
                ],
            ),
            (
                "Maintenance Service Request",
                False,
                [
                    "Lightbulb changed out of counselor reach",
                    "Door or hinge replaced",
                    "Clogged toilet - after counselor has attempted to unclog",
                    "Leak",
                    "Clogged sink or shower",
                    "Window or door not opening/closing properly",
                    "Window screen missing",
                    "Critter in the bunk",
                    "Broken or missing bed part",
                    "Infestation",
                    "Wasp or Bee nest",
                ],
            ),
        ],
    ),
    (
        "Camper Care",
        "camper_care",
        [
            (
                "Camper Care Items Request",
                True,
                [
                    "Toothbrush", "Toothpaste", "Chapstick", "Hair Ties", "Hairbrush",
                    "Nail Clippers", "Deodorant", "Shampoo", "Conditioner", "Body Wash",
                    "Water Bottles", "Underwear", "Socks", "Bug Spray", "Sunscreen",
                    "Batteries", "Flashlights", "Night Lights",
                ],
            ),
        ],
    ),
]


def _seed_catalog_for_org(apps, organization):
    Store = apps.get_model("core", "Store")
    RequestType = apps.get_model("core", "RequestType")
    CatalogItem = apps.get_model("core", "CatalogItem")

    for store_sort, (store_name, role, types) in enumerate(CATALOG):
        store, _ = Store.objects.get_or_create(
            organization=organization,
            slug=slugify(store_name),
            defaults={
                "name": store_name,
                "labels": {"en": store_name},
                "fulfilling_role": role,
                "sort_order": store_sort,
            },
        )
        for type_sort, (type_name, track_quantity, items) in enumerate(types):
            rt, _ = RequestType.objects.get_or_create(
                store=store,
                slug=slugify(type_name),
                defaults={
                    "organization": organization,
                    "name": type_name,
                    "labels": {"en": type_name},
                    "sort_order": type_sort,
                },
            )
            for item_sort, item_name in enumerate(items):
                CatalogItem.objects.get_or_create(
                    request_type=rt,
                    name=item_name,
                    defaults={
                        "organization": organization,
                        "labels": {"en": item_name},
                        "track_quantity": track_quantity,
                        "sort_order": item_sort,
                    },
                )


def _copy_order_item_suggestions(apps):
    """Mirror existing per-program OrderItemSuggestion labels into Camper Care items."""
    OrderItemSuggestion = apps.get_model("core", "OrderItemSuggestion")
    Store = apps.get_model("core", "Store")
    RequestType = apps.get_model("core", "RequestType")
    CatalogItem = apps.get_model("core", "CatalogItem")

    program_ids = (
        OrderItemSuggestion.objects.values_list("program_id", flat=True).distinct()
    )
    Program = apps.get_model("core", "Program")
    for program_id in program_ids:
        program = Program.objects.filter(pk=program_id).select_related("organization").first()
        if program is None:
            continue
        org = program.organization
        store, _ = Store.objects.get_or_create(
            organization=org,
            slug=slugify("Camper Care"),
            defaults={
                "name": "Camper Care",
                "labels": {"en": "Camper Care"},
                "fulfilling_role": "camper_care",
            },
        )
        rt, _ = RequestType.objects.get_or_create(
            store=store,
            slug=slugify("Camper Care Items Request"),
            defaults={
                "organization": org,
                "name": "Camper Care Items Request",
                "labels": {"en": "Camper Care Items Request"},
            },
        )
        rows = OrderItemSuggestion.objects.filter(program_id=program_id)
        for row in rows:
            CatalogItem.objects.get_or_create(
                request_type=rt,
                name=row.label,
                defaults={
                    "organization": org,
                    "labels": {"en": row.label},
                    "track_quantity": True,
                    "is_active": row.is_active,
                    "sort_order": row.sort_order,
                },
            )


def forwards(apps, schema_editor):
    Organization = apps.get_model("core", "Organization")
    clc = Organization.objects.filter(slug="clc").first()
    if clc is not None:
        _seed_catalog_for_org(apps, clc)
    _copy_order_item_suggestions(apps)


def backwards(apps, schema_editor):
    # Intentional no-op: never destroy admin-editable catalog data on downgrade.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0050_requesttype_catalogitem_store_requesttype_store_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
