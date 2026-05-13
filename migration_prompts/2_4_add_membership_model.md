Membership represents a Person's participation in a Program with a specific role. The role taxonomy must cover both camp roles (counselor, kitchen, maintenance, housekeeping, wellness, specialist, GC, junior counselor, leadership team) and religious school roles (madrich, faculty).

Tasks:
1. Define Membership in core/models.py:

class Membership(models.Model):
    ROLES = [
        # Camp roles
        ('camper', 'Camper'),
        ('counselor', 'Counselor'),
        ('junior_counselor', 'Junior Counselor'),
        ('specialist', 'Specialist'),
        ('general_counselor', 'General Counselor'),
        ('unit_head', 'Unit Head'),
        ('leadership_team', 'Leadership Team'),
        # Support staff
        ('kitchen_staff', 'Kitchen Staff'),
        ('maintenance', 'Maintenance'),
        ('housekeeping', 'Housekeeping'),
        # Wellness team
        ('camper_care', 'Camper Care'),
        ('health_center', 'Health Center'),
        ('special_diets', 'Special Diets'),
        # Religious school roles
        ('madrich', 'Madrich'),
        ('faculty', 'Faculty'),
        # Cross-cutting
        ('admin', 'Admin'),
    ]
    
    program = ForeignKey(Program, on_delete=CASCADE, related_name='memberships')
    person = ForeignKey(Person, on_delete=CASCADE, related_name='memberships')
    role = CharField(max_length=32, choices=ROLES)
    grade_level = IntegerField(null=True, blank=True)  # for Madrichim 8-12
    
    # Demographic and grouping tags
    tags = JSONField(default=list, blank=True)  # e.g. ["international", "israeli"] or ["specialist:waterfront"]
    
    start_date = DateField(null=True, blank=True)
    end_date = DateField(null=True, blank=True)
    is_active = BooleanField(default=True)
    metadata = JSONField(default=dict, blank=True)  # role-specific extra data
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [('program', 'person', 'role')]
        ordering = ['-created_at']

Note: tags is a list field for flexible categorization (International/Domestic/Israeli, specialist sub-types, etc.). metadata is for structured role-specific data.

2. Admin registration.
3. Migration.
4. Tests:
   - Cannot duplicate (program, person, role)
   - Same person in multiple programs allowed
   - Same person with multiple roles in one program allowed (e.g., counselor + admin)
   - tags supports list of strings
   - All role choices are queryable

Acceptance criteria:
- Migrates cleanly
- Admin works
- Tests pass
- Commit with message: "Add Membership model with comprehensive role taxonomy"