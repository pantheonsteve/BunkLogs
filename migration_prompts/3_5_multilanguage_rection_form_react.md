Build the React component for submitting reflections. Must render dynamically from any template schema, support language switching, and work mobile-first.

Tasks:
1. Create route /reflect (or appropriate path matching existing routing).
2. Component flow:
   - On load: GET /api/v1/reflections/template-for-me/?language={user_lang}
   - Render form dynamically based on template.schema
   - Language switcher in UI (English/Spanish for Crane Lake support staff)
   - On language switch: re-fetch template with new language

3. Render each field type:
   - text → text input
   - textarea → textarea with char count
   - text_list → repeated text inputs (for "list 3 things")
   - rating_group → mobile-friendly buttons per category (1-4 selector, NOT a slider)
   - multiple_choice → checkbox group
   - single_choice → radio group

4. Mobile-first styling using existing Tailwind classes.

5. Save-and-resume in localStorage (key includes template id + period).

6. On submit: POST /api/v1/reflections/ with answers + language, handle errors, show success.

7. Validation matches schema requirements before allowing submit.

8. After submit: redirect to summary view.

9. Tests:
   - Renders all field types
   - Language switching re-fetches template
   - Form validation prevents invalid submit
   - Save-and-resume works
   - Successful submit calls API correctly

Acceptance criteria:
- Form works end-to-end mobile and desktop
- Both English and Spanish render correctly
- Frontend tests pass
- npm run build succeeds
- Commit with message: "Add multi-language dynamic reflection form"