# Story 5: Submit my daily self-reflection

**As a Counselor, I want to submit my own daily reflection from the dashboard so it's part of my closeout routine.**

## Acceptance criteria

1. The dashboard's self-reflection section shows today's state: **not started**, **draft saved**, or **submitted**.
2. Tapping the section opens the Counselor self-reflection template, rendered in the user's preferred language (see `../00_cross_cutting/i18n.md`).
3. The form includes a **day-off** toggle. When toggled on:
   1. All other fields collapse or hide.
   2. The form can be submitted with no other content.
   3. The submission is marked complete for the day and the dashboard reflects it.
4. Form drafts auto-save locally (per-template-per-period key in localStorage) every 30 seconds and on field blur, so an interrupted session can be resumed.
5. Submission returns the user to the dashboard with the self-reflection section in the **submitted** state.
6. Field-level validation matches the template's schema requirements (required fields, min/max items, scale ranges). Submit is disabled until valid.

## Decisions

- C3: Drafts are private; not visible to supervisors until submitted.
