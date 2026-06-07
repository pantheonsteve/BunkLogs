import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import api from '../../../api';
import {
  createAdminAssignment,
  listAdminAssignments,
  patchAdminAssignment,
} from '../../../api/admin';
import GroupDisplayName from '../../../components/GroupDisplayName';
import AssignmentFilterBar from './AssignmentFilterBar';
import { parseListPayload, mergeMembershipPeople } from './assignmentApiHelpers';
import { programQueryParam } from './assignmentProgramRef';
import GroupTile, { todayIso } from './GroupTile';
import PeopleAssignPane from './PeopleAssignPane';

export default function GroupMembershipTab({ config, programs }) {
  const [programId, setProgramId] = useState('');
  const [status, setStatus] = useState('active');
  const [search, setSearch] = useState('');
  const [groups, setGroups] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [people, setPeople] = useState([]);
  const [selectedGroupId, setSelectedGroupId] = useState(null);
  const [groupSearch, setGroupSearch] = useState('');
  const [selectedPersonIds, setSelectedPersonIds] = useState(new Set());
  const [selectedAssignmentIds, setSelectedAssignmentIds] = useState(new Set());
  const [startDate, setStartDate] = useState(todayIso());
  const [endDate, setEndDate] = useState('');
  const [assigning, setAssigning] = useState(false);
  const [highlightPeople, setHighlightPeople] = useState(false);
  const [banner, setBanner] = useState(null);
  const [loading, setLoading] = useState(true);
  const loadSeq = useRef(0);

  const programRef = programQueryParam(programId, programs);

  const loadGroups = useCallback(async () => {
    const seq = ++loadSeq.current;
    const params = { is_active: 'true', page_size: 500 };
    if (programRef) params.program = programRef;
    const responses = await Promise.all(
      config.groupTypes.map((gt) => api.get('/api/v1/assignment-groups/', {
        params: { ...params, group_type: gt },
      })),
    );
    if (seq !== loadSeq.current) return;
    const merged = responses.flatMap((r) => parseListPayload(r.data));
    setGroups(merged.sort((a, b) => a.name.localeCompare(b.name)));
  }, [config.groupTypes, programRef]);

  const loadAssignments = useCallback(async () => {
    const data = await listAdminAssignments({
      sub_tab: config.key,
      program: programId || undefined,
      status,
      search: search || undefined,
    });
    setAssignments(data.results || []);
  }, [config.key, programId, status, search]);

  const loadPeople = useCallback(async () => {
    if (!programRef) {
      setPeople([]);
      return;
    }
    const roleQueries = await Promise.all(
      config.eligibleRoles.map((role) => api.get('/api/v1/memberships/', {
        params: {
          program: programRef,
          role,
          is_active: true,
          page_size: 500,
        },
      })),
    );
    const byPerson = new Map();
    roleQueries.forEach((resp, idx) => {
      const role = config.eligibleRoles[idx];
      const list = parseListPayload(resp.data);
      for (const [personId, entry] of mergeMembershipPeople(list, role)) {
        const existing = byPerson.get(personId);
        if (!existing) {
          byPerson.set(personId, entry);
          continue;
        }
        for (const r of entry.roles) {
          if (!existing.roles.includes(r)) existing.roles.push(r);
        }
      }
    });
    setPeople([...byPerson.values()].sort((a, b) => a.last_name.localeCompare(b.last_name)));
  }, [config.eligibleRoles, programRef]);

  useEffect(() => {
    setSelectedGroupId(null);
    setSelectedPersonIds(new Set());
    setSelectedAssignmentIds(new Set());
    setLoading(true);
    Promise.all([loadGroups(), loadAssignments(), loadPeople()])
      .finally(() => setLoading(false));
  }, [loadGroups, loadAssignments, loadPeople]);

  const selectedProgram = programs.find((p) => String(p.id) === String(programId));

  const filteredGroups = useMemo(() => {
    const q = groupSearch.trim().toLowerCase();
    if (!q) return groups;
    return groups.filter((g) => (
      `${g.name} ${g.program_name || ''} ${g.parent_name || ''}`.toLowerCase().includes(q)
    ));
  }, [groups, groupSearch]);

  const selectedGroup = groups.find((g) => g.id === selectedGroupId) || null;

  const groupAssignments = useMemo(() => {
    if (!selectedGroupId) return [];
    return assignments.filter((a) => a.group_id === selectedGroupId);
  }, [assignments, selectedGroupId]);

  const disabledPersonIds = useMemo(() => {
    const ids = new Set();
    groupAssignments.forEach((a) => {
      if (a.is_active && a.person_id) ids.add(a.person_id);
    });
    return ids;
  }, [groupAssignments]);

  const togglePerson = (id) => {
    setSelectedPersonIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAllPeople = (checked) => {
    if (!checked) {
      setSelectedPersonIds(new Set());
      return;
    }
    setSelectedPersonIds(new Set(
      people.filter((p) => !disabledPersonIds.has(p.id)).map((p) => p.id),
    ));
  };

  const toggleAssignment = (id) => {
    setSelectedAssignmentIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAllAssignments = (checked) => {
    if (!checked) {
      setSelectedAssignmentIds(new Set());
      return;
    }
    setSelectedAssignmentIds(new Set(
      groupAssignments.filter((a) => a.is_active).map((a) => a.id),
    ));
  };

  const handleBulkAssign = async () => {
    if (!selectedGroupId || selectedPersonIds.size === 0) return;
    setAssigning(true);
    setBanner(null);
    const errors = [];
    let clamped = false;
    for (const personId of selectedPersonIds) {
      try {
        const resp = await createAdminAssignment({
          sub_tab: config.key,
          group_id: selectedGroupId,
          person_id: personId,
          start_date: startDate || undefined,
          end_date: endDate || undefined,
        });
        if (resp?.backdated_clamped) clamped = true;
      } catch (err) {
        errors.push(err?.response?.data?.detail || `Person ${personId}`);
      }
    }
    setAssigning(false);
    setSelectedPersonIds(new Set());
    await loadAssignments();
    if (errors.length) {
      setBanner({ type: 'error', message: errors.join('; ') });
    } else if (clamped) {
      setBanner({ type: 'warn', message: 'Some start dates were clamped to today (backdated safety).' });
    }
  };

  const handleEndSelected = async (reason) => {
    const rows = groupAssignments.filter((a) => selectedAssignmentIds.has(a.id));
    for (const row of rows) {
      await patchAdminAssignment(row.id, row.kind, {
        end_date: todayIso(),
        is_active: false,
        reason,
      });
    }
    setSelectedAssignmentIds(new Set());
    await loadAssignments();
  };

  const focusAssign = () => {
    setHighlightPeople(true);
    setTimeout(() => setHighlightPeople(false), 2000);
  };

  return (
    <div className="space-y-4">
      <AssignmentFilterBar
        programs={programs}
        programId={programId}
        onProgramChange={setProgramId}
        status={status}
        onStatusChange={setStatus}
        search={search}
        onSearchChange={setSearch}
      />

      {banner && (
        <div
          className={`rounded-md border p-2 text-sm ${
            banner.type === 'error'
              ? 'border-red-300 bg-red-50 text-red-800'
              : 'border-amber-300 bg-amber-50 text-amber-900'
          }`}
        >
          {banner.message}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-3 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
              {config.leftLabel}
            </h2>
            <input
              type="search"
              value={groupSearch}
              onChange={(e) => setGroupSearch(e.target.value)}
              placeholder={`Filter ${config.leftLabel.toLowerCase()}…`}
              className="text-sm rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 bg-white dark:bg-gray-800 w-40"
            />
          </div>
          {loading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : filteredGroups.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400 py-4" data-testid="assignment-group-empty">
              {programId
                ? `No ${config.leftLabel.toLowerCase()} found for ${selectedProgram?.name || 'this program'}.`
                : `No ${config.leftLabel.toLowerCase()} found.`}
            </p>
          ) : (
            <ul className="max-h-96 overflow-y-auto space-y-1" data-testid="assignment-group-list">
              {filteredGroups.map((g) => (
                <li key={g.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedGroupId(g.id);
                      setSelectedAssignmentIds(new Set());
                      setSelectedPersonIds(new Set());
                    }}
                    className={[
                      'w-full text-left rounded-lg px-3 py-2 text-sm transition-colors',
                      selectedGroupId === g.id
                        ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-900 dark:text-indigo-100 font-medium'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-800 dark:text-gray-200',
                    ].join(' ')}
                  >
                    <GroupDisplayName
                      group={g}
                      nameClassName="block font-medium"
                      subtitleClassName="block text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5"
                    />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <PeopleAssignPane
          people={people}
          emptyMessage={
            programId
              ? `No ${config.eligibleRoles.join(', ').replace(/_/g, ' ')} with an active membership in ${selectedProgram?.name || 'this program'}.`
              : 'Select a program to see eligible people.'
          }
          selectedIds={selectedPersonIds}
          onToggle={togglePerson}
          onToggleAll={toggleAllPeople}
          disabledIds={disabledPersonIds}
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
          onAssign={handleBulkAssign}
          assigning={assigning}
          highlighted={highlightPeople}
        />
      </div>

      {selectedGroup && (
        <GroupTile
          title={selectedGroup.name}
          subtitle={[
            selectedGroup.program_name,
            selectedGroup.parent_name,
          ].filter(Boolean).join(' · ') || config.subtitle}
          assignments={groupAssignments}
          selectedAssignmentIds={selectedAssignmentIds}
          onToggleAssignment={toggleAssignment}
          onToggleAllAssignments={toggleAllAssignments}
          onEndSelected={handleEndSelected}
          onAssignPerson={focusAssign}
          dimEnded={status === 'all'}
        />
      )}
    </div>
  );
}
