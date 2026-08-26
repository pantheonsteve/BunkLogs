/**
 * Per-organization display vocabulary. Mirrors `backend/bunk_logs/core/terminology.py`
 * — keep `DEFAULT_TERMS` in sync with the Python module.
 *
 * Canonical keys (`camper`, `director`, `cohort`) stay in routes, payloads, and
 * `data-testid`s; only the rendered noun varies per tenant. Anything a tenant
 * leaves unset falls back to the camp wording, so orgs without the setting
 * render exactly the copy they rendered before this module existed.
 *
 * Display only — never branch on a resolved term.
 */

export const DEFAULT_TERMS = Object.freeze({
  camper: { one: 'camper', other: 'campers' },
  student: { one: 'student', other: 'students' },
  director: { one: 'Director', other: 'Directors' },
  cohort: { one: 'cohort', other: 'cohorts' },
  // Group nouns. The canonical key stays the camp word even where a tenant
  // renames it, the same way `camper` does — `group_type` still stores `bunk`
  // when a school renders it as "class".
  bunk: { one: 'bunk', other: 'bunks' },
  unit: { one: 'unit', other: 'units' },
  team: { one: 'team', other: 'teams' },
  caseload: { one: 'caseload', other: 'caseloads' },
  // Role nouns, for screens that name a role in prose. These do NOT rename
  // `Membership.role` slugs, which route templates and derive capabilities.
  counselor: { one: 'counselor', other: 'counselors' },
  unit_head: { one: 'unit head', other: 'unit heads' },
  camper_care: { one: 'Camper Care', other: 'Camper Care' },
  leadership: { one: 'Leadership', other: 'Leadership' },
  staff: { one: 'staff', other: 'staff' },
});

/** Merge an API `terminology` payload over the defaults, per key and per form. */
export function normalizeTerminology(raw) {
  const overrides = raw && typeof raw === 'object' ? raw : {};
  const merged = {};
  Object.entries(DEFAULT_TERMS).forEach(([key, fallback]) => {
    const override = overrides[key];
    const shape = typeof override === 'string' ? { one: override } : override;
    if (!shape || typeof shape !== 'object') {
      merged[key] = { ...fallback };
      return;
    }
    const one = String(shape.one || '').trim();
    const other = String(shape.other || '').trim();
    // `other` inherits a *supplied* `one` (collectives like "Ed Team" that
    // don't pluralize), but never a defaulted one -- otherwise an org that
    // sets only `other` would silently lose the default plural.
    merged[key] = {
      one: one || fallback.one,
      other: other || one || fallback.other,
    };
  });
  return merged;
}

/** Render one canonical key; unknown keys return themselves. */
export function resolveTerm(terms, key, { plural = false, capitalize = false } = {}) {
  const forms = (terms && terms[key]) || DEFAULT_TERMS[key];
  if (!forms) return key;
  const value = plural ? forms.other : forms.one;
  if (capitalize && value) return value.charAt(0).toUpperCase() + value.slice(1);
  return value;
}
