# Madrich (TBE) Flow — Stories 61-65

## TBE Tier 1 scope constraints

| Concern | Camp scope | TBE Tier 1 |
|---|---|---|
| Languages | English, Spanish, Hebrew content; English, Spanish UI | English only |
| Cadence | Daily | Weekly |
| Multi-grade content | Single template across roles | Single template for grades 8-12 Tier 1; differentiation Tier 2 |

## Story 61: Sign in and land on weekly-reflection-focused dashboard

### Acceptance criteria

1. Sign-in per Story 1. TBE Madrichim via Google SSO with Gmail or school account.
2. Post-login is Madrich dashboard, scoped to active TBE religious-school Program.
3. Sections: **Header** (user name, role "Madrich", grade level 8-12, active program e.g., "TBE Religious School 2026-27"), **My reflection** card (current week per criterion 5), **My reflections** entry (Story 65).
4. NO display of: student rosters, faculty submissions, other Madrichim, completion counts beyond own, camp-side signal.
5. My reflection card displays current week:
   1. Period framing: *"Week of [start]-[end]"*. Default Monday-Sunday per MA1.
   2. States: **Not yet started** / **Draft** / **Submitted for this week**
   3. NO daily incompleteness states. Framing "current week: not yet submitted."
6. "Current week" respects rollover boundary and program's configured week-boundary day.
7. All dashboard text in English Tier 1. Platform's UI translation infra exists but not activated.
8. FCP under 2s on mid-tier Android 4G.

### Decisions

- MA1: Monday-Sunday week boundary.
- MA2: Wednesday evening reminder for unsubmitted week.

## Story 62: Submit and edit weekly 3-2-1 reflection

### Acceptance criteria

1. Tap My reflection card opens TBE 3-2-1 template:
   1. **3 wins** — text_list, exactly 3 items, required
   2. **2 improvements** — text_list, exactly 2 items, required
   3. **1 question or concern** — text, required
   4. **5 ratings** — rating_group, 5 categories from Rachel's proposal (Reliability & Punctuality, Initiative, Communication, Problem Solving, Interpersonal), 1-4 scale (Unsatisfactory/Needs Improvement/Meets Expectations/Exceeds Expectations)
2. Form follows Story 5 draft and submission patterns. Network-tolerant per Story 8.
3. NO day-off toggle. Missed Sunday session: reflect on what happened, or don't submit. No "day off" state for weekly.
4. Submission returns to dashboard, card in **Submitted for this week**.
5. Edit window: **current reflection period**, edit until week closes.
6. After week closes: read-only. No Edit affordance.
7. `language` = English. TBE Tier 1 doesn't exercise multilingual path.
8. AudienceDisclosure on form: *"This reflection will be visible to: Your Director, TBE Admin."*

### Decisions

- MA3: Single template grades 8-12 Tier 1; differentiation Tier 2.

## Story 63: Receive templates Director assigns

### Acceptance criteria

1. Newly assigned template appears in dashboard from start date forward.
2. Multiple concurrent templates: each as separate card (recurring weekly 3-2-1 + one-time mid-year + on-demand).
3. Each card displays: period framing or "available to submit", submission state, cadence-appropriate edit window.
4. Email notification for new assignments via existing reminder infra with new "new assignment" trigger.
5. Notification in English (TBE Tier 1), deep link to submission form per Story 36 criterion 5.
6. Order: recurring weekly first, then additional templates by start date.
7. No recurring weekly template assigned: empty state *"No reflections currently assigned. Your Director will set this up shortly."*

## Story 64: Visibility to Director and TBE Admin

### Acceptance criteria

1. Form AudienceDisclosure per Story 40 criterion 10: *"This reflection will be visible to: Your Director, TBE Admin."*
2. NO sensitive-note variants for Madrich Tier 1. All same audience.
3. Visibility:
   1. Madrich (author) — full access, always original (English) content
   2. Director — TBE faculty role supervising Madrichim via Supervision (same primitive as LT-Kitchen)
   3. TBE Admin — full org-wide read per Story 59
4. Madrich does NOT see other Madrichim's reflections.
5. Director's aggregate dashboards (Story 53 scoped to Madrich cohort): responses anonymized in cohort views; individual response views display name.
6. Madrich history (Story 65) scoped to own.
7. Madrich does NOT see edit history of own. Platform retains for Admin oversight, doesn't surface to author.
8. Visibility model consistent with Kitchen Staff pattern.

### Decisions

- MA4: No parent visibility Tier 1 (Tier 2 per proposal).
- MA5: Co-Director model via LT co-supervisor pattern.

## Story 65: View reflection history

### Acceptance criteria

1. **My reflections** entry opens history view.
2. Reverse-chronological. Each entry: reflection period (e.g., "Week of Nov 4-10"), submission date and time, preview line (first sentence of "1 question or concern" field or placeholder if absent), status.
3. Prior submissions read-only. No Edit affordance. Past-week edits not permitted.
4. Weeks with no submission appear as gaps with "no reflection submitted" indicator. Honesty over comfort.
5. Scroll through entire program history. Prior years (returning Madrich) via "Prior years" link or program switcher.
6. History is Madrich's record only. Does NOT show Director annotations, edit history, supervisor metadata.
7. NO external sharing/CSV export Tier 1. End-of-year growth portfolio is Tier 2 surface.
