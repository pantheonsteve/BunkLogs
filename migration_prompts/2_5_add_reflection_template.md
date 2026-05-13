ReflectionTemplate defines the schema for a reflection. Different roles use different templates. Schema must support localized prompts (English/Spanish minimum) from day one.

Tasks:
1. Define ReflectionTemplate in core/models.py:

class ReflectionTemplate(models.Model):
    CADENCES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Biweekly'),  # for Leadership Team's 1-2x per week
        ('monthly', 'Monthly'),
        ('on_demand', 'On Demand'),
    ]
    
    organization = ForeignKey(Organization, null=True, blank=True, on_delete=CASCADE,
                               related_name='reflection_templates',
                               help_text="Null = global template available to all orgs")
    program_type = CharField(max_length=32, choices=Program.PROGRAM_TYPES, null=True, blank=True)
    role = CharField(max_length=32, null=True, blank=True,
                     help_text="Membership role this template targets. Null = applies to all roles in program type.")
    name = CharField(max_length=255)
    slug = SlugField(max_length=100)
    description = TextField(blank=True)
    cadence = CharField(max_length=32, choices=CADENCES)
    schema = JSONField(help_text="JSON schema with localized prompts; see docs/reflection-template-schema.md")
    languages = JSONField(default=list, blank=True, help_text="Supported language codes, e.g. ['en', 'es']")
    is_active = BooleanField(default=True)
    version = IntegerField(default=1)
    parent_template = ForeignKey('self', null=True, blank=True, on_delete=SET_NULL,
                                  related_name='versions',
                                  help_text="Previous version of this template; for version history")
    created_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [('organization', 'slug', 'version')]

2. Schema field structure (document in `docs/reflection-template-schema.md`):

{
  "fields": [
    {
      "key": "wins",
      "type": "text_list",
      "min_items": 3,
      "max_items": 3,
      "required": true,
      "prompts": {
        "en": "List 3 things you did well this week.",
        "es": "Lista 3 cosas que hiciste bien esta semana."
      }
    },
    {
      "key": "ratings",
      "type": "rating_group",
      "scale": [1, 4],
      "scale_labels": {
        "en": ["Unsatisfactory", "Needs Improvement", "Meets Expectations", "Exceeds Expectations"],
        "es": ["Insatisfactorio", "Necesita Mejorar", "Cumple Expectativas", "Excede Expectativas"]
      },
      "categories": [
        {"key": "punctuality", "labels": {"en": "Reliability & Punctuality", "es": "Confiabilidad y Puntualidad"}}
      ]
    }
  ]
}

Supported field types: text, textarea, text_list, rating_group, multiple_choice, single_choice. All prompts/labels are dicts keyed by language code.

3. Admin registration with JSON-friendly editor.
4. Migration.
5. Tests:
   - Template creation with each field type
   - Validation that schema is well-formed (basic structural check: fields array exists, each field has key+type+prompts)
   - Validation that prompts dict has at least one language
   - parent_template relationship works for version chains

Acceptance criteria:
- Model migrates cleanly
- Schema documentation written with examples for both English-only and bilingual templates
- Tests pass
- Commit with message: "Add ReflectionTemplate with role and localization support"