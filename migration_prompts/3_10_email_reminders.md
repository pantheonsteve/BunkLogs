Build automated reminders for staff who haven't submitted reflections. Multi-language email content (English/Spanish for support staff).

Tasks:
1. Create Celery task: `core/tasks.py` → `send_reflection_reminders(program_id, role=None)`.
2. Task logic:
   - For given program (and optionally role): find Memberships missing current period reflection
   - For each: send email reminder in their preferred language
3. Email templates: templates/emails/reflection_reminder_{lang}.html and .txt for en, es.
4. Schedule via Celery Beat. Per-role schedules (daily for counselors, weekly for support staff, biweekly for LT).
5. Per-program config in Program.settings: {"reminder_schedules": {"counselor": "daily_18:00", "kitchen_staff": "weekly_friday_15:00"}}.
6. Tests:
   - Task identifies correct people to remind
   - Doesn't remind those who submitted
   - Email is in correct language per Person preference
   - Schedule honors per-role config

Acceptance criteria:
- Task works end-to-end (verified by captured emails in test)
- Multi-language emails render correctly
- Tests pass
- Commit with message: "Add multi-language reflection reminder emails"