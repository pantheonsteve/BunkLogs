#!/usr/bin/env bash
#
# Populate a local Temple Beth-El (TBE) sandbox with real data so every
# Madrich / Faculty / Admin surface from migration_prompts/4_1 through
# 4_8 (org setup, weekly 3-2-1 reflections, availability calendar,
# classroom challenge log) has something to look at.
#
# Wraps the existing `setup_tbe` + `seed_tbe_dev_data` management
# commands (already exposed as `make setup-tbe` / `make seed-tbe`) and
# prints a walkthrough of exactly which URL to visit for each surface,
# as which seeded person, once it's done.
#
# Usage:
#   ./scripts/seed_tbe_local.sh            # idempotent create/refresh
#   ./scripts/seed_tbe_local.sh --reset    # wipe + recreate seeded data
#
# Requires containers to be reachable (starts them via `make up` if
# they aren't already running) and DEBUG=True locally (default for
# docker-compose.local.yml), which is what powers the passwordless
# "Dev: view as user" picker this script tells you to use.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

DJANGO_CONTAINER="bunk_logs_local_django"
RESET_FLAG=""
if [[ "${1:-}" == "--reset" ]]; then
  RESET_FLAG="--reset"
fi

django_manage() {
  podman exec "$DJANGO_CONTAINER" python manage.py "$@"
}

echo "==> Checking containers..."
if ! podman ps --filter "name=${DJANGO_CONTAINER}" --filter "status=running" --format '{{.Names}}' \
    | grep -q "^${DJANGO_CONTAINER}$"; then
  echo "    Not running yet -- starting (make up)..."
  make up
  echo "    Waiting for postgres..."
  sleep 8
fi

echo "==> Applying migrations..."
django_manage migrate

echo "==> Ensuring Temple Beth-El org + 2026-27 program (setup_tbe)..."
django_manage setup_tbe

echo "==> Seeding TBE dev sandbox (seed_tbe_dev_data ${RESET_FLAG})..."
django_manage seed_tbe_dev_data ${RESET_FLAG}

echo "==> Looking up the seeded classroom's dashboard id..."
CLASSROOM_ID="$(django_manage shell -c "
from bunk_logs.core.models import AssignmentGroup
g = AssignmentGroup.all_objects.filter(organization__slug='tbe', slug='dev-test-classroom').first()
print(g.id if g else '')
" | tr -d '\r' | tail -n 1)"

cat <<EOF

============================================================
 TBE local sandbox ready
============================================================

Frontend:      http://localhost:5173  (run 'make frontend-dev' in another terminal if it's not up)
Backend:       http://localhost:8000
Django admin:  http://localhost:8000/admin/

LOGGING IN AS EACH PERSON
  Use the "Dev: view as user" picker in the bottom-left corner of the
  app (only shown when DEBUG=True + local DB -- no password needed).
  Search by the email addresses below and click to sign in as them.
  (Real password login also works -- shared password: tbedevpass123)

------------------------------------------------------------
Madrich (grade 8) -- tbe-dev-madrich-8@example.test
  /madrich                    Dashboard: 3-2-1 + Mid-Year Check-In cards,
                               availability card, "Report a challenge" card
  /madrich/availability       Sunday availability calendar (Step 4_7)
  /madrich/challenges         Challenge log -- "My reports" tab shows THEIR
                               own open challenge by name; "Our classroom"
                               tab shows grade 9's resolved challenge
                               redacted to "A Madrich" (MA7 semi-anonymity)
  /madrich/challenges/new     Report a new challenge (disclosure footer)
  /madrich/history            Weekly reflection history

Madrich (grade 9) -- tbe-dev-madrich-9@example.test
  Same surfaces as above, mirrored: their own resolved challenge (with a
  faculty reply) is visible by name under "My reports"; grade 8's open
  challenge shows redacted under "Our classroom".

Faculty -- tbe-dev-faculty@example.test
  /faculty/challenges          Inbox: both seeded challenges, full author
                                names visible (faculty never sees "A Madrich")
  /faculty/challenges/:id      Detail -- Acknowledge / Resolve + reply box
EOF

if [[ -n "$CLASSROOM_ID" ]]; then
  echo "  /dashboards/group/${CLASSROOM_ID}       Classroom dashboard -- \"Open challenges\" section"
  echo "                                (replaces the old reflections-not-configured stub)"
else
  echo "  /dashboards/group/:id        Classroom dashboard -- \"Open challenges\" section"
  echo "                               (could not resolve the seeded classroom id -- see above for errors)"
fi

cat <<EOF

Admin -- tbe-dev-admin@example.test
  /admin/reflections            Weekly 3-2-1 completion, filterable by grade
  /admin/reflections/availability  Madrichim x Sunday staffing matrix (4_7)
  Classroom challenges have no dedicated admin UI in Tier 1 -- reachable via
  GET /api/v1/admin/classroom-challenges/ and .../export.csv (bearer auth).

------------------------------------------------------------
Re-run any time -- idempotent. Pass --reset to wipe and recreate:
  ./scripts/seed_tbe_local.sh --reset
============================================================
EOF
