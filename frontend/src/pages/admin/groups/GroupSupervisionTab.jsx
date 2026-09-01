import { useCallback, useEffect, useMemo, useState } from 'react';

import api from '../../../api';
import {
  createAdminAssignment,
  listAdminAssignments,
  patchAdminAssignment,
} from '../../../api/admin';
import Badge from '../../../components/ui/Badge';
import BulkActionBar from '../../../components/ui/BulkActionBar';
import Button from '../../../components/ui/Button';
import ConfirmDialog from '../../../components/ui/ConfirmDialog';
import DataTable from '../../../components/ui/DataTable';
import EmptyState from '../../../components/ui/EmptyState';
import Modal from '../../../components/ui/Modal';
import Note from '../../../components/ui/Note';
import { useTerm } from '../../../context/OrgBrandingContext';
import { mergeMembershipPeople, parseListPayload } from './assignmentApiHelpers';

/**
 * Who supervises this group without being one of its authors.
 *
 * Camper care carries a caseload of bunks: they can see the group's logs
 * and act on flags, but they don't write the daily entry. That's a
 * `Supervision` row rather than a group membership, which is why it needs
 * its own tab instead of sitting alongside Staff.
 */
function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export default function GroupSupervisionTab({ group, onChanged, showToast }) {
  const term = useTerm();
  const [rows, setRows] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(() => new Set());
  const [adding, setAdding] = useState(false);
  const [picked, setPicked] = useState(() => new Set());
  const [busy, setBusy] = useState(false);
  const [confirmEnd, setConfirmEnd] = useState(false);

  const supervisorsCap = term('camper_care', { plural: true, capitalize: true });

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [assignments, memberships] = await Promise.all([
        listAdminAssignments({
          sub_tab: 'cc_caseload',
          program: group.program || undefined,
          status: 'active',
        }),
        api.get('/api/v1/memberships/', {
          params: {
            program: group.program,
            role: 'camper_care',
            is_active: true,
            page_size: 500,
          },
        }),
      ]);
      setRows((assignments.results || []).filter((r) => r.target_bunk_id === group.id));
      setCandidates([...mergeMembershipPeople(
        parseListPayload(memberships.data), 'camper_care',
      ).values()]);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not load supervision.');
    } finally {
      setLoading(false);
    }
  }, [group.id, group.program]);

  useEffect(() => { load(); }, [load]);

  const assignedPersonIds = useMemo(() => {
    const ids = new Set();
    for (const row of rows) {
      const match = candidates.find((c) => c.membershipId === row.supervisor_membership_id);
      if (match) ids.add(match.id);
    }
    return ids;
  }, [rows, candidates]);

  const addSupervisors = async () => {
    setBusy(true);
    const errors = [];
    for (const personId of picked) {
      const person = candidates.find((c) => c.id === personId);
      if (!person?.membershipId) continue;
      try {
        await createAdminAssignment({
          sub_tab: 'cc_caseload',
          supervisor_membership_id: person.membershipId,
          target_bunk_id: group.id,
          start_date: todayIso(),
        });
      } catch (err) {
        errors.push(err?.response?.data?.detail || person.full_name);
      }
    }
    setBusy(false);
    setPicked(new Set());
    setAdding(false);
    await load();
    onChanged?.();
    showToast(errors.length ? errors.join('; ') : 'Supervision added.');
  };

  const endSelected = async () => {
    setBusy(true);
    for (const id of selected) {
      const row = rows.find((r) => r.id === id);
      if (!row) continue;
      await patchAdminAssignment(row.id, row.kind, {
        end_date: todayIso(),
        is_active: false,
        reason: `Ended from ${group.name}.`,
      });
    }
    setSelected(new Set());
    setBusy(false);
    setConfirmEnd(false);
    await load();
    showToast('Supervision ended.');
  };

  const columns = [
    {
      key: 'name',
      header: 'Supervisor',
      render: (r) => (
        <span className="font-medium text-gray-900 dark:text-white">
          {r.supervisor_name || '—'}
        </span>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      render: (r) => <Badge tone="info">{(r.supervisor_role || '').replace(/_/g, ' ')}</Badge>,
    },
    {
      key: 'since',
      header: 'Since',
      align: 'right',
      render: (r) => (
        <span className="text-xs text-gray-500 tabular-nums">{r.start_date || '—'}</span>
      ),
    },
  ];

  if (loading) return <p className="text-sm text-gray-500">Loading supervision…</p>;

  return (
    <div className="space-y-4" data-testid="group-supervision-tab">
      {error && <Note tone="danger">{error}</Note>}

      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {supervisorsCap} who can see this {term('group')} without writing its logs.
        </p>
        <Button size="sm" onClick={() => setAdding(true)} data-testid="group-supervision-add">
          Add supervisor
        </Button>
      </div>

      <BulkActionBar count={selected.size} onClear={() => setSelected(new Set())}>
        <Button
          size="sm"
          variant="danger"
          onClick={() => setConfirmEnd(true)}
          data-testid="group-supervision-end"
        >
          End {selected.size} supervision{selected.size === 1 ? '' : 's'}
        </Button>
      </BulkActionBar>

      <DataTable
        columns={columns}
        rows={rows}
        rowTestId={(r) => `group-supervision-row-${r.id}`}
        selection={{
          selected,
          onToggle: (id) => setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
          }),
          onToggleAll: (checked) => setSelected(checked ? new Set(rows.map((r) => r.id)) : new Set()),
        }}
        empty={(
          <EmptyState title="Nobody supervises this group yet">
            Add a supervisor if someone needs to see these logs without writing them.
          </EmptyState>
        )}
      />

      {adding && (
        <Modal
          title={`Add supervisors to ${group.name}`}
          onClose={() => setAdding(false)}
          dismissible={!busy}
          data-testid="group-supervision-modal"
          footer={(
            <>
              <Button variant="secondary" onClick={() => setAdding(false)} disabled={busy}>
                Cancel
              </Button>
              <div className="flex-1" />
              <Button
                onClick={addSupervisors}
                disabled={busy || picked.size === 0}
                data-testid="group-supervision-confirm"
              >
                {busy ? 'Adding…' : `Add ${picked.size || ''}`.trim()}
              </Button>
            </>
          )}
        >
          {candidates.length === 0 ? (
            <Note tone="warn">
              Nobody in this program holds a {term('camper_care')} membership yet.
            </Note>
          ) : (
            <ul className="divide-y divide-gray-100 dark:divide-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              {candidates.map((c) => {
                const already = assignedPersonIds.has(c.id);
                return (
                  <li key={c.id}>
                    <label
                      className={`flex items-center gap-3 px-3 py-2 text-sm ${already ? 'opacity-50' : 'cursor-pointer'}`}
                      data-testid={`group-supervision-candidate-${c.id}`}
                    >
                      <input
                        type="checkbox"
                        disabled={already}
                        checked={picked.has(c.id)}
                        onChange={() => setPicked((prev) => {
                          const next = new Set(prev);
                          if (next.has(c.id)) next.delete(c.id);
                          else next.add(c.id);
                          return next;
                        })}
                        className="w-4 h-4 accent-blue-600"
                        aria-label={`Add ${c.full_name}`}
                      />
                      <span className="flex-1">{c.full_name}</span>
                      {already && <Badge tone="neutral">Already supervising</Badge>}
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </Modal>
      )}

      {confirmEnd && (
        <ConfirmDialog
          title={`End ${selected.size} supervision${selected.size === 1 ? '' : 's'} of ${group.name}?`}
          confirmLabel={`End ${selected.size}`}
          busy={busy}
          consequences={[
            'Set an end date of today on the supervision',
            `Remove this ${term('group')} from their caseload view`,
          ]}
          reassurance="Flags and notes they already wrote stay in place."
          onConfirm={endSelected}
          onClose={() => setConfirmEnd(false)}
        />
      )}
    </div>
  );
}
