# Prompt 3.14 — Field key registry and reusable schemas

**Wave:** 3 (Crane Lake Summer 2026 Build) — Form Builder addition
**Estimated time:** 4-6 hours
**Prerequisite:** Prompt 3.13 complete.

**Use the context prompt at the top of `bunklogs-migration-prompts.md` before this session.**

---

```
Add a per-organization field key registry so admins can reuse canonical keys across templates. This makes future cross-template reporting possible and prevents key sprawl.

CONTEXT:
Without a registry, an admin building three templates might use `punctuality_rating`, `punctuality`, and `on_time_score` for the same concept, breaking comparability. The registry provides autocomplete with existing keys plus the ability to define a new canonical key with a description.

Tasks:

1. Add a new model `core/models.py::FieldKey`:

class FieldKey(models.Model):
    organization = ForeignKey(Organization, null=True, blank=True, on_delete=CASCADE,
                               related_name='field_keys',
                               help_text="Null = global key available to all orgs")
    key = CharField(max_length=64)
    display_name = CharField(max_length=255)
    description = TextField(blank=True)
    expected_field_type = CharField(max_length=32, blank=True,
                                     help_text="Optional hint for editor: text, rating_group, etc.")
    expected_dashboard_role = CharField(max_length=32, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [('organization', 'key')]
        ordering = ['key']

2. Migration. Apply OrgScopedManager (with all_objects fallback) consistent with other multi-tenant models.

3. Seed initial global keys via a data migration or management command `core/management/commands/seed_field_keys.py`:
   - punctuality, reliability, communication, problem_solving, interpersonal, initiative — all rating_group/category_ratings
   - wins, improvements — text_list
   - open_concern — textarea/open_concern
   - These mirror the TBE 5-category model and the 3-2-1 structure so they're useful out of the box

4. API endpoints at /api/v1/field-keys/:
   - GET /api/v1/field-keys/ — list keys visible to current org (own + global). Query: ?q= for prefix search (for autocomplete)
   - POST /api/v1/field-keys/ — create new key in current org (org admin or super admin)
   - PATCH /api/v1/field-keys/{id}/ — update display_name/description (super admin only for globals)
   - DELETE /api/v1/field-keys/{id}/ — soft restrict if any template references the key

5. Update the schema validator from prompt 3.13 to optionally cross-reference: when a field's key matches a registered FieldKey AND that FieldKey has expected_field_type set, log a warning (not an error) if the types disagree. Don't block — just surface in API response.

6. Add a "registered_keys" hint to the template detail response so the editor can highlight which fields use canonical keys.

7. Tests:
   - FieldKey CRUD with org isolation
   - Global keys visible across orgs
   - Prefix search returns expected matches
   - Org admins can create org-scoped keys
   - Org admins cannot create global keys
   - Type mismatch warning surfaces correctly
   - Delete blocked when key in use

Acceptance criteria:
- Model migrates cleanly
- Initial global keys seeded
- Autocomplete endpoint performs (prefix index acceptable)
- Tests pass, linter passes
- Commit message: "Add FieldKey registry for canonical reflection field keys"
- PR description explains the rationale and includes the seed list

Out of scope:
- Cross-template reports (those come later, once two+ templates share keys in production)
- Forced consistency (registry is a guide, not a requirement, in v1)
```
