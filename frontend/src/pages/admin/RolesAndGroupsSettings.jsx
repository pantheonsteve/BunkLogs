/**
 * Which roles this organization uses, and how each kind of group
 * places them. Labels come from terminology; the values saved are the
 * role and group-type slugs the API already understands.
 */
import { useMemo, useState } from 'react';

import { patchAdminSettings } from '../../api/admin';
import Button from '../../components/ui/Button';
import Card, { CardBody, CardHeader } from '../../components/ui/Card';
import Note from '../../components/ui/Note';
import { useTerm } from '../../context/OrgBrandingContext';
import { labeledRoles } from '../../utils/roleLabels';
import { GROUP_TYPE_LABELS, GROUP_TYPE_ORDER } from './groups/groupTypes';

function groupTypeName(type, term) {
  const fromTerm = term(type, { capitalize: true });
  if (fromTerm.toLowerCase() !== type) return fromTerm;
  return GROUP_TYPE_LABELS[type] || fromTerm;
}

function rowsFromMembers(members) {
  const byRole = new Map();
  for (const member of members || []) {
    const row = byRole.get(member.role) || {
      role: member.role,
      writes: false,
      about: false,
      supervises: false,
    };
    if (member.placed_as === 'author') row.writes = true;
    if (member.placed_as === 'subject') row.about = true;
    if (member.supervises_group) row.supervises = true;
    byRole.set(member.role, row);
  }
  return [...byRole.values()];
}

function membersFromRows(rows) {
  const members = [];
  for (const row of rows) {
    if (row.writes) {
      members.push({
        role: row.role,
        placed_as: 'author',
        supervises_group: Boolean(row.supervises),
      });
    }
    if (row.about) {
      members.push({
        role: row.role,
        placed_as: 'subject',
        supervises_group: Boolean(row.supervises) && !row.writes,
      });
    }
  }
  return members;
}

function initialGroups(config) {
  const state = {};
  for (const type of GROUP_TYPE_ORDER) {
    const cfg = config?.[type];
    state[type] = {
      enabled: Boolean(cfg?.enabled),
      rows: rowsFromMembers(cfg?.members),
    };
  }
  return state;
}

export default function RolesAndGroupsTab({ settings, onSaved }) {
  const term = useTerm();
  const catalog = settings.role_catalog || [];
  const superviseByRole = useMemo(() => {
    const map = {};
    for (const entry of catalog) map[entry.role] = Boolean(entry.can_supervise);
    return map;
  }, [catalog]);

  const [checked, setChecked] = useState(() => new Set(settings.enabled_roles || []));
  const [groups, setGroups] = useState(() => initialGroups(settings.group_type_config));
  const [roleError, setRoleError] = useState('');
  const [groupError, setGroupError] = useState('');
  const [savingRoles, setSavingRoles] = useState(false);
  const [savingGroups, setSavingGroups] = useState(false);

  const toggleRole = (role) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(role)) next.delete(role);
      else next.add(role);
      return next;
    });
  };

  const saveRoles = async () => {
    setSavingRoles(true);
    setRoleError('');
    const roles = catalog.map((entry) => entry.role).filter((role) => checked.has(role));
    try {
      const saved = await patchAdminSettings({ settings: { roles } });
      onSaved({
        settings: { ...(settings.settings || {}), ...(saved?.settings || {}), roles },
        enabled_roles: roles,
      });
    } catch (err) {
      setRoleError(err?.response?.data?.detail || 'Could not save roles.');
    } finally {
      setSavingRoles(false);
    }
  };

  const updateType = (type, patch) => {
    setGroups((prev) => ({ ...prev, [type]: { ...prev[type], ...patch } }));
  };

  const updateRow = (type, role, patch) => {
    setGroups((prev) => ({
      ...prev,
      [type]: {
        ...prev[type],
        rows: prev[type].rows.map((row) => (row.role === role ? { ...row, ...patch } : row)),
      },
    }));
  };

  const addRow = (type, role) => {
    if (!role) return;
    setGroups((prev) => {
      if (prev[type].rows.some((row) => row.role === role)) return prev;
      return {
        ...prev,
        [type]: {
          ...prev[type],
          rows: [...prev[type].rows, { role, writes: true, about: false, supervises: false }],
        },
      };
    });
  };

  const saveGroups = async () => {
    setSavingGroups(true);
    setGroupError('');
    const groupTypes = {};
    for (const type of GROUP_TYPE_ORDER) {
      const entry = groups[type];
      groupTypes[type] = {
        enabled: Boolean(entry?.enabled),
        members: membersFromRows(entry?.rows || []),
      };
    }
    try {
      const saved = await patchAdminSettings({ settings: { group_types: groupTypes } });
      onSaved({
        settings: { ...(settings.settings || {}), ...(saved?.settings || {}), group_types: groupTypes },
        group_type_config: groupTypes,
      });
    } catch (err) {
      setGroupError(err?.response?.data?.detail || 'Could not save groups.');
    } finally {
      setSavingGroups(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card data-testid="settings-roles-card">
        <CardHeader
          title="Roles"
          subtitle="People can only be given a role that is turned on."
        />
        <CardBody className="space-y-3">
          {catalog.length === 0 && (
            <p className="text-sm text-gray-500">Roles could not be loaded.</p>
          )}
          <ul className="space-y-2">
            {catalog.map((entry) => (
              <li key={entry.role}>
                <label className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={checked.has(entry.role)}
                    onChange={() => toggleRole(entry.role)}
                    data-testid={`settings-role-${entry.role}`}
                  />
                  <span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {term(entry.role, { capitalize: true })}
                    </span>
                    {entry.description && (
                      <span className="block text-xs text-gray-500 dark:text-gray-400">
                        {entry.description}
                      </span>
                    )}
                  </span>
                </label>
              </li>
            ))}
          </ul>
          {roleError && <Note tone="danger" data-testid="settings-roles-error">{roleError}</Note>}
          <div className="flex justify-end">
            <Button onClick={saveRoles} disabled={savingRoles} data-testid="settings-roles-save">
              {savingRoles ? 'Saving…' : 'Save roles'}
            </Button>
          </div>
        </CardBody>
      </Card>

      <Card data-testid="settings-groups-card">
        <CardHeader
          title="Groups"
          subtitle="For each kind of group, choose who can be added and what they do there."
        />
        <CardBody className="space-y-4">
          {GROUP_TYPE_ORDER.map((type) => {
            const entry = groups[type];
            if (!entry) return null;
            const used = new Set(entry.rows.map((row) => row.role));
            const available = [...checked].filter((role) => !used.has(role));
            const availableLabels = labeledRoles(available, term, catalog);
            return (
              <section key={type} className="rounded-md border border-gray-200 dark:border-gray-700 p-3 space-y-2" data-testid={`settings-group-type-${type}`}>
                <label className="flex items-center gap-2 text-sm font-medium">
                  <input
                    type="checkbox"
                    checked={entry.enabled}
                    onChange={(e) => updateType(type, { enabled: e.target.checked })}
                    data-testid={`settings-group-enabled-${type}`}
                  />
                  {groupTypeName(type, term)}
                </label>
                {entry.enabled && (
                  <div className="space-y-2 pl-6">
                    {entry.rows.map((row) => (
                      <div key={row.role} className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                        <span className="w-36 font-medium">{term(row.role, { capitalize: true })}</span>
                        <label className="flex items-center gap-1">
                          <input
                            type="checkbox"
                            checked={row.writes}
                            onChange={(e) => updateRow(type, row.role, { writes: e.target.checked })}
                          />
                          Writes
                        </label>
                        <label className="flex items-center gap-1">
                          <input
                            type="checkbox"
                            checked={row.about}
                            onChange={(e) => updateRow(type, row.role, { about: e.target.checked })}
                          />
                          Is written about
                        </label>
                        <label className="flex items-center gap-1">
                          <input
                            type="checkbox"
                            checked={row.supervises}
                            disabled={!superviseByRole[row.role]}
                            onChange={(e) => updateRow(type, row.role, { supervises: e.target.checked })}
                          />
                          Supervises
                        </label>
                      </div>
                    ))}
                    {available.length > 0 && (
                      <label className="block text-xs text-gray-600 dark:text-gray-300">
                        Add a role
                        <select
                          defaultValue=""
                          onChange={(e) => {
                            addRow(type, e.target.value);
                            e.target.value = '';
                          }}
                          className="mt-1 block rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
                          data-testid={`settings-group-add-role-${type}`}
                        >
                          <option value="">Choose…</option>
                          {available.map((role, index) => (
                            <option key={role} value={role}>{availableLabels[index]}</option>
                          ))}
                        </select>
                      </label>
                    )}
                  </div>
                )}
              </section>
            );
          })}
          {groupError && <Note tone="danger">{groupError}</Note>}
          <div className="flex justify-end">
            <Button onClick={saveGroups} disabled={savingGroups} data-testid="settings-groups-save">
              {savingGroups ? 'Saving…' : 'Save groups'}
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
