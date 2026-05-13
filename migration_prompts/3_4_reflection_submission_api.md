Build DRF API endpoints under /api/v1/ for submitting reflections. Must handle role-based template selection and language preference.

Tasks:
1. Create serializers for Reflection that:
   - Validate `answers` against the linked template's schema for the specified language
   - Return reflection data with template metadata

2. Create ReflectionViewSet at /api/v1/reflections/:
   - GET /reflections/ — list current user's reflections (auto-filtered by org)
   - GET /reflections/{id}/ — retrieve specific reflection
   - POST /reflections/ — create new reflection
   - PATCH /reflections/{id}/ — update if not is_complete

3. Add helper endpoint: GET /api/v1/reflections/template-for-me/
   - Returns the appropriate ReflectionTemplate for the current user based on their active Membership role
   - Accepts ?language=es to return template with Spanish content

4. Permissions:
   - Person can see/edit only their own reflections
   - Faculty/leadership_team can see reflections for their assigned units
   - Admin can see all reflections in their org
   - Wellness team has read-only access to wellness-related reflection types

5. Add filtering: by program, by period_start range, by template, by membership role

6. Tests:
   - Person can submit
   - Person can't see another person's reflections
   - Leadership team sees unit-level reflections
   - Cross-org access impossible
   - Schema validation rejects malformed answers
   - Language parameter works correctly
   - Wellness team permissions enforced

Acceptance criteria:
- Endpoints work as specified
- Role-based permissions enforced
- Language handling correct
- Tests pass
- Commit with message: "Add Reflection API with role and language support"