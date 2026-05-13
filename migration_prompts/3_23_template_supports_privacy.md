# Prompt 3.23 — ReflectionTemplate.supports_privacy gate

**Wave:** 3 (Crane Lake Summer 2026 Build) — Template-level privacy gate
**Estimated time:** 3-4 hours
**Prerequisite:** Prompt 3.22 complete (`Reflection.team_visibility` field, visibility-module split, and the privacy toggle on `ReflectionFormPage` are in place).

**Use the context prompt at the top of `0_0_context_prompt.md` before this session.**

---

```
Add a template-level boolean that controls whether the per-reflection
privacy toggle (3.22) is offered on a given form. The motivating problem:
a self-reflection template ("rate your own week") with a "Supervisors only"
button is meaningless -- the author IS the subject, peers don't see the
entry through any path that team_visibility could close. Worse, a counselor
clicking the wrong button could lock their own self-reflection out of the
peer-collaboration feed used by the team-dashboard. The fix is a one-bit
gate on ``ReflectionTemplate`` that hides the UI and enforces the rule
server-side.

CONTEXT:
- 3.22 made ``Reflection.team_visibility`` a per-row column (``team`` /
  ``supervisors_only``). The frontend toggle is unconditionally rendered on
  every form. There is no validation against the template -- any POST is
  accepted, regardless of whether peer visibility would even be in play
  for that template's subject_mode.
- ``ReflectionTemplate.subject_mode`` already enumerates the cases where
  the toggle is meaningful: ``single_subject``, ``multi_subject``, and
  ``group`` involve potential peer co-authors. ``self`` does not.
- Per docs/membership-role-vs-capability.md the contract is "supports_privacy
  is a UX gate; the backend should reject mismatched POSTs so a third-party
  client can't bypass the UI."

Tasks:

1. Add ``ReflectionTemplate.supports_privacy`` in ``backend/bunk_logs/core/models.py``::

       supports_privacy = models.BooleanField(
           default=False,
           help_text=(
               "Whether this template offers the per-reflection 'supervisors "
               "only' privacy toggle. Off for self-reflection templates by "
               "default; on for templates where peer authors of the same "
               "AssignmentGroup would otherwise see the entry."
           ),
       )

   Two migrations to ship the change cleanly per the BunkLogs migration
   rules:

   - ``0020_reflectiontemplate_supports_privacy.py`` -- schema-only AddField
     with ``default=False``. New rows materialise as opt-out.
   - ``0021_backfill_template_supports_privacy.py`` -- data migration that
     sets ``supports_privacy=True`` for every template whose
     ``subject_mode in ("single_subject", "multi_subject", "group")``. Self
     templates stay at ``False``. ``RunPython`` with
     ``reverse_code=migrations.RunPython.noop``; idempotent (an
     ``.update(supports_privacy=True)`` only flips rows that need it).

2. Expose the field on both template serializers in ``backend/bunk_logs/api/``:

   - ``templates.py``: add ``"supports_privacy"`` to
     ``ReflectionTemplateSerializer.Meta.fields`` (admin CRUD surface --
     this is where the editor reads/writes it).
   - ``reflections.py``: add ``"supports_privacy"`` to
     ``ReflectionTemplateSummarySerializer.Meta.fields`` so it ships back
     to the form on the ``/api/v1/reflections/template-for-me/`` response.

3. Server-side enforcement in ``ReflectionSerializer.validate`` (the
   reflection POST surface, ``backend/bunk_logs/api/reflections.py``):

       tv = attrs.get("team_visibility", getattr(self.instance, "team_visibility", None))
       template = attrs.get("template", getattr(self.instance, "template", None))
       if (
           tv == Reflection.TeamVisibility.SUPERVISORS_ONLY
           and template is not None
           and not template.supports_privacy
       ):
           raise serializers.ValidationError({
               "team_visibility": (
                   "This template does not support the 'supervisors only' "
                   "privacy flag."
               ),
           })

   Place the check after the existing schema-and-language validation, just
   before the ``return attrs`` line. The mutation path (``update()``) goes
   through ``validate`` too, so a PATCH that flips a reflection to private
   against a non-supporting template gets the same 400.

4. Backend tests in ``backend/bunk_logs/api/tests/test_reflection_api.py``:

   - ``test_supports_privacy_blocks_self_template_supervisors_only`` --
     mark ``counselor_template`` with ``subject_mode="self"`` (the existing
     fixture already is) and ``supports_privacy=False`` (default). POST
     with ``team_visibility="supervisors_only"`` -> assert 400 and the
     error message mentions ``team_visibility``.
   - ``test_supports_privacy_allows_supervisors_only`` -- create a new
     template with ``subject_mode="single_subject"`` and
     ``supports_privacy=True``. POST with
     ``team_visibility="supervisors_only"`` -> assert 201 and the row
     persists the flag.
   - ``test_supports_privacy_defaults_to_false`` -- create a template via
     ``ReflectionTemplate.all_objects.create()`` and assert the column is
     ``False``. Then POST to ``/api/v1/templates/`` (the admin route) with
     ``supports_privacy=True`` in the payload and confirm the field
     round-trips on the GET.

   Also extend ``backend/bunk_logs/api/tests/test_template_api.py`` if it
   exercises the editor flow -- add ``supports_privacy`` to the round-trip
   asserts so future regressions get caught at the admin surface too.

5. Frontend: ``frontend/src/pages/ReflectionFormPage.jsx``:

   - In ``fetchTemplate``, store ``supports_privacy: Boolean(data.supports_privacy)``
     on the ``meta`` state.
   - Force ``teamVisibility`` back to ``'team'`` whenever
     ``meta.supports_privacy === false`` (a watcher effect on the meta
     change is fine -- the form is mounted once per template fetch).
   - Hide the entire ``<fieldset data-testid="reflect-visibility">`` block
     when ``meta?.supports_privacy === false``. The simplest implementation
     is to wrap the existing JSX in ``meta?.supports_privacy ? (...) :
     null``.
   - Drop ``team_visibility`` from the POST payload when the template
     doesn't support it -- the backend default is ``team``, so leaving it
     off keeps the wire format minimal and prevents a client that has
     stale toggle state from accidentally trying ``supervisors_only``.

6. Frontend: admin editor.

   - ``frontend/src/pages/admin/templates/TemplateRoutingPanel.jsx``: add a
     checkbox below the existing ``subject_visible`` toggle, but render it
     ONLY when ``subjectModeNeedsGroups(subject_mode)`` -- i.e. for any
     non-self template. Label: "Allow 'supervisors only' privacy on
     individual entries". Helper: "Authors can mark a single entry as
     hidden from peer authors. Supervisors, admins, and (when subject_visible
     is on) subjects still see it." Wire to
     ``patch({ supports_privacy: e.target.checked })``.
   - ``frontend/src/pages/admin/templates/TemplateEditorPage.jsx``:
     - Add ``supports_privacy: false`` to the initial ``routing`` state.
     - On load, hydrate from ``data.supports_privacy``.
     - On save, include ``supports_privacy: Boolean(routing.supports_privacy)``
       in the PATCH payload.
     - When ``subject_mode`` flips back to ``self``, the
       ``setSubjectMode`` helper in the routing panel already clears
       group-mode-only state; extend it to also clear
       ``supports_privacy`` so we don't leave a meaningless True on a
       self template.

7. Frontend tests:

   - ``ReflectionFormPage.test.jsx``: extend the template payload to
     include ``supports_privacy: true`` for the existing successful-submit
     tests (so the toggle still renders there), then add:
       - ``"hides the privacy toggle when the template does not support it"``
         -- ``getMock`` returns ``supports_privacy: false`` once, render,
         assert ``queryByTestId('reflect-visibility')`` is null.
       - ``"omits team_visibility from payload when the template does not support it"``
         -- as above, fill in fields, submit, assert ``postMock`` call
         body has no ``team_visibility`` key.
   - ``TemplateEditorPage.test.jsx``: add a round-trip test that the
     checkbox persists into the PATCH payload (call ``getByLabelText`` on
     the new label, click, save, assert the captured PATCH body has
     ``supports_privacy: true``).

8. Documentation:

   - ``docs/membership-role-vs-capability.md`` -- in the "Per-reflection
     visibility (team_visibility)" section, add a paragraph clarifying
     that ``ReflectionTemplate.supports_privacy`` is the UX gate; the
     row-level flag is still authoritative on read, but writes against a
     non-supporting template are rejected so third-party clients can't
     bypass the editor.

Acceptance criteria:
- A counselor opening their self-reflection sees NO privacy toggle.
- A counselor opening a single-subject (per-camper) reflection sees the
  toggle by default (data backfill makes existing single/multi/group
  templates support privacy).
- POST with ``team_visibility="supervisors_only"`` against an unsupported
  template returns 400 with a ``team_visibility`` error key.
- Admin editor exposes the checkbox below ``subject_visible`` only for
  non-self templates and round-trips on save.
- ``make test-backend`` and ``make test-frontend`` both green.

Out of scope:
- Forcing existing data into a new state. Backfill runs at migrate-time on
  deploy; no manual intervention needed.
- Per-author overrides ("this counselor can always go private, even on a
  self template") -- the field is template-wide.
- A "Filed privately" chip on the reflection list / detail (own prompt --
  doesn't block this one).

Commit structure (single PR, ordered commits):
  1. feat(3_23_template_supports_privacy): add ReflectionTemplate.supports_privacy field + serializer expose + migration
  2. feat(3_23_template_supports_privacy): backfill supports_privacy=True for non-self templates
  3. feat(3_23_template_supports_privacy): reject supervisors_only when template.supports_privacy is False
  4. test(3_23_template_supports_privacy): coverage for template gate + reflection POST guard
  5. feat(3_23_template_supports_privacy): hide privacy toggle in form when template does not support it
  6. feat(3_23_template_supports_privacy): admin editor checkbox + round-trip tests
  7. docs(3_23_template_supports_privacy): document template-level privacy gate
```
