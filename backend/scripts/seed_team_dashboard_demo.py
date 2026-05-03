"""Seed minimal data so /team/dashboard renders meaningful content for org `clc`.

Run inside the django container:

    python manage.py shell < /app/scripts/seed_team_dashboard_demo.py

Idempotent. Targets organization=clc, program=summer-2026.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model

from bunk_logs.core.models import (
    Membership,
    Organization,
    Person,
    Program,
    Reflection,
    ReflectionTemplate,
)

User = get_user_model()

ORG_SLUG = "clc"
PROGRAM_SLUG = "summer-2026"

org = Organization.objects.get(slug=ORG_SLUG)
program = Program.all_objects.get(organization=org, slug=PROGRAM_SLUG)


def upsert_template():
    schema = {
        "fields": [
            {
                "key": "pulse",
                "type": "rating_group",
                "scale": [1, 4],
                "scale_labels": {"en": ["1", "2", "3", "4"]},
                "categories": [
                    {"key": "morale", "labels": {"en": "Morale"}},
                    {"key": "support", "labels": {"en": "Support"}},
                ],
            },
            {
                "key": "primary_concern",
                "type": "textarea",
                "required": False,
                "prompts": {"en": "One concern or question?"},
            },
        ],
    }
    tpl = ReflectionTemplate.all_objects.filter(
        organization=org, slug="demo-counselor-pulse",
    ).order_by("-version").first()
    if tpl is None:
        tpl = ReflectionTemplate.all_objects.create(
            organization=org,
            name="Demo counselor pulse",
            slug="demo-counselor-pulse",
            cadence="weekly",
            role="counselor",
            program_type="summer_camp",
            languages=["en"],
            schema=schema,
            version=1,
            is_active=True,
        )
        print(f"Created template id={tpl.id}")
    else:
        if tpl.schema != schema or not tpl.is_active:
            tpl.schema = schema
            tpl.is_active = True
            tpl.save(update_fields=["schema", "is_active"])
            print(f"Updated template id={tpl.id}")
        else:
            print(f"Template id={tpl.id} already current")
    return tpl


def upsert_person(email, first, last):
    user, _ = User.objects.get_or_create(
        email=email,
        defaults={"first_name": first, "last_name": last, "is_active": True},
    )
    person = Person.all_objects.filter(user=user).first()
    if person is None:
        person, _ = Person.all_objects.get_or_create(
            organization=org,
            email=email,
            defaults={"first_name": first, "last_name": last, "user": user},
        )
        if person.user_id != user.id:
            person.user = user
            person.save(update_fields=["user"])
    return person


def upsert_staff(email, first, unit_slug, year_round=False):
    person = upsert_person(email, first, "Demo")
    tags = ["year_round"] if year_round else []
    m, _created = Membership.all_objects.get_or_create(
        program=program,
        person=person,
        role="counselor",
        defaults={"is_active": True, "metadata": {"unit_slug": unit_slug}, "tags": tags},
    )
    changed = False
    if m.metadata.get("unit_slug") != unit_slug:
        m.metadata = {**(m.metadata or {}), "unit_slug": unit_slug}
        changed = True
    if m.tags != tags:
        m.tags = tags
        changed = True
    if not m.is_active:
        m.is_active = True
        changed = True
    if changed:
        m.save(update_fields=["metadata", "tags", "is_active"])
    return person


def upsert_reflection(template, person, period_end, morale, support, concern):
    period_start = period_end - timedelta(days=6)
    obj, created = Reflection.all_objects.update_or_create(
        program=program,
        person=person,
        template=template,
        period_end=period_end,
        defaults={
            "organization": org,
            "period_start": period_start,
            "answers": {
                "pulse": {"morale": morale, "support": support},
                "primary_concern": concern,
            },
            "language": "en",
            "is_complete": True,
        },
    )
    return obj, created


template = upsert_template()

p_tsofim_yr = upsert_staff("demo-cns-tsofim-yr@example.test", "Tsofim-YR", "tsofim", year_round=True)
p_tsofim_s = upsert_staff("demo-cns-tsofim-s@example.test", "Tsofim-S", "tsofim", year_round=False)
p_bochur_yr = upsert_staff("demo-cns-bochur-yr@example.test", "Bochur-YR", "bochurim", year_round=True)
p_bochur_s = upsert_staff("demo-cns-bochur-s@example.test", "Bochur-S", "bochurim", year_round=False)

today = date.today()
cur_end = today
cur_pe = today - timedelta(days=2)
prev_pe = today - timedelta(days=16)

submissions = [
    (p_tsofim_yr, cur_pe, 4, 4, "All good — kids settling in."),
    (p_tsofim_s, cur_pe, 3, 3, ""),
    (p_bochur_yr, cur_pe, 2, 1, "Need more coverage on overnights — please advise."),

    (p_tsofim_yr, prev_pe, 3, 3, "Last week was rough on day 1."),
    (p_bochur_yr, prev_pe, 2, 2, "Same overnight question as last week."),
]
created_count = 0
updated_count = 0
for person, pe, morale, support, concern in submissions:
    _, created = upsert_reflection(template, person, pe, morale, support, concern)
    created_count += int(created)
    updated_count += int(not created)

print(
    f"Reflections — created={created_count}, updated={updated_count}. "
    f"Open /team/dashboard with Period ends={cur_end.isoformat()} to see the current window.",
)
