"""Django admin forms for Organization subject-note authoring configuration."""

from __future__ import annotations

import json

from django import forms
from django.contrib.admin.widgets import AdminTextareaWidget
from django.core.exceptions import ValidationError

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.permissions.subject_note_authoring import DEFAULT_AUTHOR_BY_ROLE
from bunk_logs.core.permissions.subject_note_authoring import VALID_SCOPES
from bunk_logs.core.permissions.subject_note_authoring import author_by_role_for_org

AUTHOR_SCOPE_FIELD_PREFIX = "subject_note_author_scope_"

AUTHOR_SCOPE_CHOICES = [
    ("none", "None — cannot write subject notes"),
    ("supervised", "Supervised — subjects in groups they lead"),
    ("program", "Program — any subject in shared program(s)"),
    ("org", "Organization — any subject in this org"),
]

AUTHOR_SCOPE_HELP = (
    "Controls which subjects each role may write SubjectNotes about. "
    "Values shown are effective scopes (code defaults plus any saved org overrides). "
    "Only roles that differ from the product default are stored in organization settings."
)


def _settings_without_author_by_role(settings: dict | None) -> dict:
    """Return a copy of org settings omitting subject_notes.author_by_role."""
    other = dict(settings or {})
    subject_notes = other.pop("subject_notes", None)
    if not isinstance(subject_notes, dict):
        return other
    remainder = {k: v for k, v in subject_notes.items() if k != "author_by_role"}
    if remainder:
        other["subject_notes"] = remainder
    return other


def _organization_admin_form_init(self, *args, **kwargs):
    forms.ModelForm.__init__(self, *args, **kwargs)
    effective = (
        author_by_role_for_org(self.instance)
        if self.instance and self.instance.pk
        else dict(DEFAULT_AUTHOR_BY_ROLE)
    )
    for role_value, _role_label in Membership.ROLES:
        default_scope = DEFAULT_AUTHOR_BY_ROLE.get(role_value, "none")
        field_name = f"{AUTHOR_SCOPE_FIELD_PREFIX}{role_value}"
        self.fields[field_name].initial = effective.get(role_value, default_scope)
        self.fields[field_name].help_text = (
            f"Product default: {dict(AUTHOR_SCOPE_CHOICES).get(default_scope, default_scope)}"
        )

    other = _settings_without_author_by_role(
        self.instance.settings if self.instance and self.instance.pk else {},
    )
    self.fields["settings_json"].initial = json.dumps(other, indent=2, sort_keys=True)


def _organization_admin_form_clean_settings_json(self):
    raw = (self.cleaned_data.get("settings_json") or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON: {exc.msg}"
        raise ValidationError(msg) from exc
    if not isinstance(parsed, dict):
        msg = "Settings must be a JSON object."
        raise ValidationError(msg)
    return parsed


def _organization_admin_form_clean(self):
    cleaned = forms.ModelForm.clean(self)
    for role_value, _ in Membership.ROLES:
        field_name = f"{AUTHOR_SCOPE_FIELD_PREFIX}{role_value}"
        scope = cleaned.get(field_name)
        if scope and scope not in VALID_SCOPES:
            self.add_error(field_name, f"Invalid scope {scope!r}.")
    return cleaned


def _organization_admin_form_save(self, commit=True):
    org = forms.ModelForm.save(self, commit=False)
    overrides = {}
    for role_value, _ in Membership.ROLES:
        field_name = f"{AUTHOR_SCOPE_FIELD_PREFIX}{role_value}"
        scope = self.cleaned_data[field_name]
        default_scope = DEFAULT_AUTHOR_BY_ROLE.get(role_value, "none")
        if scope != default_scope:
            overrides[role_value] = scope

    existing = dict(org.settings or {}) if org.pk else {}
    settings = _settings_without_author_by_role(existing)
    settings.update(dict(self.cleaned_data.get("settings_json") or {}))

    subject_notes = dict(settings.get("subject_notes") or {})
    if overrides:
        subject_notes["author_by_role"] = overrides
    else:
        subject_notes.pop("author_by_role", None)
    if subject_notes:
        settings["subject_notes"] = subject_notes
    else:
        settings.pop("subject_notes", None)

    org.settings = settings
    if commit:
        org.save()
    return org


def _build_organization_admin_form() -> type[forms.ModelForm]:
    role_fields = {
        f"{AUTHOR_SCOPE_FIELD_PREFIX}{role_value}": forms.ChoiceField(
            choices=AUTHOR_SCOPE_CHOICES,
            label=role_label,
            required=True,
        )
        for role_value, role_label in Membership.ROLES
    }

    meta = type("Meta", (), {"model": Organization, "fields": ("name", "slug", "is_active")})

    return type(
        "OrganizationAdminForm",
        (forms.ModelForm,),
        {
            "Meta": meta,
            "settings_json": forms.CharField(
                required=False,
                label="Other organization settings (JSON)",
                help_text=(
                    "Timezone, rollover_hour, and other keys. "
                    "Subject note authoring is configured in the section above."
                ),
                widget=AdminTextareaWidget(attrs={"rows": 12, "cols": 80}),
            ),
            "__init__": _organization_admin_form_init,
            "clean_settings_json": _organization_admin_form_clean_settings_json,
            "clean": _organization_admin_form_clean,
            "save": _organization_admin_form_save,
            **role_fields,
        },
    )


OrganizationAdminForm = _build_organization_admin_form()


MEMBERSHIP_AUTHOR_OVERRIDE_CHOICES = [
    ("", "Use org role default"),
    ("true", "Yes — may author (program scope)"),
    ("false", "No — cannot author subject notes"),
]


class MembershipSubjectNoteAuthorField(forms.ChoiceField):
    """Tri-state override for Membership.metadata.can_author_subject_notes."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("choices", MEMBERSHIP_AUTHOR_OVERRIDE_CHOICES)
        kwargs.setdefault("required", False)
        kwargs.setdefault(
            "label",
            "Subject note authoring",
        )
        kwargs.setdefault(
            "help_text",
            "Override the org's role-based default for this person in this program.",
        )
        super().__init__(*args, **kwargs)


def membership_author_override_initial(metadata: dict | None) -> str:
    value = (metadata or {}).get("can_author_subject_notes")
    if value is True:
        return "true"
    if value is False:
        return "false"
    return ""


def apply_membership_author_override(metadata: dict | None, override: str) -> dict:
    """Merge tri-state override into membership metadata."""
    merged = dict(metadata or {})
    if override == "true":
        merged["can_author_subject_notes"] = True
    elif override == "false":
        merged["can_author_subject_notes"] = False
    else:
        merged.pop("can_author_subject_notes", None)
    return merged
