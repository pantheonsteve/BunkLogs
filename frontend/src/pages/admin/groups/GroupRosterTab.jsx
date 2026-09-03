import { useMemo, useState } from 'react';

import api from '../../../api';
import Button from '../../../components/ui/Button';
import BulkActionBar from '../../../components/ui/BulkActionBar';
import ConfirmDialog from '../../../components/ui/ConfirmDialog';
import DataTable from '../../../components/ui/DataTable';
import EmptyState from '../../../components/ui/EmptyState';
import OverflowMenu, { OverflowMenuItem } from '../../../components/ui/OverflowMenu';
import { profileLink } from '../../../utils/dashboardLinks';
import AddMembersModal from './AddMembersModal';

/**
 * One side of a group's roster: its subjects, or its authors.
 *
 * Both tabs are the same table over the same endpoint with a different
 * `role_in_group`, so they share this component rather than diverging.
 * Removing people is destructive and offers the softer alternative —
 * most "remove" clicks are someone leaving mid-season, which is an end
 * date on their membership, not an erasure of their history.
 */
function fullName(person) {
  const preferred = person.preferred_name && person.preferred_name !== person.first_name
    ? ` (${person.preferred_name})`
    : '';
  return `${person.first_name} ${person.last_name}${preferred}`;
}

export default function GroupRosterTab({
  group,
  roleInGroup,
  roleLabel,
  otherRoleLabel,
  emptyHint,
  onChanged,
  showToast,
}) {
  const [selected, setSelected] = useState(() => new Set());
  const [adding, setAdding] = useState(false);
  const [confirming, setConfirming] = useState(null);
  const [busy, setBusy] = useState(false);

  const members = useMemo(() => (
    (group.memberships || [])
      .filter((m) => m.is_active && m.role_in_group === roleInGroup)
      .sort((a, b) => (
        (a.person.last_name || '').localeCompare(b.person.last_name || '')
        || (a.person.first_name || '').localeCompare(b.person.first_name || '')
      ))
  ), [group.memberships, roleInGroup]);

  const existingPersonIds = useMemo(
    () => new Set(members.map((m) => m.person.id)),
    [members],
  );

  const addPerson = async (personId) => {
    await api.post(`/api/v1/assignment-groups/${group.id}/memberships/`, {
      person_id: personId,
      role_in_group: roleInGroup,
    });
  };

  const removeSelected = async () => {
    setBusy(true);
    const errors = [];
    for (const membershipId of selected) {
      try {
        await api.delete(`/api/v1/assignment-groups/${group.id}/memberships/${membershipId}/`);
      } catch (err) {
        errors.push(err?.response?.data?.detail || `Membership ${membershipId}`);
      }
    }
    setSelected(new Set());
    setBusy(false);
    setConfirming(null);
    await onChanged();
    showToast(errors.length ? errors.join('; ') : `Removed from ${group.name}.`);
  };

  const flipRole = async () => {
    const opposite = roleInGroup === 'subject' ? 'author' : 'subject';
    setBusy(true);
    const errors = [];
    for (const membershipId of selected) {
      const member = members.find((m) => m.id === membershipId);
      if (!member) continue;
      try {
        await api.post(`/api/v1/assignment-groups/${group.id}/memberships/`, {
          person_id: member.person.id,
          role_in_group: opposite,
        });
        await api.delete(`/api/v1/assignment-groups/${group.id}/memberships/${membershipId}/`);
      } catch (err) {
        errors.push(err?.response?.data?.detail || member.person.last_name);
      }
    }
    setSelected(new Set());
    setBusy(false);
    await onChanged();
    showToast(errors.length ? errors.join('; ') : `Moved to ${otherRoleLabel}.`);
  };

  const columns = [
    {
      key: 'name',
      header: 'Name',
      render: (m) => (
        <a
          href={profileLink(m.person.id)}
          onClick={(e) => e.stopPropagation()}
          className="font-medium text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400"
        >
          {fullName(m.person)}
        </a>
      ),
    },
    {
      key: 'since',
      header: 'Since',
      align: 'right',
      render: (m) => (
        <span className="text-xs text-gray-500 tabular-nums">{m.start_date || '—'}</span>
      ),
    },
  ];

  return (
    <div className="space-y-4" data-testid={`group-roster-${roleInGroup}`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {members.length} {members.length === 1 ? roleLabel.one : roleLabel.other}
        </p>
        <Button
          size="sm"
          onClick={() => setAdding(true)}
          data-testid={`group-add-${roleInGroup}`}
        >
          Add {roleLabel.other}
        </Button>
      </div>

      <BulkActionBar count={selected.size} onClear={() => setSelected(new Set())}>
        <Button
          size="sm"
          variant="secondary"
          onClick={flipRole}
          disabled={busy}
          data-testid={`group-${roleInGroup}-flip`}
        >
          Move to {otherRoleLabel}
        </Button>
        <OverflowMenu size="sm" label="More actions" triggerTestId={`group-${roleInGroup}-overflow`}>
          <OverflowMenuItem
            danger
            onClick={() => setConfirming('remove')}
            data-testid={`group-${roleInGroup}-remove`}
          >
            Remove {selected.size} from {group.name}…
          </OverflowMenuItem>
        </OverflowMenu>
      </BulkActionBar>

      <DataTable
        columns={columns}
        rows={members}
        rowTestId={(m) => `group-member-${m.id}`}
        selection={{
          selected,
          onToggle: (id) => setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
          }),
          onToggleAll: (checked) => setSelected(
            checked ? new Set(members.map((m) => m.id)) : new Set(),
          ),
        }}
        empty={<EmptyState title={`No ${roleLabel.other} yet`}>{emptyHint}</EmptyState>}
      />

      {adding && (
        <AddMembersModal
          title={`Add ${roleLabel.other} to ${group.name}`}
          roleInGroup={roleLabel.one}
          programId={group.program}
          existingPersonIds={existingPersonIds}
          onAdd={addPerson}
          onClose={() => setAdding(false)}
          onDone={async (count) => {
            setAdding(false);
            await onChanged();
            showToast(`Added ${count} ${count === 1 ? roleLabel.one : roleLabel.other}.`);
          }}
        />
      )}

      {confirming === 'remove' && (
        <ConfirmDialog
          title={`Remove ${selected.size} ${selected.size === 1 ? roleLabel.one : roleLabel.other} from ${group.name}?`}
          confirmLabel={`Remove ${selected.size}`}
          busy={busy}
          consequences={[
            `End their membership of ${group.name} today`,
            roleInGroup === 'author'
              ? 'Stop them writing new logs for this group'
              : 'Stop new logs being written about them here',
          ]}
          reassurance="Logs already written stay exactly where they are."
          onConfirm={removeSelected}
          onClose={() => setConfirming(null)}
        />
      )}
    </div>
  );
}
