# Counselor walkthrough — fill bunk logs for assigned campers

A guided manual click-through of the new multi-tenant per-camper
reflection flow, using the RBAC test bench from
[`docs/rbac-test-plan.md`](rbac-test-plan.md). At the end of this
walkthrough you'll have logged today's "bunk log" for both campers
assigned to your bunk.

## 0. Prereqs

```bash
make up                # postgres + redis + django (+ mailpit)
make frontend-dev      # vite on :5173 (in another terminal)
make seed-rbac         # idempotent; resets the RBAC fixture
```

After re-running `make seed-rbac`, today's per-camper reflections start
uncovered (you're about to fill them in). If you complete the
walkthrough and want to do it again, just re-run `make seed-rbac`.

## 1. Sign in

Open `http://localhost:5173/signin` and sign in with:

| Field    | Value                            |
| -------- | -------------------------------- |
| Email    | `rbac-counselor@example.test`    |
| Password | `rbacpass123`                    |

You'll land on **Counselor Dashboard** (`/counselor-dashboard` with today's
date). The user banner in the top right should read **RBAC Counselor —
Counselor**.

## 2. Find today's tasks

Scroll to the **Today's tasks** card at the top of the page — it's the same
data as the standalone tasks screen (`/tasks`). You'll see a progress bar and
a long list of "self" tasks (one per active template in the org). The section
you need is near the bottom and is the **only card with camper pills**:

> **RBAC test — Camper daily check-in**
> Group: **RBAC Bunk Maple**
> Period: today's date
> Subjects: **Alex RbacCamperA** · **Bree RbacCamperB**

Optional: click **Open full-screen** (or use **Tests → Tasks** for admins who
have that menu) to open `http://localhost:5173/tasks` instead.

Both campers should show an empty circle (uncovered).

## 3. Fill out the bunk log for Alex

Click the **Alex RbacCamperA** pill. The form opens at
`/reflect?template=…&assignment_group=…&subject=…&subject_name=Alex…`
with the heading "RBAC test — Camper daily check-in" and a "Subject:
Alex RbacCamperA" header.

Fill in the form exactly like this:

| Field                        | Type           | Value                                                          |
| ---------------------------- | -------------- | -------------------------------------------------------------- |
| Camper not on camp today     | Yes/No         | **No — camper was on camp**                                    |
| Unit Head help requested     | Yes/No         | **No**                                                         |
| Camper Care help requested   | Yes/No         | **No**                                                         |
| Behavior                     | 1–5 rating     | **5 — Excellent**                                              |
| Participation                | 1–5 rating     | **4**                                                          |
| Social                       | 1–5 rating     | **5 — Excellent**                                              |
| Daily report                 | textarea       | _Strong day for Alex — led group cleanup and helped a peer settle into the cabin._ |

Click **Submit**. You should see a success toast / redirect, and the
URL changes to `/tasks` (or you can navigate back manually).

Alex's pill should now show a green checkmark.

## 4. Fill out the bunk log for Bree

Click the **Bree RbacCamperB** pill on the same task card. Fill in:

| Field                        | Type           | Value                                                                            |
| ---------------------------- | -------------- | -------------------------------------------------------------------------------- |
| Camper not on camp today     | Yes/No         | **No — camper was on camp**                                                      |
| Unit Head help requested     | Yes/No         | **No**                                                                           |
| Camper Care help requested   | Yes/No         | **Yes**                                                                          |
| Behavior                     | 1–5 rating     | **3**                                                                            |
| Participation                | 1–5 rating     | **2**                                                                            |
| Social                       | 1–5 rating     | **3**                                                                            |
| Daily report                 | textarea       | _Bree was withdrawn at lunch and skipped afternoon free play. Asked Camper Care to follow up tomorrow._ |

Click **Submit**.

After both submissions, the task card on `/tasks` shows
**Coverage: 2 / 2** with both pills green.

## 5. Verify what you just did

### a. Your reflections appear in your list

Navigate to:

> `http://localhost:5173/my-reflections`
> _(or `/counselor-dashboard` → Recent reflections)_

You should see **two** new entries from today, one per camper, both
authored by you on the **RBAC test — Camper daily check-in** template.

### b. The unit head can see your work

Sign out (top-right user menu → Sign out), then sign back in as the
unit head:

| Email    | `rbac-unit-head@example.test`  |
| Password | `rbacpass123`                  |

Navigate to `/supervisor/coverage`. The **RBAC Bunk Maple** group
should show **2 / 2** coverage on today's row, attributed to you
(RBAC Counselor).

### c. The Camper Care follow-up flag surfaces

Still as the unit head (or sign in as
`rbac-camper-care@example.test`), open `/dashboards/concerns/`. Bree's
reflection should appear in the inbox because you set
`request_camper_care_help = Yes`.

## 6. Reset and try again

```bash
make seed-rbac    # wipes today's per-camper reflections, restores empty pills
```

Re-running is safe; it leaves your other RBAC test fixtures intact.

## 7. What this exercises (for reviewers)

- `subject_mode = 'single_subject'` — one Reflection per camper subject
  rather than one per author
- `assignment_group_types = ['bunk']` — the template is only bound to
  bunk-typed AssignmentGroups
- `author_role_filter = ['counselor', 'unit_head']` — both roles can
  log on behalf of a camper
- `subject_role_filter = ['camper']` — only Persons with a `camper`
  Membership appear in the pill list
- The **bunk-log shape** (yes/no toggles + 1–5 category ratings + free
  text) is intentionally identical to the legacy
  `BunkLogForm.jsx` so reviewers can compare side-by-side and confirm
  the new flow is a credible replacement before we sunset the legacy
  endpoints.

## 8. Troubleshooting

| Symptom                                                                              | Most likely cause                                                                                                  |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| `/tasks` shows no card with camper pills                                             | The seed didn't run — execute `make seed-rbac` and reload                                                          |
| The form returns "Reflection already exists for this period"                          | You already submitted it today — `make seed-rbac` to reset, or change `period_start`/`period_end` in the URL       |
| The pills are present but greyed out as "covered by …"                                | Someone else (or a previous run) authored them; `make seed-rbac` resets                                            |
| Spanish prompts appear instead of English                                             | Browser sent `Accept-Language: es` and the template only declares `en`; force `?language=en` in the form URL       |
| 401 / redirected to `/signin` mid-session                                             | JWT expired (default 5 min); sign in again — the SPA usually refreshes automatically but a long pause can lapse it |
