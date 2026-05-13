Extend `core` with the Program model.

Tasks:
1. Define Program in core/models.py:

class Program(models.Model):
    PROGRAM_TYPES = [
        ('summer_camp', 'Summer Camp'),
        ('religious_school', 'Religious School'),
    ]
    
    organization = ForeignKey(Organization, on_delete=CASCADE, related_name='programs')
    name = CharField(max_length=255)
    slug = SlugField(max_length=100)
    program_type = CharField(max_length=32, choices=PROGRAM_TYPES)
    start_date = DateField()
    end_date = DateField()
    is_active = BooleanField(default=True)
    settings = JSONField(default=dict, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [('organization', 'slug')]
        ordering = ['-start_date']

2. Register in admin: list_display, list_filter on program_type and is_active, search on name.
3. Migration.
4. Tests:
   - Program creation
   - Cannot duplicate slug within an org
   - Same slug allowed across different orgs
   - Date validation (end_date >= start_date)

Acceptance criteria:
- Model migrates cleanly
- Admin works
- Tests pass
- Commit with message: "Add Program model"