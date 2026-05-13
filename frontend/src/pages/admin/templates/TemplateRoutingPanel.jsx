import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import {
  CADENCE_OPTIONS,
  GROUP_TYPE_OPTIONS,
  ROLE_OPTIONS,
  SUBJECT_MODE_OPTIONS,
  assignmentScopeFor,
  subjectModeNeedsGroups,
} from './templateRouting';

function selectClass() {
  return 'w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2.5 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500';
}

function ChipGroup({ legend, options, value, onChange, ariaLabel }) {
  const selected = new Set(value || []);
  function toggle(opt) {
    const next = new Set(selected);
    if (next.has(opt)) {
      next.delete(opt);
    } else {
      next.add(opt);
    }
    onChange(Array.from(next));
  }
  return (
    <fieldset aria-label={ariaLabel || legend}>
      <legend className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
        {legend}
      </legend>
      <div className="flex flex-wrap gap-1.5">
        {options.map((opt) => {
          const isOn = selected.has(opt.value);
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => toggle(opt.value)}
              aria-pressed={isOn}
              className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                isOn
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:border-blue-400'
              }`}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

/**
 * Settings card that exposes the ReflectionTemplate routing fields
 * (cadence, subject_mode, group types, role filters, subject_visible).
 *
 * `assignment_scope` is intentionally not a control here — it's derived from
 * `subject_mode` by `assignmentScopeFor` on save (see `templateRouting.js`).
 */
export default function TemplateRoutingPanel({ value, onChange, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);

  const subjectMode = value.subject_mode || 'self';
  const showGroups = subjectModeNeedsGroups(subjectMode);

  function patch(partial) {
    onChange({ ...value, ...partial });
  }

  function setSubjectMode(next) {
    const updates = { subject_mode: next };
    if (!subjectModeNeedsGroups(next)) {
      // Clear group-mode-only fields when collapsing back to 'self' so we
      // don't leave stale data that would fail coherence validation.
      updates.assignment_group_types = [];
      updates.subject_role_filter = [];
      updates.subject_visible = false;
      // supports_privacy is only meaningful when peer co-authors exist; a
      // self-mode template has nobody to hide from. Clear it so we don't
      // leave a meaningless True flag on collapse.
      updates.supports_privacy = false;
    }
    patch(updates);
  }

  return (
    <section
      aria-labelledby="template-settings-heading"
      className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <h3
            id="template-settings-heading"
            className="text-sm font-semibold text-gray-900 dark:text-white"
          >
            Settings
          </h3>
        </div>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {SUBJECT_MODE_OPTIONS.find((o) => o.value === subjectMode)?.label || subjectMode}
          {' · '}
          {CADENCE_OPTIONS.find((o) => o.value === value.cadence)?.label || value.cadence || '—'}
        </span>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-1 space-y-4 border-t border-gray-100 dark:border-gray-800">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="tpl-cadence"
                className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5"
              >
                Cadence
              </label>
              <select
                id="tpl-cadence"
                className={selectClass()}
                value={value.cadence || 'weekly'}
                onChange={(e) => patch({ cadence: e.target.value })}
              >
                {CADENCE_OPTIONS.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="tpl-subject-mode"
                className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5"
              >
                Who is each submission about?
              </label>
              <select
                id="tpl-subject-mode"
                className={selectClass()}
                value={subjectMode}
                onChange={(e) => setSubjectMode(e.target.value)}
              >
                {SUBJECT_MODE_OPTIONS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {SUBJECT_MODE_OPTIONS.find((m) => m.value === subjectMode)?.description}
              </p>
              <p className="mt-1 text-[11px] text-gray-400 dark:text-gray-500">
                Assignment scope: <code>{assignmentScopeFor(subjectMode)}</code>
                <span className="opacity-70"> (auto-set)</span>
              </p>
            </div>
          </div>

          {showGroups && (
            <ChipGroup
              legend="Which group types does this template apply to?"
              ariaLabel="Assignment group types"
              options={GROUP_TYPE_OPTIONS}
              value={value.assignment_group_types}
              onChange={(next) => patch({ assignment_group_types: next })}
            />
          )}

          <ChipGroup
            legend="Who can fill out this form? (author roles)"
            ariaLabel="Author role filter"
            options={ROLE_OPTIONS}
            value={value.author_role_filter}
            onChange={(next) => patch({ author_role_filter: next })}
          />
          <p className="-mt-3 text-[11px] text-gray-500 dark:text-gray-400">
            Empty = any role with a membership in the program can author.
          </p>

          {showGroups && (
            <>
              <ChipGroup
                legend="Who can be a subject? (subject roles)"
                ariaLabel="Subject role filter"
                options={ROLE_OPTIONS}
                value={value.subject_role_filter}
                onChange={(next) => patch({ subject_role_filter: next })}
              />
              <p className="-mt-3 text-[11px] text-gray-500 dark:text-gray-400">
                Empty = any group member with role <code>subject</code> qualifies.
              </p>

              <label className="flex items-center gap-2 text-sm text-gray-800 dark:text-gray-200 cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 dark:border-gray-600"
                  checked={Boolean(value.subject_visible)}
                  onChange={(e) => patch({ subject_visible: e.target.checked })}
                  aria-label="Subject can see reflections about themselves"
                />
                <span>Subject can see reflections about themselves</span>
              </label>

              <label className="flex items-start gap-2 text-sm text-gray-800 dark:text-gray-200 cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 dark:border-gray-600 mt-0.5"
                  checked={Boolean(value.supports_privacy)}
                  onChange={(e) => patch({ supports_privacy: e.target.checked })}
                  aria-label="Allow 'supervisors only' privacy on individual entries"
                />
                <span>
                  Allow &lsquo;supervisors only&rsquo; privacy on individual entries
                  <span className="block text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">
                    Authors can mark a single entry as hidden from peer authors.
                    Supervisors, admins, and (when subject_visible is on) subjects still see it.
                  </span>
                </span>
              </label>
            </>
          )}
        </div>
      )}
    </section>
  );
}
