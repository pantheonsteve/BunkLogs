Create a new Django app called `core` to house the new multi-tenant models. Start with Organization.

Tasks:
1. Create the app: `python manage.py startapp core`
2. Add to INSTALLED_APPS.
3. Define Organization:

class Organization(models.Model):
    name = CharField(max_length=255)
    slug = SlugField(max_length=100, unique=True)
    settings = JSONField(default=dict, blank=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

4. Register in admin: list_display showing name, slug, is_active, created_at.
5. Generate and apply migrations.
6. Tests:
   - Organization can be created
   - Slug uniqueness enforced
   - Settings JSON accepts arbitrary dict

Acceptance criteria:
- New app `core` exists with Organization model
- Migration applies cleanly
- Admin works
- Tests pass
- Commit with message: "Add core app with Organization model"