Reflection is the actual submitted reflection. Generic — content validated against linked ReflectionTemplate's schema.

Tasks:
1. Define Reflection in core/models.py:

class Reflection(models.Model):
    organization = ForeignKey(Organization, on_delete=CASCADE, related_name='reflections')
    program = ForeignKey(Program, on_delete=CASCADE, related_name='reflections')
    person = ForeignKey(Person, on_delete=CASCADE, related_name='reflections')
    template = ForeignKey(ReflectionTemplate, on_delete=PROTECT, related_name='reflections')
    submitted_by = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL,
                               help_text="Who actually submitted this reflection")
    period_start = DateField(help_text="Start of period being reflected on")
    period_end = DateField(help_text="End of period being reflected on")
    answers = JSONField(help_text="Validated against template.schema")
    language = CharField(max_length=10, default='en', help_text="Language used to fill out this reflection")
    submitted_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    is_complete = BooleanField(default=True)
    
    class Meta:
        ordering = ['-period_end']
        indexes = [
            Index(fields=['organization', 'program', 'period_end']),
            Index(fields=['person', 'period_end']),
            Index(fields=['template', 'is_complete']),
        ]

2. Add validate_answers method that checks `answers` matches `template.schema` structure (basic validation).
3. Admin registration with filters by program, template, role-via-template, period_end.
4. Migration.
5. Tests:
   - Reflection creation with valid answers
   - Validation rejects answers missing required fields
   - period_end >= period_start
   - Querying by person, by program, by date range, by template role
   - Language field captured correctly

Acceptance criteria:
- Migrates cleanly
- Validation works
- Tests pass
- Commit with message: "Add Reflection model with completion and language tracking"