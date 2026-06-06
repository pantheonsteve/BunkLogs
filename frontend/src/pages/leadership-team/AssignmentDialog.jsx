/**
 * LT Assignment Dialog — Step 7_12 Story 52, extended in Step 7_22.
 *
 * Modal for creating one or more TemplateAssignments. Four target types:
 * role / individuals / tag_group (single POST), and assignment_group
 * (one POST per checked group; results aggregated). Conflict (409) flow
 * surfaces an inline picker so the user can retry with replace / run_both
 * / cancel. Caller controls open/close; ``onCreated(assignment)`` fires
 * for each successful create.
 *
 * Extended fields exposed in this dialog:
 *   - ``title``       — per-assignment display title (falls back to template.name)
 *   - ``is_required`` — whether the assignment produces dashboard tasks (default true)
 *   - ``subject_mode`` — read-only badge surfaced from the template so the LT user
 *     knows what mode they are assigning without leaving the dialog.
 *   - group_type filter — narrows the assignment-group picker to a single group type
 *     (bunk / unit / etc.) so large orgs don't have to scroll through everything.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  createAssignment,
  listAssignmentGroups,
  listAssignments,
  unassignAssignment,
} from '../../api/leadershipTeam';
import { useAuth } from '../../auth/AuthContext';

const TARGET_TYPES = [
  { value: 'role', label: 'Role' },
  { value: 'individuals', label: 'Individuals' },
  { value: 'tag_group', label: 'Tag group' },
  { value: 'assignment_group', label: 'Assignment group' },
];

const ROLE_OPTIONS = [
  'counselor', 'junior_counselor', 'specialist', 'general_counselor',
  'unit_head', 'leadership_team', 'kitchen_staff', 'maintenance',
  'administrative_staff', 'housekeeping', 'camper_care', 'health_center', 'medical',
  'madrich', 'faculty',
];

const CADENCE_OVERRIDES = ['', 'daily', 'weekly', 'biweekly', 'monthly', 'on_demand'];

const SUBJECT_MODE_LABELS = {
  self: 'Self-reflection',
  single_subject: 'Single subject',
  multi_subject: 'Multi-subject',
  group: 'Group / unit',
};

const SCOPE_LABELS = {
  none: 'No group context',
  per_subject_in_group: 'Per-subject in group',
  per_group: 'Per group',
};

// Human labels for group types shown as compact pills in the template header.
const GROUP_TYPE_SHORT = {
  bunk: 'Bunk', unit: 'Unit', division: 'Division', cohort: 'Cohort',
  classroom: 'Classroom', caseload: 'Caseload', specialty: 'Specialty', custom: 'Custom',
};

const CONFLICT_CHOICES = [
  { value: 'replace', label: 'Replace existing (end prior assignment)' },
  { value: 'run_both', label: 'Run both' },
  { value: 'cancel', label: 'Cancel — keep prior, do not create' },
];

// Display order for group_type sections; anything unrecognised falls under
// "Other". Matches the order in core.models.AssignmentGroup.GROUP_TYPES.
const GROUP_TYPE_ORDER = [
  'bunk', 'unit', 'division', 'cohort', 'classroom', 'caseload', 'specialty', 'custom',
];

const GROUP_TYPE_LABEL = {
  bunk: 'Bunks',
  unit: 'Units',
  division: 'Divisions',
  cohort: 'Cohorts',
  classroom: 'Classrooms',
  caseload: 'Caseloads',
  specialty: 'Specialty / Activity groups',
  custom: 'Custom groups',
};

// Render a compact human label for an assignment row so the LT user can
// tell rows apart in the "Current assignments" list. Falls back to the
// raw target_type when nothing more specific is available.
function describeAssignment(a) {
  if (!a) return '';
  if (a.target_type === 'role') {
    const role = a.target_payload?.role;
    return role ? `Role: ${role}` : 'Role';
  }
  if (a.target_type === 'individuals') {
    const n = Array.isArray(a.target_payload?.membership_ids)
      ? a.target_payload.membership_ids.length
      : 0;
    return `Individuals (${n})`;
  }
  if (a.target_type === 'tag_group') {
    const tag = a.target_payload?.tag;
    return tag ? `Tag: ${tag}` : 'Tag group';
  }
  if (a.target_type === 'assignment_group') {
    return a.assignment_group_name
      ? `Group: ${a.assignment_group_name}`
      : `Group #${a.assignment_group ?? '?'}`;
  }
  return a.target_type || 'Assignment';
}

function groupByGroupType(groups) {
  const buckets = new Map();
  for (const g of groups) {
    const key = g.group_type || 'other';
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(g);
  }
  const ordered = [];
  for (const key of GROUP_TYPE_ORDER) {
    if (buckets.has(key)) {
      ordered.push([key, buckets.get(key)]);
      buckets.delete(key);
    }
  }
  for (const [key, list] of buckets) ordered.push([key, list]);
  for (const [, list] of ordered) {
    list.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  }
  return ordered;
}

export default function AssignmentDialog({ template, onClose, onCreated }) {
  const { orgSlug } = useAuth();
  const [targetType, setTargetType] = useState('role');
  const [role, setRole] = useState(template?.role ?? 'counselor');
  const [membershipIds, setMembershipIds] = useState('');
  const [tag, setTag] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [cadenceOverride, setCadenceOverride] = useState('');
  // Step 7_20 fields: title and is_required on the TemplateAssignment row.
  const [assignmentTitle, setAssignmentTitle] = useState('');
  const [isRequired, setIsRequired] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [conflicts, setConflicts] = useState([]);
  const [resolution, setResolution] = useState('');

  // Assignment-group picker state.
  const [groups, setGroups] = useState([]);
  const [groupsLoading, setGroupsLoading] = useState(false);
  const [groupsError, setGroupsError] = useState('');
  const [selectedGroupIds, setSelectedGroupIds] = useState(() => new Set());
  // Narrows the group list to a single type (bunk / unit / etc.) when set.
  const [groupTypeFilter, setGroupTypeFilter] = useState('');
  // Per-group submission outcomes for the assignment_group flow.
  // { [groupId]: { status: 'ok' | 'conflict' | 'error', detail?, assignment? } }
  const [groupResults, setGroupResults] = useState({});

  const grouped = useMemo(() => groupByGroupType(groups), [groups]);
  const visibleGrouped = useMemo(
    () => (groupTypeFilter ? grouped.filter(([gt]) => gt === groupTypeFilter) : grouped),
    [grouped, groupTypeFilter],
  );

  // Existing assignments for this template (active or scheduled).
  const [current, setCurrent] = useState([]);
  const [currentLoading, setCurrentLoading] = useState(false);
  const [currentError, setCurrentError] = useState('');
  const [unassignPending, setUnassignPending] = useState(null);

  const reloadCurrent = useCallback(async () => {
    if (!template?.id) return;
    setCurrentLoading(true);
    setCurrentError('');
    try {
      const data = await listAssignments(orgSlug, { template: template.id });
      const rows = (data?.assignments ?? data?.results ?? data ?? []).filter(
        (a) => a.status === 'active' || a.status === 'scheduled',
      );
      setCurrent(rows);
    } catch {
      setCurrentError('Failed to load current assignments.');
    } finally {
      setCurrentLoading(false);
    }
  }, [orgSlug, template?.id]);

  useEffect(() => { reloadCurrent(); }, [reloadCurrent]);

  const handleUnassign = async (assignment) => {
    const ok = typeof window !== 'undefined'
      ? window.confirm(`Unassign "${assignment.display_title || assignment.template_slug}" from this audience?`)
      : true;
    if (!ok) return;
    setUnassignPending(assignment.id);
    setError('');
    try {
      await unassignAssignment(orgSlug, assignment);
      if (onCreated) {
        // Reuse the same callback so the parent can refresh the
        // template list (count badge). Pass a marker so callers can
        // tell creates from unassigns if they care.
        onCreated({ ...assignment, _unassigned: true });
      }
      await reloadCurrent();
    } catch (err) {
      const detail = err?.response?.data?.detail
        ?? err?.response?.data?.errors
        ?? 'Failed to unassign.';
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setUnassignPending(null);
    }
  };

  // Lazy-load groups the first time the user opens the AG tab. We deliberately
  // omit ``groupsLoading`` from the dep array — toggling it inside the effect
  // would otherwise trip the cleanup and cancel the in-flight fetch.
  const [groupsLoaded, setGroupsLoaded] = useState(false);
  useEffect(() => {
    if (targetType !== 'assignment_group') return undefined;
    if (groupsLoaded || groupsLoading) return undefined;
    let cancelled = false;
    setGroupsLoading(true);
    setGroupsError('');
    listAssignmentGroups(orgSlug)
      .then((rows) => { if (!cancelled) setGroups(rows); })
      .catch(() => { if (!cancelled) setGroupsError('Failed to load assignment groups.'); })
      .finally(() => {
        if (cancelled) return;
        setGroupsLoading(false);
        setGroupsLoaded(true);
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetType, orgSlug, groupsLoaded]);

  const toggleGroup = (id) => {
    setSelectedGroupIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };
  const toggleGroupType = (gtypeGroups) => {
    const ids = gtypeGroups.map((g) => g.id);
    setSelectedGroupIds((prev) => {
      const next = new Set(prev);
      const allChecked = ids.every((id) => next.has(id));
      for (const id of ids) {
        if (allChecked) next.delete(id); else next.add(id);
      }
      return next;
    });
  };

  const baseBody = useCallback(() => {
    const body = {
      template: template?.id,
      start_date: startDate,
      is_required: isRequired,
    };
    const trimmedTitle = assignmentTitle.trim();
    if (trimmedTitle) body.title = trimmedTitle;
    if (endDate) body.end_date = endDate;
    if (cadenceOverride) body.cadence_override = cadenceOverride;
    return body;
  }, [template, startDate, endDate, cadenceOverride, isRequired, assignmentTitle]);

  const buildSinglePayload = useCallback(() => {
    const target_payload = (() => {
      if (targetType === 'role') return { role };
      if (targetType === 'individuals') {
        const ids = membershipIds
          .split(',')
          .map((s) => parseInt(s.trim(), 10))
          .filter((n) => Number.isFinite(n));
        return { membership_ids: ids };
      }
      return { tag };
    })();
    return {
      ...baseBody(),
      target_type: targetType,
      target_payload,
    };
  }, [baseBody, targetType, role, membershipIds, tag]);

  // Validate, return error message string or '' when OK.
  const validate = () => {
    if (!template?.id) return 'Choose a template first.';
    if (!startDate) return 'Start date is required.';
    if (targetType === 'role' && !role) return 'Pick a role.';
    if (targetType === 'individuals' && !membershipIds.trim()) {
      return 'Enter at least one membership ID.';
    }
    if (targetType === 'tag_group' && !tag.trim()) {
      return 'Enter a tag.';
    }
    if (targetType === 'assignment_group' && selectedGroupIds.size === 0) {
      return 'Check at least one group.';
    }
    return '';
  };

  const submitOne = async (body) => {
    if (conflicts.length > 0 && resolution) {
      body.conflict_resolution = resolution;
    }
    return createAssignment(orgSlug, body);
  };

  // Submit one POST per checked group; aggregate per-group results.
  const submitGroups = async () => {
    const ids = Array.from(selectedGroupIds);
    const baseRoleHint = role || template?.role || 'counselor';
    const results = {};
    let anyConflict = false;
    const conflictRows = [];
    for (const gid of ids) {
      // Prior outcome: skip rows that already succeeded so a Retry only
      // re-attempts failures / conflicts.
      const prior = groupResults[gid];
      if (prior?.status === 'ok') {
        results[gid] = prior;
        continue;
      }
      const body = {
        ...baseBody(),
        target_type: 'assignment_group',
        // Backend ignores target_payload for assignment_group but the
        // legacy serializer still echoes it back, so send the author
        // role hint as documentation.
        target_payload: { role: baseRoleHint },
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
        } else {
          const detail = err?.response?.data?.detail
            ?? err?.response?.data?.errors
            ?? 'Failed to create assignment.';
          results[gid] = {
            status: 'error',
            detail: typeof detail === 'string' ? detail : JSON.stringify(detail),
          };
        }
      }
    }
    setGroupResults(results);
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

  const submit = async () => {
    setError('');
    const validationError = validate();
    if (validationError) { setError(validationError); return; }
    setSubmitting(true);
    try {
      if (targetType === 'assignment_group') {
        await submitGroups();
        return;
      }
      if (conflicts.length > 0 && !resolution) {
        setError('Pick how to resolve the conflict.');
        return;
      }
      const data = await submitOne(buildSinglePayload());
      if (onCreated) onCreated(data);
      onClose?.();
    } catch (err) {
      const status = err?.response?.status;
      if (status === 409) {
        const body = err.response.data ?? {};
        setConflicts(body.conflicts ?? []);
        setError(body.detail ?? 'There is a conflicting assignment.');
        setResolution('');
      } else {
        const detail = err?.response?.data?.detail
          ?? err?.response?.data?.errors
          ?? 'Failed to create assignment.';
        setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center px-4"
      data-testid="lt-assignment-dialog"
    >
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg max-w-lg w-full p-5 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">
            Assign template
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-gray-500 hover:text-gray-700"
            data-testid="lt-assignment-close"
          >
            ✕
          </button>
        </div>

        <div className="mb-3">
          <p className="text-sm text-gray-600 dark:text-gray-300 mb-1.5">
            {template?.name} <span className="text-xs text-gray-400">v{template?.version}</span>
          </p>
          {/* Template-level configuration badges — edit the template to change these. */}
          <div className="flex flex-wrap gap-1.5" data-testid="lt-assignment-template-badges">
            {template?.subject_mode && (
              <span
                className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 font-medium"
                title="Subject mode — configured on the template"
                data-testid="lt-assignment-subject-mode-badge"
              >
                {SUBJECT_MODE_LABELS[template.subject_mode] ?? template.subject_mode}
              </span>
            )}
            {template?.assignment_scope && template.assignment_scope !== 'none' && (
              <span
                className="text-xs px-2 py-0.5 rounded-full bg-sky-100 dark:bg-sky-900/40 text-sky-700 dark:text-sky-300 font-medium"
                title="Assignment scope — configured on the template"
                data-testid="lt-assignment-scope-badge"
              >
                {SCOPE_LABELS[template.assignment_scope] ?? template.assignment_scope}
              </span>
            )}
            {Array.isArray(template?.assignment_group_types) && template.assignment_group_types.map((gt) => (
              <span
                key={gt}
                className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 font-medium"
                title="Applies to this group type"
                data-testid={`lt-assignment-group-type-badge-${gt}`}
              >
                {GROUP_TYPE_SHORT[gt] ?? gt}
              </span>
            ))}
          </div>
          {(template?.subject_mode || template?.assignment_scope) && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              Subject mode and scope are set on the template — edit the template to change them.
            </p>
          )}
        </div>

        <section
          className="mb-4 rounded-md border border-gray-200 dark:border-gray-700 p-3"
          data-testid="lt-current-assignments"
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-100">
              Current assignments
            </h3>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {currentLoading ? 'Loading…' : `${current.length} active/scheduled`}
            </span>
          </div>
          {currentError && (
            <p className="text-sm text-red-600 dark:text-red-400" data-testid="lt-current-error">
              {currentError}
            </p>
          )}
          {!currentLoading && !currentError && current.length === 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="lt-current-empty">
              Not currently assigned to anyone.
            </p>
          )}
          {current.length > 0 && (
            <ul className="space-y-1.5">
              {current.map((a) => (
                <li
                  key={a.id}
                  className="flex items-center justify-between gap-2 text-sm text-gray-700 dark:text-gray-200"
                  data-testid={`lt-current-row-${a.id}`}
                >
                  <div className="min-w-0">
                    <div className="truncate">{describeAssignment(a)}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {a.start_date} – {a.end_date ?? '∞'}
                      <span className="ml-2 uppercase tracking-wide">{a.status}</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleUnassign(a)}
                    disabled={unassignPending === a.id}
                    className="text-xs rounded-md border border-red-300 dark:border-red-700 text-red-700 dark:text-red-300 px-2 py-1 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50"
                    data-testid={`lt-unassign-${a.id}`}
                  >
                    {unassignPending === a.id ? 'Unassigning…' : 'Unassign'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className="space-y-3">
          <div className="flex gap-2 flex-wrap" role="tablist" data-testid="lt-assignment-target-tabs">
            {TARGET_TYPES.map((t) => (
              <button
                key={t.value}
                type="button"
                role="tab"
                aria-selected={targetType === t.value}
                onClick={() => setTargetType(t.value)}
                className={`text-sm px-3 py-1 rounded-md ${
                  targetType === t.value
                    ? 'bg-indigo-600 text-white'
                    : 'border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300'
                }`}
                data-testid={`lt-assignment-target-${t.value}`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {targetType === 'role' && (
            <label className="block text-sm text-gray-700 dark:text-gray-300">
              Role
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                data-testid="lt-assignment-role"
              >
                {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Membership in this role auto-includes future additions while the assignment is active.
              </p>
            </label>
          )}

          {targetType === 'individuals' && (
            <label className="block text-sm text-gray-700 dark:text-gray-300">
              Membership IDs (comma-separated)
              <input
                type="text"
                value={membershipIds}
                onChange={(e) => setMembershipIds(e.target.value)}
                placeholder="123, 456"
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                data-testid="lt-assignment-individuals"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Static snapshot — added members later need a new assignment.
              </p>
            </label>
          )}

          {targetType === 'tag_group' && (
            <label className="block text-sm text-gray-700 dark:text-gray-300">
              Membership tag
              <input
                type="text"
                value={tag}
                onChange={(e) => setTag(e.target.value)}
                placeholder="e.g. kitchen-lead"
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                data-testid="lt-assignment-tag"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Dynamic — any membership with this tag is included.
              </p>
            </label>
          )}

          {targetType === 'assignment_group' && (
            <div className="space-y-2" data-testid="lt-assignment-groups-panel">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Check one or more groups. A separate assignment is created per group.
              </p>
              {groupsLoading && (
                <p className="text-sm text-gray-500" data-testid="lt-groups-loading">Loading groups…</p>
              )}
              {groupsError && (
                <p className="text-sm text-red-600 dark:text-red-400" data-testid="lt-groups-error">
                  {groupsError}
                </p>
              )}
              {!groupsLoading && !groupsError && grouped.length === 0 && (
                <p className="text-sm text-gray-500" data-testid="lt-groups-empty">
                  No active assignment groups found in this org.
                </p>
              )}
              {!groupsLoading && !groupsError && grouped.length > 0 && (
                <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  Filter by group type
                  <select
                    value={groupTypeFilter}
                    onChange={(e) => setGroupTypeFilter(e.target.value)}
                    className="ml-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                    data-testid="lt-assignment-group-type-filter"
                  >
                    <option value="">All types</option>
                    {GROUP_TYPE_ORDER.filter((gt) => grouped.some(([k]) => k === gt)).map((gt) => (
                      <option key={gt} value={gt}>{GROUP_TYPE_LABEL[gt] ?? gt}</option>
                    ))}
                    {grouped
                      .filter(([gt]) => !GROUP_TYPE_ORDER.includes(gt))
                      .map(([gt]) => (
                        <option key={gt} value={gt}>{gt}</option>
                      ))}
                  </select>
                </label>
              )}
              {visibleGrouped.map(([gtype, list]) => {
                const ids = list.map((g) => g.id);
                const allChecked = ids.every((id) => selectedGroupIds.has(id));
                const someChecked = ids.some((id) => selectedGroupIds.has(id));
                return (
                  <fieldset
                    key={gtype}
                    className="rounded-md border border-gray-200 dark:border-gray-700 p-2"
                    data-testid={`lt-assignment-group-section-${gtype}`}
                  >
                    <legend className="px-1 text-xs font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 flex items-center gap-2">
                      <label className="flex items-center gap-1 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={allChecked}
                          ref={(el) => {
                            if (el) el.indeterminate = !allChecked && someChecked;
                          }}
                          onChange={() => toggleGroupType(list)}
                          data-testid={`lt-assignment-group-toggle-all-${gtype}`}
                        />
                        {GROUP_TYPE_LABEL[gtype] || gtype}
                      </label>
                      <span className="font-normal text-gray-400">({list.length})</span>
                    </legend>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 mt-1">
                      {list.map((g) => {
                        const checked = selectedGroupIds.has(g.id);
                        const outcome = groupResults[g.id];
                        return (
                          <label
                            key={g.id}
                            className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300"
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleGroup(g.id)}
                              data-testid={`lt-assignment-group-${g.id}`}
                            />
                            <span className="truncate">{g.name}</span>
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
                        );
                      })}
                    </div>
                  </fieldset>
                );
              })}
              {selectedGroupIds.size > 0 && (
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {selectedGroupIds.size} group{selectedGroupIds.size === 1 ? '' : 's'} selected.
                </p>
              )}
            </div>
          )}

          <div className="flex gap-3">
            <label className="flex-1 text-sm text-gray-700 dark:text-gray-300">
              Start date
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                data-testid="lt-assignment-start"
              />
            </label>
            <label className="flex-1 text-sm text-gray-700 dark:text-gray-300">
              End date (optional)
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                data-testid="lt-assignment-end"
              />
            </label>
          </div>

          <label className="block text-sm text-gray-700 dark:text-gray-300">
            Cadence override (optional)
            <select
              value={cadenceOverride}
              onChange={(e) => setCadenceOverride(e.target.value)}
              className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
              data-testid="lt-assignment-cadence"
            >
              {CADENCE_OVERRIDES.map((c) => (
                <option key={c} value={c}>{c || 'inherit from template'}</option>
              ))}
            </select>
          </label>

          <label className="block text-sm text-gray-700 dark:text-gray-300">
            Display title (optional)
            <input
              type="text"
              value={assignmentTitle}
              onChange={(e) => setAssignmentTitle(e.target.value)}
              placeholder={template?.name ?? 'Defaults to template name'}
              className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
              data-testid="lt-assignment-title"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Override how this assignment appears in dashboards. Leave blank to use the template name.
            </p>
          </label>

          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={isRequired}
              onChange={(e) => setIsRequired(e.target.checked)}
              className="rounded"
              data-testid="lt-assignment-is-required"
            />
            <span>
              Required{' '}
              <span className="font-normal text-gray-500 dark:text-gray-400">
                — produces tasks in per-role dashboards and counts toward "all set"
              </span>
            </span>
          </label>

          {conflicts.length > 0 && (
            <div
              className="rounded-md border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-3 text-sm text-amber-900 dark:text-amber-200"
              data-testid="lt-assignment-conflicts"
            >
              <p className="font-medium mb-1">Conflicting assignments:</p>
              <ul className="list-disc list-inside text-xs space-y-0.5 mb-2">
                {conflicts.map((c) => (
                  <li key={c.id}>
                    #{c.id}: {c.start_date} – {c.end_date ?? '∞'} ({c.target_type})
                  </li>
                ))}
              </ul>
              <fieldset className="space-y-1" role="radiogroup">
                {CONFLICT_CHOICES.map((c) => (
                  <label key={c.value} className="flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name="lt-conflict-resolution"
                      value={c.value}
                      checked={resolution === c.value}
                      onChange={() => setResolution(c.value)}
                      data-testid={`lt-conflict-${c.value}`}
                    />
                    {c.label}
                  </label>
                ))}
              </fieldset>
            </div>
          )}

          {error && (
            <p className="text-red-600 dark:text-red-400 text-sm" data-testid="lt-assignment-error">
              {error}
            </p>
          )}
        </div>

        <div className="flex justify-end gap-2 mt-4">
          <button
            type="button"
            onClick={onClose}
            className="text-sm rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1.5"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={submitting}
            className="text-sm rounded-md bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-3 py-1.5"
            data-testid="lt-assignment-submit"
          >
            {submitting
              ? 'Creating…'
              : targetType === 'assignment_group' && selectedGroupIds.size > 1
                ? `Create ${selectedGroupIds.size} assignments`
                : 'Create assignment'}
          </button>
        </div>
      </div>
    </div>
  );
}
