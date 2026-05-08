# Prompt 3.17 — Subject/author model and AssignmentGroup foundation

**Wave:** 3 (Crane Lake Summer 2026 Build) — Shared-roster observation pattern
**Estimated time:** 8-10 hours
**Prerequisite:** Prompts 3.13 through 3.16 complete (form builder shipped).

**Use the context prompt at the top of `bunklogs-migration-prompts.md` before this session.**

---

```
Add the data model foundation for shared-roster observation patterns. Templates can now declare WHO fills out the form (author) versus WHO the form is ABOUT (subject), and reflections can be scoped to an AssignmentGroup (a bunk, classroom, caseload, etc.) for completion tracking.

CONTEXT:
Today's Reflection model assumes a one-to-one mapping: a Person reflects on themselves. The bunk log use case breaks this: a counselor fills out a form ABOUT a camper, multiple counselors share responsibility for a roster of campers, and "complete" means every camper got a log from someone. This pattern generalizes — wellness caseloads, faculty-about-Madrich observations, leadership-about-unit, special diets per camper, etc.

This prompt establishes the data model. Subsequent prompts (3.18-3.20) populate, surface, and visualize it.

CRITICAL: Existing self-reflection templates (TBE Madrichim, kitchen staff, counselor self-reflections) MUST continue to work without changes. Migrations must default existing reflections to subject_mode='self' with author=subject.

Tasks:

1. Extend ReflectionTemplate schema in core/models.py with new fields:

class ReflectionTemplate(models.Model):
    # ... existing fields ...
    
    SUBJECT_MODES = [
        ('self', 'Self-reflection (author == subject)'),
        ('single_subject', 'About one other person'),
        ('multi_subject', 'About multiple people in one submission'),
        ('group', 'About a group/unit, no individual subject'),
    ]
    subject_mode = CharField(max_length=32, choices=SUBJECT_MODES, default='self')
    
    ASSIGNMENT_SCOPES = [
        ('none', 'No group context'),
        ('per_subject_in_group', 'One reflection per subject in the assignment group'),
        ('per_group', 'One reflection per group as a whole'),
    ]
    assignment_scope = CharField(max_length=32, choices=ASSIGNMENT_SCOPES, default='none')
    
    assignment_group_types = JSONField(default=list, blank=True,
        help_text="Which group types this template applies to, e.g. ['bunk']")
    
    author_role_filter = JSONField(default=list, blank=True,
        help_text="Membership roles eligible to author this template, e.g. ['counselor', 'unit_head']")
    
    subject_role_filter = JSONField(default=list, blank=True,
        help_text="Membership roles eligible to be subjects, e.g. ['camper']. Empty = any role.")
    
    required_per_subject_per_period = IntegerField(default=1,
        help_text="How many reflections per subject per cadence period for completion")
    
    subject_visible = BooleanField(default=False,
        help_text="Whether the subject can see reflections about themselves")

2. Update validate_template_schema (from 3.13) to enforce coherence:
   - subject_mode='self' requires assignment_scope='none'
   - subject_mode='group' requires assignment_scope='per_group'
   - subject_mode='single_subject' or 'multi_subject' requires assignment_scope='per_subject_in_group'
   - When assignment_scope != 'none', assignment_group_types must be non-empty
   - subject_visible can only be True when subject_mode != 'self' (self always visible)
   - author_role_filter and subject_role_filter must reference valid Membership.ROLES values

3. Create AssignmentGroup model in core/models.py:

class AssignmentGroup(models.Model):
    GROUP_TYPES = [
        ('bunk', 'Bunk'),
        ('classroom', 'Classroom'),
        ('caseload', 'Caseload'),
        ('unit', 'Unit'),
        ('division', 'Division'),
        ('cohort', 'Cohort'),
        ('specialty', 'Specialty/Activity Group'),
        ('custom', 'Custom Group'),
    ]
    
    organization = ForeignKey(Organization, on_delete=CASCADE, related_name='assignment_groups')
    program = ForeignKey(Program, on_delete=CASCADE, related_name='assignment_groups')
    name = CharField(max_length=255)
    slug = SlugField(max_length=100)
    group_type = CharField(max_length=32, choices=GROUP_TYPES)
    parent = ForeignKey('self', null=True, blank=True, on_delete=SET_NULL,
                        related_name='children',
                        help_text="For nesting: bunk -> unit -> division")
    metadata = JSONField(default=dict, blank=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [('program', 'slug')]
        ordering = ['group_type', 'name']
        indexes = [
            Index(fields=['program', 'group_type', 'is_active']),
            Index(fields=['parent']),
        ]
    
    def __str__(self):
        return f"{self.get_group_type_display()}: {self.name}"
    
    def get_descendants(self):
        """Recursive children for hierarchy queries (cache for perf if needed)."""
        descendants = list(self.children.filter(is_active=True))
        for child in list(descendants):
            descendants.extend(child.get_descendants())
        return descendants

Apply OrgScopedManager consistent with other multi-tenant models.

4. Create AssignmentGroupMembership model:

class AssignmentGroupMembership(models.Model):
    ROLES_IN_GROUP = [
        ('subject', 'Subject'),
        ('author', 'Author'),
    ]
    
    group = ForeignKey(AssignmentGroup, on_delete=CASCADE, related_name='memberships')
    person = ForeignKey(Person, on_delete=CASCADE, related_name='assignment_group_memberships')
    role_in_group = CharField(max_length=16, choices=ROLES_IN_GROUP)
    start_date = DateField(null=True, blank=True)
    end_date = DateField(null=True, blank=True)
    is_active = BooleanField(default=True)
    metadata = JSONField(default=dict, blank=True,
        help_text="Role-specific data, e.g. {'is_lead_counselor': true} or {'caseload_priority': 'high'}")
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [('group', 'person', 'role_in_group')]
        indexes = [
            Index(fields=['group', 'role_in_group', 'is_active']),
            Index(fields=['person', 'role_in_group', 'is_active']),
        ]

A Person can be in multiple groups (e.g. Bunk Maple + Wellness caseload + Soccer specialty). A Person can hold both subject and author roles in different groups (a unit head is author of "Junior unit" but subject of "Year-round leadership team").

5. Extend Reflection model. CRITICAL: this is a destructive rename. Migration must preserve existing data.

class Reflection(models.Model):
    # RENAME: person -> subject
    subject = ForeignKey(Person, null=True, blank=True, on_delete=CASCADE,
                         related_name='reflections_about',
                         help_text="Who this reflection is ABOUT. Null when subject_mode='group'.")
    
    # NEW
    subject_group = ForeignKey(AssignmentGroup, null=True, blank=True, on_delete=CASCADE,
                                related_name='reflections_as_subject',
                                help_text="Set when subject_mode='group'")
    
    author = ForeignKey(Person, null=True, blank=True, on_delete=SET_NULL,
                        related_name='reflections_authored',
                        help_text="Who FILLED OUT this reflection (Person; may equal subject for self-reflection)")
    
    assignment_group = ForeignKey(AssignmentGroup, null=True, blank=True, on_delete=SET_NULL,
                                   related_name='reflections',
                                   help_text="Which group context this was authored in (e.g. which bunk)")
    
    submission_id = UUIDField(default=uuid.uuid4, db_index=True,
                              help_text="Groups multi-subject submissions together")
    
    # KEEP submitted_by (User) for audit trail — different from author (Person)
    # ... rest of existing fields ...
    
    class Meta:
        ordering = ['-period_end']
        indexes = [
            Index(fields=['organization', 'program', 'period_end']),
            Index(fields=['subject', 'period_end']),
            Index(fields=['subject_group', 'period_end']),
            Index(fields=['assignment_group', 'period_end']),
            Index(fields=['author', 'period_end']),
            Index(fields=['template', 'is_complete']),
            Index(fields=['submission_id']),
        ]

6. Data migration for existing reflections:
   - For every existing Reflection: subject = person (the renamed field), author = person, assignment_group = null, subject_group = null
   - For every existing ReflectionTemplate: subject_mode = 'self', assignment_scope = 'none' (defaults handle this)
   - Verify: count of reflections before == count after, no nulls in subject for existing rows

   Use a two-step Django migration:
   a) Schema migration: add new fields, rename person to subject (Django supports this with RenameField)
   b) Data migration: populate author = subject for all existing rows
   
   Test the migration on a copy of staging data before running anywhere.

7. Update validate_template_schema to also validate, when called with a template instance: that schema field constraints align with subject_mode (e.g. you can't have a section_header that says "About yourself" when subject_mode='single_subject' — but this is content concern, not enforced; just ensure the structural validation still passes).

8. Add an admin UI for AssignmentGroup and AssignmentGroupMembership:
   - List view: group_type filter, program filter, search by name
   - Detail view: shows memberships with role_in_group breakdown
   - Bulk actions: deactivate group, transfer members to another group of same type

9. API surface (read-only for now; population comes in 3.18):
   - GET /api/v1/assignment-groups/ — list groups visible to current user, filtered by ?program=, ?group_type=, ?parent=, ?include_descendants=true|false
   - GET /api/v1/assignment-groups/{id}/ — detail with memberships
   - GET /api/v1/assignment-groups/{id}/subjects/ — list of Persons in subject role
   - GET /api/v1/assignment-groups/{id}/authors/ — list of Persons in author role
   
   Permissions: any authenticated user in the org can read; write endpoints come in 3.18.

10. Update existing Reflection API endpoints from 3.4:
    - List/detail responses now include subject, author, assignment_group, subject_group, submission_id fields
    - Existing self-reflection submissions continue to work (submitted Reflection has subject=author=current user's Person)
    - The 'template-for-me' endpoint still works for self-reflection templates; multi-subject template handling moves to 3.19's 'what do I owe today' endpoint
    - Add ?subject={person_id}, ?author={person_id}, ?assignment_group={group_id} filters

11. Tests (must cover):
    - Existing self-reflection templates and reflections continue to validate after migration
    - Data migration correctly populates author=subject for legacy reflections
    - Schema validator enforces subject_mode/assignment_scope coherence rules
    - AssignmentGroup creation, hierarchy (parent/children), get_descendants
    - AssignmentGroupMembership: a Person can be subject in one group and author in another
    - A Person cannot be subject and author in the SAME group (uniqueness allows different roles in same group, so verify intent — actually unique_together is (group, person, role_in_group), so same person CAN be both in same group; document this and add a regression test for the case where it's intentional, e.g. peer mentoring)
    - Cross-org isolation holds for AssignmentGroup (uses OrgScopedManager)
    - subject_visible defaults to False, can be set True only for non-self templates
    - Reflection API includes new fields in responses
    - Reflection filters by subject, author, assignment_group work
    - ?include_descendants=true on assignment-groups returns nested children correctly
    - submission_id is unique per submit-event but groups multi-subject reflections together

12. Update docs/data-model.md with a new section on assignment groups and the subject/author/submission_id distinction. Include diagrams (text-based ASCII or a Mermaid diagram in the markdown) showing:
    - The Bunk Maple example: 8 campers as subjects, 3 counselors as authors, 8 reflections per day each with subject + author + assignment_group=Bunk Maple
    - The TBE classroom example: 6 Madrichim as subjects (when faculty observes them), 1 faculty as author
    - Self-reflection: subject == author, no assignment_group

Acceptance criteria:
- Existing self-reflection flows work end-to-end without changes (TBE Madrichim test passes, kitchen staff test passes)
- AssignmentGroup and AssignmentGroupMembership migrate cleanly
- Reflection model rename completes without data loss (verified by count + spot checks)
- Validator enforces subject_mode/assignment_scope coherence
- Read API endpoints work with permission scoping
- Documentation updated with diagrams
- Full test suite passes including new tests
- ruff check passes
- Commit history is structured: 1) template schema extensions + validator, 2) AssignmentGroup + Membership models, 3) Reflection model rename + new fields + data migration, 4) admin + API + tests, 5) docs

Out of scope:
- Group population (Campminder import extension comes in 3.18)
- Roster-aware home screen (3.19)
- Coverage dashboards and heatmaps (3.20)
- Permission rework for author-group-supervisor visibility (folded into 3.20)
```
