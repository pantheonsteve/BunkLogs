/**
 * AssignFormDialog — builder-scoped assignment creation dialog.
 *
 * Opens from the "Assign form" button on a published LT template. Differences
 * from the general-purpose AssignmentDialog (used in TemplateLibrary):
 *   - "Individuals" target type is rendered disabled ("Coming soon").
 *   - On 409 the form fields are frozen and the submit area is replaced by a
 *     conflict resolution panel; the user picks replace/run_both/cancel and
 *     clicks "Confirm" to re-POST.
 *   - On 400 with "scored camper form" in the body, an amber callout is shown
 *     below the target group picker instead of the generic error area.
 *   - Group picker filters by program and group type; checkboxes allow
 *     assigning to multiple groups at once (one POST per group).
 *
 * Calls onCreated(assignment) on success, then closes.
 *
 * FA-E, Step 7_20 frontend.
 */

import { useEffect, useMemo, useState } from 'react';
import { createAssignment, listAssignmentGroups } from '../../api/leadershipTeam';
import { useAuth } from '../../auth/AuthContext';

// ─── Constants ────────────────────────────────────────────────────────────────

const TARGET_TYPES = [
  { value: 'assignment_group', label: 'Assignment group', recommended: true },
  { value: 'role', label: 'Role' },
  { value: 'tag_group', label: 'Tag group' },
  { value: 'individuals', label: 'Individuals', disabled: true, hint: 'Coming soon' },
];

const ROLE_OPTIONS = [
  'counselor', 'junior_counselor', 'specialist', 'general_counselor',
  'unit_head', 'leadership_team', 'kitchen_staff', 'maintenance',
  'administrative_staff', 'housekeeping', 'camper_care', 'health_center', 'medical',
  'madrich', 'faculty',
];

const CADENCES = ['daily', 'weekly', 'biweekly', 'monthly', 'on_demand'];

const CONFLICT_CHOICES = [
  { value: 'replace', label: 'Replace — end the existing assignment and start this one' },
  { value: 'run_both', label: 'Run both — keep both active simultaneously' },
  { value: 'cancel', label: 'Cancel — discard and close the dialog' },
];

const GROUP_TYPE_ORDER = [
  'bunk', 'unit', 'division', 'cohort', 'classroom', 'caseload', 'team', 'specialty', 'custom',
];

const GROUP_TYPE_LABEL = {
  bunk: 'Bunks',
  unit: 'Units',
  division: 'Divisions',
  cohort: 'Cohorts',
  classroom: 'Classrooms',
  caseload: 'Caseloads',
  team: 'Teams',
  specialty: 'Specialty / Activity groups',
  custom: 'Custom groups',
};

const GROUP_TYPE_SHORT = {
  bunk: 'Bunk', unit: 'Unit', division: 'Division', cohort: 'Cohort',
  classroom: 'Classroom', caseload: 'Caseload', team: 'Team', specialty: 'Specialty', custom: 'Custom',
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

/**
 * Detect the scored-camper grid guard: the backend returns 400 with a message
 * containing "scored camper form" in either array or detail shape.
 */
function extractScoredCamperError(responseData) {
  if (!responseData) return null;
  const candidates = [
    typeof responseData === 'string' ? responseData : null,
    responseData.detail,
    Array.isArray(responseData) ? responseData.join(' ') : null,
    Array.isArray(responseData.non_field_errors) ? responseData.non_field_errors.join(' ') : null,
  ].filter(Boolean);
  const found = candidates.find((s) => s.toLowerCase().includes('scored camper form'));
  return found ?? null;
}

function extractErrorMessage(responseData) {
  if (!responseData) return 'Failed to create assignment.';
  if (typeof responseData === 'string') return responseData;
  if (responseData.detail) return responseData.detail;
  if (Array.isArray(responseData)) return responseData.join(' · ');
  if (responseData.errors) {
    return Array.isArray(responseData.errors)
      ? responseData.errors.join(' · ')
      : JSON.stringify(responseData.errors);
  }
  return JSON.stringify(responseData);
}

// ─── Group picker ─────────────────────────────────────────────────────────────

function GroupPicker({
  orgSlug,
  template,
  selectedIds,
  onToggleGroup,
  onSetSelectedIds,
  groupResults,
  scoredCamperError,
}) {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [search, setSearch] = useState('');
  const [programFilter, setProgramFilter] = useState('');
  const [groupTypeFilter, setGroupTypeFilter] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError('');
    listAssignmentGroups(orgSlug)
      .then((rows) => { if (!cancelled) setGroups(rows); })
      .catch(() => { if (!cancelled) setLoadError('Failed to load groups.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [orgSlug]);

  const programOptions = useMemo(() => {
    const byId = new Map();
    for (const g of groups) {
      if (g.program != null && !byId.has(g.program)) {
        byId.set(g.program, g.program_name ?? `Program #${g.program}`);
      }
    }
    return [...byId.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [groups]);

  const allowedGroupTypes = useMemo(() => {
    const fromTemplate = Array.isArray(template?.assignment_group_types)
      ? template.assignment_group_types.filter(Boolean)
      : [];
    return fromTemplate.length > 0 ? new Set(fromTemplate) : null;
  }, [template?.assignment_group_types]);

  const typeOptions = useMemo(() => {
    if (!programFilter) return [];
    const types = new Set(
      groups
        .filter((g) => String(g.program) === programFilter)
        .map((g) => g.group_type)
        .filter(Boolean),
    );
    const ordered = GROUP_TYPE_ORDER.filter((gt) => types.has(gt));
    for (const gt of types) {
      if (!ordered.includes(gt)) ordered.push(gt);
    }
    if (allowedGroupTypes) {
      return ordered.filter((gt) => allowedGroupTypes.has(gt));
    }
    return ordered;
  }, [groups, programFilter, allowedGroupTypes]);

  const visibleGroups = useMemo(() => {
    if (!programFilter || !groupTypeFilter) return [];
    let list = groups.filter(
      (g) => String(g.program) === programFilter && g.group_type === groupTypeFilter,
    );
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter((g) => (g.name || '').toLowerCase().includes(q));
    }
    return list.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  }, [groups, programFilter, groupTypeFilter, search]);

  const filtersReady = Boolean(programFilter && groupTypeFilter);
  const allVisibleSelected = visibleGroups.length > 0
    && visibleGroups.every((g) => selectedIds.has(g.id));
  const someVisibleSelected = visibleGroups.some((g) => selectedIds.has(g.id));

  const toggleAllVisible = () => {
    const ids = visibleGroups.map((g) => g.id);
    onSetSelectedIds((prev) => {
      const next = new Set(prev);
      const allChecked = ids.every((id) => next.has(id));
      for (const id of ids) {
        if (allChecked) next.delete(id);
        else next.add(id);
      }
      return next;
    });
  };

  useEffect(() => {
    if (programOptions.length === 1 && !programFilter) {
      setProgramFilter(String(programOptions[0][0]));
    }
  }, [programOptions, programFilter]);

  useEffect(() => {
    setGroupTypeFilter('');
  }, [programFilter]);

  return (
    <div className="space-y-2">
      {loading && (
        <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="assign-form-groups-loading">
          Loading groups…
        </p>
      )}
      {loadError && (
        <p className="text-sm text-red-600 dark:text-red-400" data-testid="assign-form-groups-error">
          {loadError}
        </p>
      )}
      {!loading && !loadError && groups.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="assign-form-groups-empty">
          No active assignment groups found in this org.
        </p>
      )}
      {!loading && !loadError && groups.length > 0 && (
        <>
          <div className="flex flex-wrap gap-3">
            <label className="block text-sm text-gray-700 dark:text-gray-300 min-w-[12rem]">
              Program
              <select
                value={programFilter}
                onChange={(e) => setProgramFilter(e.target.value)}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                data-testid="assign-form-program-filter"
              >
                <option value="">Select program…</option>
                {programOptions.map(([id, label]) => (
                  <option key={id} value={String(id)}>{label}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm text-gray-700 dark:text-gray-300 min-w-[12rem]">
              Group type
              <select
                value={groupTypeFilter}
                onChange={(e) => setGroupTypeFilter(e.target.value)}
                disabled={!programFilter}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm disabled:opacity-50"
                data-testid="assign-form-group-type-filter"
              >
                <option value="">Select type…</option>
                {typeOptions.map((gt) => (
                  <option key={gt} value={gt}>{GROUP_TYPE_LABEL[gt] ?? gt}</option>
                ))}
              </select>
            </label>
          </div>
          {!filtersReady && (
            <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="assign-form-groups-filter-hint">
              Select a program and group type to browse groups.
            </p>
          )}
          {filtersReady && (
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search groups…"
              className="w-full text-sm rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700"
              data-testid="assign-form-group-search"
            />
          )}
        </>
      )}
      {filtersReady && visibleGroups.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="assign-form-groups-filter-empty">
          No groups match these filters.
        </p>
      )}
      {filtersReady && visibleGroups.length > 0 && (
        <div
          className="rounded-md border border-gray-200 dark:border-gray-700 p-2 space-y-2"
          data-testid="assign-form-group-list"
        >
          <label className="flex items-center gap-2 text-xs font-medium text-gray-600 dark:text-gray-300 cursor-pointer">
            <input
              type="checkbox"
              checked={allVisibleSelected}
              ref={(el) => {
                if (el) el.indeterminate = !allVisibleSelected && someVisibleSelected;
              }}
              onChange={toggleAllVisible}
              data-testid="assign-form-group-select-all"
            />
            Select all ({visibleGroups.length})
          </label>
          <ul className="max-h-48 overflow-y-auto space-y-1">
            {visibleGroups.map((g) => {
              const checked = selectedIds.has(g.id);
              const outcome = groupResults?.[g.id];
              return (
                <li key={g.id}>
                  <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => onToggleGroup(g.id)}
                      data-testid={`assign-form-group-${g.id}`}
                    />
                    <span className="truncate" data-testid={`assign-form-group-label-${g.id}`}>
                      {g.name}
                      {g.group_type ? ` (${GROUP_TYPE_SHORT[g.group_type] ?? g.group_type})` : ''}
                      <span className="text-gray-400 dark:text-gray-500 ml-1.5">#{g.id}</span>
                    </span>
                    {outcome?.status === 'ok' && (
                      <span className="text-xs text-green-700 dark:text-green-300">✓</span>
                    )}
                    {outcome?.status === 'conflict' && (
                      <span className="text-xs text-amber-700 dark:text-amber-300" title={outcome.detail}>
                        conflict
                      </span>
                    )}
                    {outcome?.status === 'error' && (
                      <span className="text-xs text-red-700 dark:text-red-300" title={outcome.detail}>
                        error
                      </span>
                    )}
                  </label>
                </li>
              );
            })}
          </ul>
        </div>
      )}
      {selectedIds.size > 0 && (
        <p className="text-xs text-gray-500 dark:text-gray-400" data-testid="assign-form-groups-selected-count">
          {selectedIds.size} group{selectedIds.size === 1 ? '' : 's'} selected.
        </p>
      )}

      {scoredCamperError && (
        <div
          className="rounded-md border border-amber-400 dark:border-amber-600 bg-amber-50 dark:bg-amber-900/20 p-3 text-sm text-amber-900 dark:text-amber-200"
          data-testid="assign-form-scored-camper-error"
          role="alert"
        >
          <p className="font-semibold mb-1">
            This bunk already has an active scored camper form.
          </p>
          <p>
            Only one scored camper form can drive a bunk&apos;s score grid. End or replace the
            existing assignment first.
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Conflict resolution panel ────────────────────────────────────────────────

function ConflictPanel({ conflicts, resolution, onResolutionChange, onConfirm, onCancel, submitting }) {
  return (
    <div
      className="rounded-md border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-4 space-y-3"
      data-testid="assign-form-conflict-panel"
    >
      <p className="text-sm font-semibold text-amber-900 dark:text-amber-200">
        This assignment overlaps with an existing one:
      </p>
      <ul className="text-xs text-amber-800 dark:text-amber-300 list-disc list-inside space-y-0.5">
        {conflicts.map((c) => (
          <li key={c.id} data-testid={`conflict-item-${c.id}`}>
            <span className="font-medium">{c.display_title || c.title || c.template_slug}</span>
            {' '}·{' '}
            {c.start_date} – {c.end_date ?? 'ongoing'}
            {c.assignment_group_name ? ` · ${c.assignment_group_name}` : ''}
          </li>
        ))}
      </ul>
      <fieldset>
        <legend className="sr-only">Conflict resolution</legend>
        <div className="space-y-2">
          {CONFLICT_CHOICES.map((choice) => (
            <label
              key={choice.value}
              className="flex items-center gap-2 text-sm text-amber-900 dark:text-amber-200 cursor-pointer"
            >
              <input
                type="radio"
                name="conflict-resolution"
                value={choice.value}
                checked={resolution === choice.value}
                onChange={() => onResolutionChange(choice.value)}
                data-testid={`conflict-choice-${choice.value}`}
              />
              {choice.label}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={onCancel}
          className="text-sm rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1.5"
          data-testid="conflict-cancel"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={!resolution || submitting}
          className="text-sm rounded-md bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-3 py-1.5"
          data-testid="conflict-confirm"
        >
          {submitting ? 'Confirming…' : 'Confirm'}
        </button>
      </div>
    </div>
  );
}

// ─── Main dialog ──────────────────────────────────────────────────────────────

/**
 * @param {object} props
 * @param {object} props.template — the ReflectionTemplate being assigned
 * @param {function} props.onClose
 * @param {function} props.onCreated — called with the new assignment on 201
 */
export default function AssignFormDialog({ template, onClose, onCreated }) {
  const { orgSlug } = useAuth();

  // Form state
  const [targetType, setTargetType] = useState('assignment_group');
  const [selectedGroupIds, setSelectedGroupIds] = useState(() => new Set());
  const [role, setRole] = useState('counselor');
  const [tag, setTag] = useState('');
  const [title, setTitle] = useState('');
  const [isRequired, setIsRequired] = useState(true);
  const [startDate, setStartDate] = useState(todayStr());
  const [endDate, setEndDate] = useState('');
  const [cadenceOverride, setCadenceOverride] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Submission state
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [dateError, setDateError] = useState('');
  const [groupResults, setGroupResults] = useState({});

  // Scored-camper guard (400 with specific message)
  const [scoredCamperError, setScoredCamperError] = useState('');

  // Batch conflict resolution (assignment_group multi-POST)
  const [conflicts, setConflicts] = useState([]);
  const [resolution, setResolution] = useState('');

  // Single-target conflict resolution (role / tag_group)
  const [conflictState, setConflictState] = useState(null);
  const [singleResolution, setSingleResolution] = useState('replace');

  // Validate end >= start client-side
  const validateDates = () => {
    if (endDate && startDate && endDate < startDate) {
      setDateError('End date must be on or after start date.');
      return false;
    }
    setDateError('');
    return true;
  };

  const buildBasePayload = () => {
    const payload = {
      template: template?.id,
      is_required: isRequired,
      start_date: startDate,
    };
    if (title.trim()) payload.title = title.trim();
    if (endDate) payload.end_date = endDate;
    if (cadenceOverride) payload.cadence_override = cadenceOverride;
    return payload;
  };

  const buildPayload = (extraFields = {}) => {
    const payload = {
      ...buildBasePayload(),
      target_type: targetType,
      ...extraFields,
    };

    if (targetType === 'assignment_group') {
      payload.target_payload = { role: role || template?.role || 'counselor' };
      if (extraFields.assignment_group) payload.assignment_group = extraFields.assignment_group;
    } else if (targetType === 'role') {
      payload.target_payload = { role };
    } else if (targetType === 'tag_group') {
      payload.target_payload = { tag };
    }

    return payload;
  };

  const toggleGroup = (id) => {
    setSelectedGroupIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const submitGroups = async () => {
    if (conflicts.length > 0 && !resolution) {
      setError('Pick how to resolve the conflict.');
      return false;
    }
    const ids = Array.from(selectedGroupIds);
    const results = { ...groupResults };
    let anyConflict = false;
    const conflictRows = [];
    let scoredMsg = '';

    for (const gid of ids) {
      const prior = results[gid];
      if (prior?.status === 'ok') continue;

      const body = {
        ...buildBasePayload(),
        target_type: 'assignment_group',
        target_payload: { role: role || template?.role || 'counselor' },
        assignment_group: gid,
      };
      if (resolution) body.conflict_resolution = resolution;

      try {
        const data = await createAssignment(orgSlug, body);
        results[gid] = { status: 'ok', assignment: data };
        if (onCreated) onCreated(data);
      } catch (err) {
        const status = err?.response?.status;
        if (status === 409) {
          anyConflict = true;
          const body409 = err.response.data ?? {};
          results[gid] = {
            status: 'conflict',
            detail: body409.detail ?? 'Conflicting assignment exists.',
            conflicts: body409.conflicts ?? [],
          };
          conflictRows.push(...(body409.conflicts ?? []));
        } else if (status === 400) {
          const body400 = err.response.data;
          const msg = extractScoredCamperError(body400);
          if (msg) scoredMsg = msg;
          const detail = msg || extractErrorMessage(body400);
          results[gid] = { status: 'error', detail };
        } else {
          results[gid] = {
            status: 'error',
            detail: extractErrorMessage(err?.response?.data),
          };
        }
      }
    }

    setGroupResults(results);
    if (scoredMsg) setScoredCamperError(scoredMsg);

    if (anyConflict) {
      setConflicts(conflictRows);
      setError('One or more groups already have an active assignment. Pick a resolution and retry.');
      setResolution((prev) => prev || '');
      return false;
    }

    const everyOk = ids.every((id) => results[id]?.status === 'ok');
    if (everyOk) {
      onClose?.();
      return true;
    }
    setError('Some assignments could not be created. See per-group errors below.');
    return false;
  };

  const handleSubmit = async () => {
    setError('');
    setScoredCamperError('');
    setDateError('');

    if (!template?.id) { setError('No template selected.'); return; }
    if (!startDate) { setError('Start date is required.'); return; }
    if (!validateDates()) return;
    if (targetType === 'assignment_group' && selectedGroupIds.size === 0) {
      setError('Check at least one group.'); return;
    }
    if (targetType === 'role' && !role) { setError('Select a role.'); return; }
    if (targetType === 'tag_group' && !tag.trim()) { setError('Enter a tag.'); return; }

    setSubmitting(true);
    try {
      if (targetType === 'assignment_group') {
        await submitGroups();
        return;
      }
      const payload = buildPayload();
      const data = await createAssignment(orgSlug, payload);
      if (onCreated) onCreated(data);
      onClose?.();
    } catch (err) {
      const status = err?.response?.status;
      if (status === 409) {
        const body = err.response.data ?? {};
        setConflictState({ conflicts: body.conflicts ?? [], pendingPayload: buildPayload() });
        setSingleResolution('replace');
      } else if (status === 400) {
        const body = err.response.data;
        const scoredMsg = extractScoredCamperError(body);
        if (scoredMsg) {
          setScoredCamperError(scoredMsg);
        } else {
          setError(extractErrorMessage(body));
        }
      } else {
        setError(extractErrorMessage(err?.response?.data));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleConflictConfirm = async () => {
    if (!conflictState) return;
    if (singleResolution === 'cancel') {
      onClose?.();
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const payload = { ...conflictState.pendingPayload, conflict_resolution: singleResolution };
      const data = await createAssignment(orgSlug, payload);
      if (onCreated) onCreated(data);
      onClose?.();
    } catch (err) {
      const status = err?.response?.status;
      if (status === 409) {
        const body = err.response.data ?? {};
        setConflictState({ conflicts: body.conflicts ?? [], pendingPayload: conflictState.pendingPayload });
      } else {
        setConflictState(null);
        setError(extractErrorMessage(err?.response?.data));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleConflictCancel = () => {
    onClose?.();
  };

  const inSingleConflict = Boolean(conflictState);
  const fieldDisabled = submitting || inSingleConflict;
  const assignButtonLabel = (() => {
    if (submitting) return 'Assigning…';
    if (targetType === 'assignment_group' && selectedGroupIds.size > 1) {
      return `Assign to ${selectedGroupIds.size} groups`;
    }
    return 'Assign form';
  })();

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center px-4"
      data-testid="assign-form-dialog"
      role="dialog"
      aria-modal="true"
      aria-label="Assign form"
    >
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full p-5 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">Assign form</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            data-testid="assign-form-close"
            aria-label="Close dialog"
          >
            ✕
          </button>
        </div>

        {template && (
          <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
            <span className="font-medium">{template.name}</span>
            <span className="ml-2 text-xs text-gray-400">v{template.version}</span>
          </p>
        )}

        <div className="space-y-4">
          {/* Target type */}
          <fieldset>
            <legend className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Target type <span className="text-red-500">*</span>
            </legend>
            <div className="space-y-1.5" role="radiogroup" data-testid="assign-form-target-type">
              {TARGET_TYPES.map((t) => (
                <label
                  key={t.value}
                  className={`flex items-center gap-2 text-sm ${
                    t.disabled
                      ? 'text-gray-400 dark:text-gray-500 cursor-not-allowed'
                      : 'text-gray-700 dark:text-gray-300 cursor-pointer'
                  }`}
                >
                  <input
                    type="radio"
                    name="target-type"
                    value={t.value}
                    checked={targetType === t.value}
                    disabled={fieldDisabled || t.disabled}
                    onChange={() => setTargetType(t.value)}
                    data-testid={`assign-form-target-${t.value}`}
                  />
                  {t.label}
                  {t.recommended && (
                    <span className="text-xs text-indigo-600 dark:text-indigo-400">(recommended)</span>
                  )}
                  {t.disabled && t.hint && (
                    <span className="text-xs text-gray-400 dark:text-gray-500">— {t.hint}</span>
                  )}
                </label>
              ))}
            </div>
          </fieldset>

          {/* Target value */}
          {targetType === 'assignment_group' && (
            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Assignment groups <span className="text-red-500">*</span>
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                Check one or more groups. A separate assignment is created per group.
              </p>
              <fieldset disabled={fieldDisabled}>
                <GroupPicker
                  orgSlug={orgSlug}
                  template={template}
                  selectedIds={selectedGroupIds}
                  onToggleGroup={toggleGroup}
                  onSetSelectedIds={setSelectedGroupIds}
                  groupResults={groupResults}
                  scoredCamperError={scoredCamperError}
                />
              </fieldset>
            </div>
          )}

          {targetType === 'role' && (
            <label className="block text-sm text-gray-700 dark:text-gray-300">
              Role <span className="text-red-500">*</span>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                disabled={fieldDisabled}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm disabled:opacity-50"
                data-testid="assign-form-role"
              >
                {ROLE_OPTIONS.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </label>
          )}

          {targetType === 'tag_group' && (
            <label className="block text-sm text-gray-700 dark:text-gray-300">
              Tag string <span className="text-red-500">*</span>
              <input
                type="text"
                value={tag}
                onChange={(e) => setTag(e.target.value)}
                disabled={fieldDisabled}
                placeholder="e.g. kitchen-lead"
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm disabled:opacity-50"
                data-testid="assign-form-tag"
              />
            </label>
          )}

          {/* Title */}
          <label className="block text-sm text-gray-700 dark:text-gray-300">
            Title (optional)
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={fieldDisabled}
              maxLength={255}
              placeholder="Leave blank to use template name"
              className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm disabled:opacity-50"
              data-testid="assign-form-title"
            />
          </label>

          {/* Required toggle */}
          <label className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
            <input
              type="checkbox"
              checked={isRequired}
              onChange={(e) => setIsRequired(e.target.checked)}
              disabled={fieldDisabled}
              className="mt-0.5 rounded"
              data-testid="assign-form-required"
            />
            <span>
              Required
              <span className="block text-xs font-normal text-gray-500 dark:text-gray-400">
                On: appears in staff task lists. Off: appears in optional forms library.
              </span>
            </span>
          </label>

          {/* Dates */}
          <div className="flex gap-3 flex-wrap">
            <label className="flex-1 min-w-[8rem] text-sm text-gray-700 dark:text-gray-300">
              Start date <span className="text-red-500">*</span>
              <input
                type="date"
                value={startDate}
                onChange={(e) => { setStartDate(e.target.value); setDateError(''); }}
                disabled={fieldDisabled}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm disabled:opacity-50"
                data-testid="assign-form-start-date"
              />
            </label>
            <label className="flex-1 min-w-[8rem] text-sm text-gray-700 dark:text-gray-300">
              End date (optional)
              <input
                type="date"
                value={endDate}
                onChange={(e) => { setEndDate(e.target.value); setDateError(''); }}
                disabled={fieldDisabled}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm disabled:opacity-50"
                data-testid="assign-form-end-date"
              />
            </label>
          </div>
          {dateError && (
            <p className="text-xs text-red-600 dark:text-red-400" data-testid="assign-form-date-error">
              {dateError}
            </p>
          )}

          {/* Advanced: cadence override */}
          <div>
            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className="text-xs text-gray-500 dark:text-gray-400 hover:underline"
              data-testid="assign-form-advanced-toggle"
            >
              {showAdvanced ? '▾' : '▸'} Advanced
            </button>
            {showAdvanced && (
              <label className="block text-sm text-gray-700 dark:text-gray-300 mt-2">
                Cadence override (optional)
                <select
                  value={cadenceOverride}
                  onChange={(e) => setCadenceOverride(e.target.value)}
                  disabled={fieldDisabled}
                  className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm disabled:opacity-50"
                  data-testid="assign-form-cadence"
                >
                  <option value="">inherit from template</option>
                  {CADENCES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Overrides the template&apos;s default cadence for this assignment only.
                </p>
              </label>
            )}
          </div>

          {/* Generic error (non-scored-camper 400, network, etc.) */}
          {error && (
            <p
              className="text-sm text-red-600 dark:text-red-400"
              data-testid="assign-form-error"
            >
              {error}
            </p>
          )}

          {targetType === 'assignment_group' && conflicts.length > 0 && (
            <div
              className="rounded-md border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-3 text-sm text-amber-900 dark:text-amber-200"
              data-testid="assign-form-conflicts"
            >
              <p className="font-medium mb-1">Conflicting assignments:</p>
              <ul className="list-disc list-inside text-xs space-y-0.5 mb-2">
                {conflicts.map((c) => (
                  <li key={c.id} data-testid={`conflict-item-${c.id}`}>
                    {c.display_title || c.title || c.template_slug}
                    {' · '}
                    {c.start_date} – {c.end_date ?? 'ongoing'}
                    {c.assignment_group_name ? ` · ${c.assignment_group_name}` : ''}
                  </li>
                ))}
              </ul>
              <fieldset className="space-y-1" role="radiogroup">
                {CONFLICT_CHOICES.map((choice) => (
                  <label key={choice.value} className="flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name="assign-form-batch-conflict"
                      value={choice.value}
                      checked={resolution === choice.value}
                      onChange={() => setResolution(choice.value)}
                      data-testid={`conflict-choice-${choice.value}`}
                    />
                    {choice.label}
                  </label>
                ))}
              </fieldset>
            </div>
          )}

          {/* Conflict resolution panel — role/tag single POST only */}
          {inSingleConflict ? (
            <ConflictPanel
              conflicts={conflictState.conflicts}
              resolution={singleResolution}
              onResolutionChange={setSingleResolution}
              onConfirm={handleConflictConfirm}
              onCancel={handleConflictCancel}
              submitting={submitting}
            />
          ) : (
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="text-sm rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1.5"
                data-testid="assign-form-cancel"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting}
                className="text-sm rounded-md bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-3 py-1.5"
                data-testid="assign-form-submit"
              >
                {assignButtonLabel}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
