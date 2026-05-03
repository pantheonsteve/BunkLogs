Allow admin to tag Memberships with demographic and grouping tags (International/Domestic/Israeli, specialist sub-types like waterfront/arts/sports).

Tasks:
1. In Django admin: add a tag editing widget for Membership.tags (JSON list field).
2. In the admin user-facing app: add a Membership management view where admins can:
   - View all memberships in current program
   - Filter by role, tags
   - Edit tags on individual memberships (text input that adds to tags list)
   - Bulk tag operations (add tag X to selected memberships)

3. API endpoint: PATCH /api/v1/memberships/{id}/ to update tags.

4. Tests:
   - Tag CRUD via API
   - Bulk tagging
   - Tag-based filtering returns correct memberships

Acceptance criteria:
- Admin can manage tags via UI
- Tag changes persist
- Tests pass
- Commit with message: "Add Membership tagging UI for admin"