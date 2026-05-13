Add Person model. Longitudinal identity for kids and staff being tracked. Separate from Django User. Kitchen Staff, Madrichim, Counselors, Campers are all Persons. They may or may not log in.

Tasks:
1. Define Person in core/models.py:

class Person(models.Model):
    organization = ForeignKey(Organization, on_delete=CASCADE, related_name='persons')
    first_name = CharField(max_length=100)
    last_name = CharField(max_length=100)
    preferred_name = CharField(max_length=100, blank=True)
    date_of_birth = DateField(null=True, blank=True)
    email = EmailField(blank=True)
    user = OneToOneField(User, null=True, blank=True, on_delete=SET_NULL, related_name='person_record')
    external_ids = JSONField(default=dict, blank=True)  # e.g. {"campminder_id": "12345"}
    notes = TextField(blank=True)
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['last_name', 'first_name']
    
    @property
    def full_name(self):
        return f"{self.preferred_name or self.first_name} {self.last_name}"

Note: external_ids stores cross-system identifiers like Campminder ID for Crane Lake.

2. Register in admin.
3. Migration.
4. Tests:
   - Person creation without User
   - Person creation linked to User
   - full_name property
   - external_ids stores arbitrary key/value pairs
   - Cannot create without organization

Do NOT modify Camper or User models. Person is a parallel concept bridged later.

Acceptance criteria:
- Person migrates cleanly
- Admin works
- Tests pass
- Commit with message: "Add Person model with external_ids for cross-system identity"