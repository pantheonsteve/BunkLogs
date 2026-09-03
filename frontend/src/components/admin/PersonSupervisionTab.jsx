import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  createAdminAssignment,
  getAdminSupervisorStatus,
  listAdminAssignments,
  patchAdminAssignment,
} from '../../api/admin';
import Badge from '../ui/Badge';
import Button from '../ui/Button';
import ConfirmDialog from '../ui/ConfirmDialog';
import Note from '../ui/Note';
import { useAdminProgram } from '../../context/AdminProgramContext';

/**
 * Supervision, seen from one person rather than from a group.
 *
 * Two of the old Assignments sub-tabs had no group to live on: `lt_team`
 * (leadership supervises everyone holding a role in a program) and the
 * read-only supervisor-status inspector. Both are person-scoped, so they
 * belong on the person.
 */
const LT_TARGET_ROLES = [
  'counselor', 'unit_head', 'kitchen_staff', 'maintenance', 'camper_care',
];

function prettyRole(role) {
  return role.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function EntityList({ title, items }) {
  if (!items?.length) return null;
  return (
    <div>
      <h4 className="text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
        {title}
      </h4>
      <ul className="flex flex-wrap gap-1.5">
        {items.map((it) => (
          <li key={it.id ?? `${it.target_type}-${it.target_name}`}>
            <Badge tone="info">{it.name || it.target_name || '—'}</Badge>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function PersonSupervisionTab({ person }) {
  const { programId, program } = useAdminProgram();
  const [status, setStatus] = useState(null);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [addRole, setAddRole] = useState(LT_TARGET_ROLES[0]);
  const [busy, setBusy] = useState(false);
  const [ending, setEnding] = useState(null);

  const membershipIds = useMemo(
    () => new Set((person.memberships || []).map((m) => m.id)),
    [person.memberships],
  );
  const ltMembership = (person.memberships || []).find(
    (m) => m.role === 'leadership_team'
      && m.is_active
      && (!programId || String(m.program_id) === String(programId)),
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [statusData, assignments] = await Promise.all([
        getAdminSupervisorStatus(person.id),
        listAdminAssignments({
          sub_tab: 'lt_team',
          program: programId || undefined,
          status: 'active',
        }),
      ]);
      setStatus(statusData);
      setRows(
        (assignments.results || []).filter(
          (r) => membershipIds.has(r.supervisor_membership_id),
        ),
      );
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not load supervision.');
    } finally {
      setLoading(false);
    }
  }, [person.id, programId, membershipIds]);

  useEffect(() => { load(); }, [load]);

  const addSupervision = async () => {
    if (!ltMembership || !programId) return;
    setBusy(true);
    setError('');
    try {
      await createAdminAssignment({
        sub_tab: 'lt_team',
        supervisor_membership_id: ltMembership.id,
        target_program_id: Number(programId),
        target_role: addRole,
        start_date: todayIso(),
      });
      await load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not add supervision.');
    } finally {
      setBusy(false);
    }
  };

  const endSupervision = async () => {
    setBusy(true);
    try {
      await patchAdminAssignment(ending.id, ending.kind, {
        end_date: todayIso(),
        is_active: false,
        reason: 'Ended from the person profile.',
      });
      setEnding(null);
      await load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not end supervision.');
      setBusy(false);
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500" data-testid="supervision-loading">Loading supervision…</p>;
  }

  const entities = status?.supervised_entities || {};
  const hasEntities = ['units', 'bunks', 'teams', 'supervisions']
    .some((k) => entities[k]?.length);

  return (
    <div className="space-y-4" data-testid="person-supervision-tab">
      {error && <Note tone="danger">{error}</Note>}

      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={status?.is_supervisor ? 'ok' : 'neutral'} dot>
          {status?.is_supervisor ? 'Supervisor' : 'Not a supervisor'}
        </Badge>
        <Badge tone={status?.can_view_reflections ? 'ok' : 'neutral'} dot>
          {status?.can_view_reflections
            ? 'Can view others’ reflections'
            : 'No reflection visibility'}
        </Badge>
        <Badge tone="neutral">
          Supervises {status?.supervised_people?.count ?? 0} people
        </Badge>
      </div>

      {hasEntities ? (
        <div className="space-y-3">
          <EntityList title="Units" items={entities.units} />
          <EntityList title="Bunks" items={entities.bunks} />
          <EntityList title="Teams" items={entities.teams} />
          <EntityList title="Supervision rows" items={entities.supervisions} />
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Nothing supervised yet.
        </p>
      )}

      <div>
        <h4 className="text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
          Supervision by role{program ? ` · ${program.name}` : ''}
        </h4>
        {rows.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            No role-wide supervision in this program.
          </p>
        ) : (
          <ul className="divide-y divide-gray-100 dark:divide-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            {rows.map((row) => (
              <li
                key={row.id}
                data-testid={`supervision-row-${row.id}`}
                className="flex items-center justify-between gap-2 px-3 py-2 text-sm"
              >
                <span className="text-gray-800 dark:text-gray-200">
                  {prettyRole(row.target_role || '')}
                  {row.target_program_name && (
                    <span className="text-xs text-gray-500 ml-2">{row.target_program_name}</span>
                  )}
                </span>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => setEnding(row)}
                  data-testid={`supervision-end-${row.id}`}
                >
                  End
                </Button>
              </li>
            ))}
          </ul>
        )}

        {ltMembership && programId && (
          <div className="mt-2 flex items-center gap-2">
            <select
              value={addRole}
              onChange={(e) => setAddRole(e.target.value)}
              data-testid="supervision-add-role"
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm"
            >
              {LT_TARGET_ROLES.map((r) => (
                <option key={r} value={r}>{prettyRole(r)}</option>
              ))}
            </select>
            <Button
              size="sm"
              onClick={addSupervision}
              disabled={busy}
              data-testid="supervision-add"
            >
              Add supervision
            </Button>
          </div>
        )}
      </div>

      {ending && (
        <ConfirmDialog
          title={`End supervision of ${prettyRole(ending.target_role || '')}?`}
          description={`${person.full_name} will stop supervising everyone holding this role.`}
          confirmLabel="End supervision"
          busy={busy}
          consequences={[
            'Set an end date of today on this supervision row',
            'Remove reflection visibility for people in that role',
          ]}
          reassurance="Nothing already written is deleted, and the row stays in history."
          onConfirm={endSupervision}
          onClose={() => setEnding(null)}
        />
      )}
    </div>
  );
}
