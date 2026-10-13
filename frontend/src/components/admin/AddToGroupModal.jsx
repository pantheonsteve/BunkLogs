/**
 * Place someone in a group from their profile.
 *
 * The group type decides the placement. We only ask when their role
 * can sit in that group more than one way (a madrich who both writes
 * and is written about).
 */
import { useEffect, useMemo, useState } from 'react';

import api from '../../api';
import Button from '../ui/Button';
import Modal from '../ui/Modal';
import Note from '../ui/Note';
import { useTerm } from '../../context/OrgBrandingContext';
import { GROUP_TYPE_LABELS } from '../../pages/admin/groups/groupTypes';

const SUBJECT_ROLES = ['camper', 'student'];

function typeName(type, term) {
  const fromTerm = term(type, { capitalize: true });
  if (fromTerm.toLowerCase() !== type) return fromTerm;
  return GROUP_TYPE_LABELS[type] || fromTerm;
}

function placementsFor(person, group, config) {
  const roles = new Set(
    (person.memberships || []).filter((m) => m.is_active).map((m) => m.role),
  );
  const typeConfig = config?.[group.group_type];
  if (typeConfig?.enabled && typeConfig.members?.length) {
    return typeConfig.members.filter((member) => roles.has(member.role));
  }
  const placedAs = [...roles].some((role) => SUBJECT_ROLES.includes(role)) ? 'subject' : 'author';
  const role = [...roles][0];
  return role ? [{ role, placed_as: placedAs, supervises_group: false }] : [];
}

export default function AddToGroupModal({ person, onClose, onAdded }) {
  const term = useTerm();
  const [groups, setGroups] = useState([]);
  const [query, setQuery] = useState('');
  const [groupId, setGroupId] = useState('');
  const [placementKey, setPlacementKey] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.get('/api/v1/assignment-groups/', { params: { is_active: 'true' } })
      .then(({ data }) => {
        if (cancelled) return;
        const rows = Array.isArray(data) ? data : (data.results || []);
        setGroups(rows);
      })
      .catch(() => {
        if (!cancelled) setError('Could not load groups.');
      });
    return () => { cancelled = true; };
  }, []);

  const alreadyIn = useMemo(
    () => new Set((person.group_memberships || []).map((g) => g.group_id)),
    [person.group_memberships],
  );
  const choices = groups.filter((group) => {
    if (alreadyIn.has(group.id)) return false;
    if (!query.trim()) return true;
    return (group.name || '').toLowerCase().includes(query.trim().toLowerCase());
  }).slice(0, 30);

  const selected = groups.find((group) => String(group.id) === String(groupId));
  const placements = selected
    ? placementsFor(person, selected, person.group_type_config)
    : [];

  const save = async (placedAs) => {
    if (!selected) return;
    setSaving(true);
    setError('');
    try {
      await api.post(`/api/v1/assignment-groups/${selected.id}/memberships/`, {
        person_id: person.id,
        role_in_group: placedAs,
      });
      onAdded();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not add them to that group.');
      setSaving(false);
    }
  };

  const confirm = () => {
    if (placements.length === 1) {
      save(placements[0].placed_as);
      return;
    }
    const chosen = placements.find((member, index) => `${member.role}:${member.placed_as}:${index}` === placementKey);
    if (!chosen) {
      setError('Choose how they sit in this group.');
      return;
    }
    save(chosen.placed_as);
  };

  return (
    <Modal
      title={`Add ${person.full_name || 'this person'} to a group`}
      onClose={onClose}
      dismissible={!saving}
      data-testid="add-to-group-modal"
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button>
          <div className="flex-1" />
          <Button onClick={confirm} disabled={saving || !selected || placements.length === 0} data-testid="add-to-group-save">
            {saving ? 'Adding…' : 'Add to group'}
          </Button>
        </>
      )}
    >
      <div className="space-y-3">
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
          Group
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search groups…"
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
            data-testid="add-to-group-search"
          />
        </label>
        <select
          value={groupId}
          onChange={(e) => {
            setGroupId(e.target.value);
            setPlacementKey('');
            setError('');
          }}
          size={6}
          className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
          data-testid="add-to-group-list"
        >
          {choices.map((group) => (
            <option key={group.id} value={group.id}>
              {group.name} · {typeName(group.group_type, term)}
            </option>
          ))}
        </select>
        {selected && placements.length === 0 && (
          <Note tone="warn">
            Their role is not set up for a {typeName(selected.group_type, term).toLowerCase()}.
            Turn it on under Settings, then try again.
          </Note>
        )}
        {selected && placements.length === 1 && (
          <p className="text-sm text-gray-600 dark:text-gray-300" data-testid="add-to-group-placement">
            They will be added as someone who {placements[0].placed_as === 'author' ? 'writes' : 'is written about'}.
          </p>
        )}
        {selected && placements.length > 1 && (
          <fieldset className="space-y-1" data-testid="add-to-group-choices">
            <legend className="text-xs font-medium text-gray-700 dark:text-gray-300">How do they sit in this group?</legend>
            {placements.map((member, index) => {
              const key = `${member.role}:${member.placed_as}:${index}`;
              const words = member.placed_as === 'author' ? 'Writes' : 'Is written about';
              return (
                <label key={key} className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="placement"
                    checked={placementKey === key}
                    onChange={() => setPlacementKey(key)}
                  />
                  {term(member.role, { capitalize: true })} · {words}
                </label>
              );
            })}
          </fieldset>
        )}
        {error && <Note tone="danger">{error}</Note>}
      </div>
    </Modal>
  );
}
