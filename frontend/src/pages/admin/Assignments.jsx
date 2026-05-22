import { useCallback, useEffect, useState } from 'react';
import {
  listAdminAssignments,
  createAdminAssignment,
  patchAdminAssignment,
} from '../../api/admin';

/**
 * Step 7_13 PR2 — Assignments management (Story 56).
 *
 * Five sub-tabs all mounted on a single endpoint:
 *
 *   - uh_counselor   (Supervision target_type=MEMBERSHIP)
 *   - cc_caseload    (Supervision target_type=BUNK)
 *   - lt_team        (Supervision target_type=ROLE_IN_PROGRAM)
 *   - counselor_bunk (AssignmentGroupMembership role=author)
 *   - camper_bunk    (AssignmentGroupMembership role=subject)
 *
 * Reflects the server-side backdated-clamp invariant: if the user
 * picks a past start date, we display a yellow banner explaining that
 * historical content stays anchored to the prior assignment.
 */

const SUB_TABS = [
  { key: 'counselor_bunk', label: 'Counselor → Bunk' },
  { key: 'uh_counselor', label: 'Unit Head → Counselor' },
  { key: 'cc_caseload', label: 'Camper Care → Caseload' },
  { key: 'lt_team', label: 'Leadership → Team' },
  { key: 'camper_bunk', label: 'Camper → Bunk / Student → Grade' },
];

function todayIso() {
  return new Date().toISOString().split('T')[0];
}

function StatusPill({ row }) {
  const today = todayIso();
  const end = row.end_date;
  let label = 'Active';
  let cls = 'bg-emerald-100 text-emerald-800';
  if (!row.is_active) {
    label = end ? 'Recently ended' : 'Inactive';
    cls = 'bg-gray-200 text-gray-700';
  } else if (end && end >= today && end <= addDays(today, 7)) {
    label = 'Ending within 7d';
    cls = 'bg-amber-100 text-amber-800';
  } else if (row.start_date && row.start_date > today) {
    label = 'Future-dated';
    cls = 'bg-indigo-100 text-indigo-800';
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full ${cls}`}>{label}</span>
  );
}

function addDays(iso, n) {
  const d = new Date(iso);
  d.setDate(d.getDate() + n);
  return d.toISOString().split('T')[0];
}

function AssignmentRow({ row, onChanged }) {
  const [confirming, setConfirming] = useState(false);
  const [reason, setReason] = useState('');
  const handleEnd = async () => {
    if (!reason.trim()) return;
    await patchAdminAssignment(row.id, row.kind, {
      end_date: todayIso(),
      is_active: false,
      reason,
    });
    setConfirming(false);
    setReason('');
    onChanged();
  };
  const title = row.kind === 'supervision'
    ? `${row.supervisor_name || `Supervisor ${row.supervisor_membership_id}`} → ${supervisionTarget(row)}`
    : `${row.person_name || `Person ${row.person_id}`} ↔ ${row.group_name || `Group ${row.group_id}`}`;
  return (
    <li
      data-testid={`assignment-row-${row.kind}-${row.id}`}
      className="rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3 text-sm"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="font-medium">{title}</p>
        <StatusPill row={row} />
      </div>
      <p className="text-xs text-gray-500">
        {row.start_date || '—'} → {row.end_date || 'open'}
      </p>
      {row.is_active && !confirming && (
        <button
          type="button"
          data-testid={`assignment-end-${row.id}`}
          onClick={() => setConfirming(true)}
          className="mt-2 text-xs text-red-700 underline"
        >
          End assignment
        </button>
      )}
      {confirming && (
        <div className="mt-2 flex gap-2 items-center">
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reason"
            className="text-xs rounded-md border border-gray-300 p-1 flex-1"
          />
          <button
            type="button"
            disabled={!reason.trim()}
            onClick={handleEnd}
            className="text-xs px-2 py-1 rounded-md bg-red-600 text-white disabled:opacity-60"
          >
            Confirm end
          </button>
        </div>
      )}
    </li>
  );
}

function supervisionTarget(row) {
  if (row.target_type === 'membership') return `Membership ${row.target_membership_id}`;
  if (row.target_type === 'bunk') return `Bunk ${row.target_bunk_id}`;
  if (row.target_type === 'role_in_program') {
    return `${row.target_role} in Program ${row.target_program_id}`;
  }
  return 'Target';
}

function CreateForm({ subTab, onCreated }) {
  const [draft, setDraft] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    setResponse(null);
    try {
      const payload = { sub_tab: subTab, ...draft };
      const data = await createAdminAssignment(payload);
      setResponse(data);
      setDraft({});
      onCreated();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not create.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      data-testid="assignment-create-form"
      className="rounded-md border border-indigo-200 bg-indigo-50/40 dark:bg-indigo-900/10 p-3 space-y-2"
    >
      <p className="text-sm font-medium">New {subTab.replace('_', ' ')}</p>
      <p className="text-xs text-gray-600">Membership / group / person IDs are required. The
        backend clamps backdated <code>start_date</code> values to today; historical content is not retroactively reattributed.</p>
      {subTab === 'uh_counselor' && (
        <>
          <NumberField label="Supervisor membership ID" value={draft.supervisor_membership_id || ''} onChange={(v) => setDraft({ ...draft, supervisor_membership_id: v })} />
          <NumberField label="Target counselor membership ID" value={draft.target_membership_id || ''} onChange={(v) => setDraft({ ...draft, target_membership_id: v })} />
        </>
      )}
      {subTab === 'cc_caseload' && (
        <>
          <NumberField label="Supervisor (CC) membership ID" value={draft.supervisor_membership_id || ''} onChange={(v) => setDraft({ ...draft, supervisor_membership_id: v })} />
          <NumberField label="Target bunk (assignment group) ID" value={draft.target_bunk_id || ''} onChange={(v) => setDraft({ ...draft, target_bunk_id: v })} />
        </>
      )}
      {subTab === 'lt_team' && (
        <>
          <NumberField label="Supervisor (LT) membership ID" value={draft.supervisor_membership_id || ''} onChange={(v) => setDraft({ ...draft, supervisor_membership_id: v })} />
          <NumberField label="Target program ID" value={draft.target_program_id || ''} onChange={(v) => setDraft({ ...draft, target_program_id: v })} />
          <TextField label="Target role" value={draft.target_role || ''} onChange={(v) => setDraft({ ...draft, target_role: v })} />
        </>
      )}
      {(subTab === 'counselor_bunk' || subTab === 'camper_bunk') && (
        <>
          <NumberField label="Group (Bunk) ID" value={draft.group_id || ''} onChange={(v) => setDraft({ ...draft, group_id: v })} />
          <NumberField label="Person ID" value={draft.person_id || ''} onChange={(v) => setDraft({ ...draft, person_id: v })} />
        </>
      )}
      <TextField label="Start date (yyyy-mm-dd, optional — defaults to today)" value={draft.start_date || ''} onChange={(v) => setDraft({ ...draft, start_date: v })} />
      <TextField label="End date (optional)" value={draft.end_date || ''} onChange={(v) => setDraft({ ...draft, end_date: v })} />

      {error && <p className="text-sm text-red-700">{error}</p>}
      {response?.backdated_clamped && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-2 text-xs space-y-1" data-testid="backdated-warning">
          <p>Start date was backdated to {response.requested_start_date}; effective start clamped to today.</p>
          <p>Historical reflections / notes will remain anchored to the prior assignment.</p>
        </div>
      )}
      {response?.warnings?.length > 0 && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-2 text-xs" data-testid="assignment-warnings">
          <p className="font-medium">Conflicts on the same target:</p>
          <ul className="list-disc pl-4">
            {response.warnings.map((w) => (
              <li key={w.supervision_id}>{w.supervisor_name || `Membership ${w.supervisor_membership_id}`} ({w.kind})</li>
            ))}
          </ul>
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        data-testid="assignment-create-submit"
        className="px-3 py-1.5 rounded-md text-sm bg-indigo-600 text-white disabled:opacity-60"
      >
        {submitting ? 'Creating…' : 'Create assignment'}
      </button>
    </form>
  );
}

function NumberField({ label, value, onChange }) {
  return (
    <label className="block text-xs font-medium">
      {label}
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm bg-white"
      />
    </label>
  );
}

function TextField({ label, value, onChange }) {
  return (
    <label className="block text-xs font-medium">
      {label}
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm bg-white"
      />
    </label>
  );
}

export default function AdminAssignments() {
  const [subTab, setSubTab] = useState(SUB_TABS[0].key);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listAdminAssignments(subTab);
      setRows(data.results || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [subTab]);

  useEffect(() => { load(); }, [load]);

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-6xl mx-auto" data-testid="admin-assignments">
      <header className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Assignments</h1>
      </header>

      <nav className="border-b border-gray-200 dark:border-gray-700 flex gap-3 mb-4">
        {SUB_TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            data-testid={`assignment-sub-tab-${t.key}`}
            onClick={() => setSubTab(t.key)}
            className={`pb-2 -mb-px text-sm font-medium border-b-2 ${
              subTab === t.key
                ? 'border-indigo-500 text-indigo-700 dark:text-indigo-200'
                : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <section data-testid="assignment-list" className="space-y-2">
          {loading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : error ? (
            <p className="text-sm text-red-700">Could not load assignments.</p>
          ) : rows.length === 0 ? (
            <p className="text-sm italic text-gray-500">No assignments in this view.</p>
          ) : (
            <ul className="space-y-2">
              {rows.map((row) => (
                <AssignmentRow key={`${row.kind}-${row.id}`} row={row} onChanged={load} />
              ))}
            </ul>
          )}
        </section>
        <aside>
          <CreateForm subTab={subTab} onCreated={load} />
        </aside>
      </div>
    </main>
  );
}
