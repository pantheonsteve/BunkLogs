# Prompt 3.24 — "Filed privately" chip on reflection surfaces

**Wave:** 3 (Crane Lake Summer 2026 Build) — UX polish for the privacy toggle
**Estimated time:** 4-5 hours
**Prerequisite:** Prompts 3.22 (`Reflection.team_visibility`) and 3.23 (`ReflectionTemplate.supports_privacy`) merged.

**Use the context prompt at the top of `0_0_context_prompt.md` before this session.**

---

```
Step 3.22 added per-reflection privacy and 3.23 added the template-level
gate. The data is there but a supervisor scanning a dashboard has no
visible way to tell that a given entry was filed privately. This prompt
adds a "Filed privately" chip (and a lock icon where space is tight) on
every surface where individual reflections are listed, so the supervisor
can a) recognise the entry needs to be treated as sensitive and b) know
why a co-author on their team can't see it.

CONTEXT:
- ``Reflection.team_visibility`` is already authoritative; nothing about
  visibility changes in this prompt. The only thing changing is that the
  flag becomes visible on read.
- The dashboard endpoints return purpose-built payloads (not
  ``ReflectionSerializer``), so each one needs ``team_visibility`` added
  explicitly. The list endpoint ``/api/v1/reflections/`` already exposes
  it via ``ReflectionSerializer`` (added in 3.22).
- Author-facing surfaces also get the chip so an author who flipped the
  toggle can confirm what they did. ``my-summary`` history entries and
  the post-submission ``ReflectionSummaryPage`` are the two surfaces.

Tasks:

1. Backend: expose ``team_visibility`` on every dashboard payload that
   surfaces an individual reflection. Each is a one-key addition; the
   underlying queries already select the column.

   - ``backend/bunk_logs/api/dashboards/trends.py`` -- in the
     ``per_cell`` dict and again in the ``cells`` output per day; the
     chip is rendered on the cell.
   - ``backend/bunk_logs/api/dashboards/concerns.py`` -- in the ``items``
     list (the Concerns Inbox).
   - ``backend/bunk_logs/api/dashboards/template.py`` -- in ``_agg_text``'s
     ``items`` list (each text response item).
   - ``backend/bunk_logs/api/dashboards/subject.py`` -- in
     ``recent_texts``, in each ``rating_series`` point, in each
     ``tpl_entry["reflections"]`` row, and in ``patterns`` items that
     carry a ``reflection_id`` (the ``low_rating`` kind). Downward-trend
     patterns aggregate over many reflections and intentionally don't
     carry one.
   - ``backend/bunk_logs/api/reflections.py`` -- in the ``history``
     entries returned by the ``my_summary`` action.

   Each addition is ``"team_visibility": r.team_visibility`` (or the
   underlying queryset row). Keep the keys named consistently across
   surfaces so the React side can lift a single helper.

2. Backend smoke tests. For each surface, one quick assertion that the
   field appears verbatim:

   - ``backend/bunk_logs/api/tests/test_reflection_api.py`` -- extend the
     ``my_summary`` coverage with ``test_my_summary_history_exposes_team_visibility``
     (post a private + a team reflection, assert the values come back).
   - ``backend/bunk_logs/api/tests/test_dashboard_api.py`` (or whichever
     test file exists for dashboards) -- add or extend tests for each
     dashboard surface listed above with one assertion per payload that
     ``team_visibility`` is present and equals the expected value.

3. Frontend: shared chip component.

   Create ``frontend/src/components/reflection/PrivacyChip.jsx``::

       export default function PrivacyChip({ teamVisibility, size = 'sm' }) {
         if (teamVisibility !== 'supervisors_only') return null;
         // Returns a small pill with a lock glyph + "Filed privately"
         // and a long-form tooltip explaining the contract.
       }

   - ``size="sm"`` is the default (pill chip). ``size="icon"`` renders
     just the lock for very tight layouts (the TrendCell uses ``"icon"``).
   - The tooltip text: "Filed privately. Only supervisors, admins, and
     (when subject_visible is enabled) the subject can read this entry."
   - Add ``frontend/src/components/reflection/__tests__/PrivacyChip.test.jsx``
     with three cases: returns null on ``team`` / undefined, renders pill
     on ``supervisors_only``, renders icon-only on ``size="icon"`` (use
     ``getByLabelText`` to assert the accessible name).

4. Frontend: wire the chip into each surface.

   - ``frontend/src/dashboards/trends/TrendCell.jsx`` -- when the cell
     has ``cell.team_visibility === 'supervisors_only'``, render a small
     lock glyph (``size="icon"``) absolutely positioned in the
     top-right of the cell, AND append "filed privately" to the
     existing ``tooltip`` string and ``aria-label``. The link still
     works -- the chip is a visual marker, not a link target.
   - ``frontend/src/dashboards/widgets/TextResponseListWidget.jsx`` --
     render the chip (pill) in the header line of each item, beside the
     ``period_end``.
   - ``frontend/src/dashboards/concerns/ConcernsInbox.jsx`` -- render
     the chip in the badge row beside the existing ``KindBadge``.
   - ``frontend/src/dashboards/subject/SubjectDetail.jsx`` -- the
     subject-detail page surfaces reflections in several blocks
     (patterns, recent_texts, rating_series, per-template reflections).
     Render the chip in each block where a per-reflection row appears.
   - ``frontend/src/pages/MyReflectionsPage.jsx`` -- in the history
     ``<ul>``, render the chip next to the ``StatusBadge`` when an
     entry is submitted and private.
   - ``frontend/src/pages/ReflectionSummaryPage.jsx`` -- if
     ``location.state.teamVisibility === 'supervisors_only'``, render
     the chip below the title.
   - ``frontend/src/pages/ReflectionFormPage.jsx`` -- the page already
     navigates to the summary with a state object on submit. Add
     ``teamVisibility: meta?.supports_privacy ? teamVisibility : 'team'``
     to that state so the summary page can show the chip.

5. Frontend tests:

   - Add a TrendCell test asserting that when the cell has
     ``team_visibility: 'supervisors_only'``, the lock element renders
     and the tooltip / aria-label include the phrase ``filed privately``
     case-insensitively.
   - Extend the existing ``ReflectionFormPage`` "successful submit"
     vitest to assert the navigation state argument includes
     ``teamVisibility``.
   - Extend ``MyReflectionsPage`` (a new file under
     ``frontend/src/pages/__tests__/`` if one doesn't exist) with a test
     that the chip appears for a private history entry and not for a
     team one. Mock the ``/my-summary/`` endpoint.

6. Documentation:

   - Add a short bullet to ``docs/membership-role-vs-capability.md`` in
     the "Per-reflection visibility" section noting that the chip is
     rendered on the listed surfaces; cite the shared
     ``PrivacyChip`` component as the single source of truth so future
     surfaces don't fork the styling.

Acceptance criteria:
- Every dashboard endpoint that returns ``reflection_id`` for an
  individual reflection now also returns ``team_visibility``.
- The chip appears on:
  - TrendCell (icon-only overlay)
  - TextResponseListWidget items
  - ConcernsInbox items
  - SubjectDetail (patterns, recent texts, rating series links, per-template reflection rows)
  - MyReflectionsPage history entries
  - ReflectionSummaryPage post-submission view
- The chip is ABSENT (returns null) for ``team_visibility === 'team'``
  and for missing values.
- ``make test-backend`` and ``make test-frontend`` both green.

Out of scope:
- Letting a viewer FLIP the flag from any of these list/detail surfaces
  -- the toggle lives on the form, not the list. A separate "demote /
  promote visibility from the detail page" prompt can come later if the
  product asks for it.
- A "supervisors only" filter chip on the reflection list page itself
  (would let supervisors filter the queue to just private entries).
  Queue this as a follow-up if anyone asks; it's an additive feature.

Commit structure (single PR, ordered commits):
  1. feat(3_24_filed_privately_chip): expose team_visibility on dashboard payloads
  2. test(3_24_filed_privately_chip): pin team_visibility presence on each surface
  3. feat(3_24_filed_privately_chip): add shared PrivacyChip component + tests
  4. feat(3_24_filed_privately_chip): render PrivacyChip on TrendCell + text/concerns/subject widgets
  5. feat(3_24_filed_privately_chip): render PrivacyChip on author-facing surfaces (my-reflections + summary + form-to-summary state)
  6. docs(3_24_filed_privately_chip): document chip surfaces + reuse contract
```
