import { useCallback, useEffect, useMemo, useState } from 'react';
import api from '../../../api';
import {
  createAdminAssignment,
  listAdminAssignments,
  patchAdminAssignment,
} from '../../../api/admin';
import { parseListPayload, personFromMembership, mergeMembershipPeople } from './assignmentApiHelpers';
import AssignmentFilterBar from './AssignmentFilterBar';
import { programQueryParam } from './assignmentProgramRef';
import GroupTile, { todayIso } from './GroupTile';
import PeopleAssignPane from './PeopleAssignPane';

function prettyRole(role) {
  return role.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

export default function SupervisionTab({ config, programs }) {
  const [programId, setProgramId] = useState('');
  const [status, setStatus] = useState('active');
  const [search, setSearch] = useState('');
  const [assignments, setAssignments] = useState([]);
  const [leftItems, setLeftItems] = useState([]);
  const [supervisors, setSupervisors] = useState([]);
  const [selectedLeftKey, setSelectedLeftKey] = useState(null);
  const [selectedSupervisorIds, setSelectedSupervisorIds] = useState(new Set());
  const [selectedAssignmentIds, setSelectedAssignmentIds] = useState(new Set());
  const [startDate, setStartDate] = useState(todayIso());
  const [endDate, setEndDate] = useState('');
  const [assigning, setAssigning] = useState(false);
  const [highlightPeople, setHighlightPeople] = useState(false);
  const [banner, setBanner] = useState(null);
  const [loading, setLoading] = useState(true);
  const [leftSearch, setLeftSearch] = useState('');

  const programRef = programQueryParam(programId, programs);

  const loadAssignments = useCallback(async () => {
    const data = await listAdminAssignments({
      sub_tab: config.key,
      program: programId || undefined,
      status,
      search: search || undefined,
    });
    setAssignments(data.results || []);
  }, [config.key, programId, status, search]);

  const loadLeftAndSupervisors = useCallback(async () => {
    if (config.key === 'uh_counselor') {
      if (!programId) {
        setLeftItems([]);
        setSupervisors([]);
        return;
      }
      const [uhResp, counselorResp] = await Promise.all([
        api.get('/api/v1/memberships/', {
          params: { program: programRef, role: 'unit_head', is_active: true, page_size: 500 },
        }),
        api.get('/api/v1/memberships/', {
          params: {
            program: programRef,
            role: config.targetRoles[0],
            is_active: true,
            page_size: 500,
          },
        }),
      ]);
      const uhs = parseListPayload(uhResp.data).map((m) => {
        const person = personFromMembership(m);
        return {
          key: `uh-${m.id}`,
          membershipId: m.id,
          label: person?.full_name || m.person_name || 'Unit head',
          subtitle: 'Unit head',
        };
      });
      setLeftItems(uhs);
      const counselors = new Map();
      for (const [personId, entry] of mergeMembershipPeople(
        parseListPayload(counselorResp.data),
        config.targetRoles[0],
      )) {
        counselors.set(personId, entry);
      }
      for (const role of config.targetRoles.slice(1)) {
        const { data } = await api.get('/api/v1/memberships/', {
          params: { program: programRef, role, is_active: true, page_size: 500 },
        });
        for (const [personId, entry] of mergeMembershipPeople(parseListPayload(data), role)) {
          const existing = counselors.get(personId);
          if (!existing) {
            counselors.set(personId, entry);
            continue;
          }
          for (const r of entry.roles) {
            if (!existing.roles.includes(r)) existing.roles.push(r);
          }
        }
      }
      setSupervisors([...counselors.values()]);
      return;
    }

    if (config.key === 'cc_caseload') {
      const params = { is_active: 'true', group_type: 'bunk', page_size: 500 };
      if (programRef) params.program = programRef;
      const { data } = await api.get('/api/v1/assignment-groups/', { params });
      const list = parseListPayload(data);
      setLeftItems(list.map((g) => ({
        key: `bunk-${g.id}`,
        bunkId: g.id,
        label: g.name,
        subtitle: [g.program_name, g.parent_name || 'Bunk'].filter(Boolean).join(' · '),
        programName: g.program_name,
      })));
      if (!programId) {
        setSupervisors([]);
        return;
      }
      const ccResp = await api.get('/api/v1/memberships/', {
        params: { program: programRef, role: 'camper_care', is_active: true, page_size: 500 },
      });
      setSupervisors([...mergeMembershipPeople(parseListPayload(ccResp.data), 'camper_care').values()]);
      return;
    }

    if (config.key === 'lt_team') {
      if (!programId) {
        setLeftItems([]);
        setSupervisors([]);
        return;
      }
      setLeftItems(config.targetRoleOptions.map((role) => ({
        key: `role-${role}`,
        role,
        programId: Number(programId),
        label: prettyRole(role),
        subtitle: programs.find((p) => String(p.id) === String(programId))?.name,
      })));
      const ltResp = await api.get('/api/v1/memberships/', {
        params: { program: programRef, role: 'leadership_team', is_active: true, page_size: 500 },
      });
      setSupervisors([...mergeMembershipPeople(parseListPayload(ltResp.data), 'leadership_team').values()]);
    }
  }, [config, programId, programRef, programs]);

  useEffect(() => {
    setLoading(true);
    Promise.all([loadAssignments(), loadLeftAndSupervisors()])
      .finally(() => setLoading(false));
  }, [loadAssignments, loadLeftAndSupervisors]);

  const filteredLeft = useMemo(() => {
    const q = leftSearch.trim().toLowerCase();
    if (!q) return leftItems;
    return leftItems.filter((item) => item.label.toLowerCase().includes(q));
  }, [leftItems, leftSearch]);

  const selectedLeft = leftItems.find((i) => i.key === selectedLeftKey) || null;

  const visibleAssignments = useMemo(() => {
    if (!selectedLeft) return [];
    if (config.key === 'uh_counselor') {
      return assignments.filter((a) => a.supervisor_membership_id === selectedLeft.membershipId);
    }
    if (config.key === 'cc_caseload') {
      return assignments.filter((a) => a.target_bunk_id === selectedLeft.bunkId);
    }
    if (config.key === 'lt_team') {
      return assignments.filter(
        (a) => a.target_program_id === selectedLeft.programId
          && a.target_role === selectedLeft.role,
      );
    }
    return [];
  }, [assignments, selectedLeft, config.key]);

  const disabledSupervisorIds = useMemo(() => {
    const ids = new Set();
    if (!selectedLeft) return ids;
    visibleAssignments.forEach((a) => {
      if (!a.is_active) return;
      if (config.key === 'uh_counselor' && a.target_membership_id) {
        const counselor = supervisors.find((s) => s.membershipId === a.target_membership_id);
        if (counselor?.id) ids.add(counselor.id);
      } else if (a.supervisor_membership_id) {
        const sup = supervisors.find((s) => s.membershipId === a.supervisor_membership_id);
        if (sup?.id) ids.add(sup.id);
      }
    });
    return ids;
  }, [visibleAssignments, selectedLeft, supervisors, config.key]);

  const toggleSupervisor = (id) => {
    setSelectedSupervisorIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAllSupervisors = (checked) => {
    if (!checked) {
      setSelectedSupervisorIds(new Set());
      return;
    }
    setSelectedSupervisorIds(new Set(
      supervisors.filter((p) => !disabledSupervisorIds.has(p.id)).map((p) => p.id),
    ));
  };

  const handleBulkAssignFixed = async () => {
    if (!selectedLeft || selectedSupervisorIds.size === 0) return;
    setAssigning(true);
    setBanner(null);
    const errors = [];
    let anyWarnings = false;
    let clamped = false;

    if (config.key === 'uh_counselor') {
      for (const counselorId of selectedSupervisorIds) {
        const counselor = supervisors.find((s) => s.id === counselorId);
        if (!counselor?.membershipId) continue;
        try {
          const resp = await createAdminAssignment({
            sub_tab: config.key,
            supervisor_membership_id: selectedLeft.membershipId,
            target_membership_id: counselor.membershipId,
            start_date: startDate || undefined,
            end_date: endDate || undefined,
          });
          if (resp?.backdated_clamped) clamped = true;
          if (resp?.warnings?.length) anyWarnings = true;
        } catch (err) {
          errors.push(err?.response?.data?.detail || counselor.full_name);
        }
      }
    } else if (config.key === 'cc_caseload') {
      for (const ccId of selectedSupervisorIds) {
        const cc = supervisors.find((s) => s.id === ccId);
        if (!cc?.membershipId) continue;
        try {
          const resp = await createAdminAssignment({
            sub_tab: config.key,
            supervisor_membership_id: cc.membershipId,
            target_bunk_id: selectedLeft.bunkId,
            start_date: startDate || undefined,
            end_date: endDate || undefined,
          });
          if (resp?.backdated_clamped) clamped = true;
          if (resp?.warnings?.length) anyWarnings = true;
        } catch (err) {
          errors.push(err?.response?.data?.detail || cc.full_name);
        }
      }
    } else if (config.key === 'lt_team') {
      for (const ltId of selectedSupervisorIds) {
        const lt = supervisors.find((s) => s.id === ltId);
        if (!lt?.membershipId) continue;
        try {
          const resp = await createAdminAssignment({
            sub_tab: config.key,
            supervisor_membership_id: lt.membershipId,
            target_program_id: selectedLeft.programId,
            target_role: selectedLeft.role,
            start_date: startDate || undefined,
            end_date: endDate || undefined,
          });
          if (resp?.backdated_clamped) clamped = true;
          if (resp?.warnings?.length) anyWarnings = true;
        } catch (err) {
          errors.push(err?.response?.data?.detail || lt.full_name);
        }
      }
    }

    setAssigning(false);
    setSelectedSupervisorIds(new Set());
    await loadAssignments();
    if (errors.length) {
      setBanner({ type: 'error', message: errors.join('; ') });
    } else if (anyWarnings) {
      setBanner({ type: 'warn', message: 'Co-supervision warnings returned — review assignments.' });
    } else if (clamped) {
      setBanner({ type: 'warn', message: 'Some start dates were clamped to today.' });
    }
  };

  const rightPaneLabel = config.key === 'uh_counselor'
    ? 'Counselors to supervise'
    : config.key === 'cc_caseload'
      ? 'Camper care staff'
      : 'Leadership team';

  const handleEndSelected = async (reason) => {
    const rows = visibleAssignments.filter((a) => selectedAssignmentIds.has(a.id));
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

  return (
    <div className="space-y-4">
      <AssignmentFilterBar
        programs={programs}
        programId={programId}
        onProgramChange={(v) => {
          setProgramId(v);
          setSelectedLeftKey(null);
        }}
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
              value={leftSearch}
              onChange={(e) => setLeftSearch(e.target.value)}
              placeholder="Filter…"
              className="text-sm rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 bg-white dark:bg-gray-800 w-40"
            />
          </div>
          {loading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : (
            <ul className="max-h-96 overflow-y-auto space-y-1">
              {filteredLeft.map((item) => (
                <li key={item.key}>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedLeftKey(item.key);
                      setSelectedAssignmentIds(new Set());
                      setSelectedSupervisorIds(new Set());
                    }}
                    className={[
                      'w-full text-left rounded-lg px-3 py-2 text-sm transition-colors',
                      selectedLeftKey === item.key
                        ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-900 dark:text-indigo-100 font-medium'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-800 dark:text-gray-200',
                    ].join(' ')}
                  >
                    <span>{item.label}</span>
                    {item.subtitle && (
                      <span className="block text-xs text-gray-500 truncate">{item.subtitle}</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <PeopleAssignPane
          people={supervisors}
          selectedIds={selectedSupervisorIds}
          onToggle={toggleSupervisor}
          onToggleAll={toggleAllSupervisors}
          disabledIds={disabledSupervisorIds}
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
          onAssign={handleBulkAssignFixed}
          assigning={assigning}
          assignLabel="Assign selected"
          highlighted={highlightPeople}
        />
      </div>

      {selectedLeft && (
        <GroupTile
          title={selectedLeft.label}
          subtitle={selectedLeft.subtitle || config.subtitle}
          assignments={visibleAssignments}
          selectedAssignmentIds={selectedAssignmentIds}
          onToggleAssignment={(id) => {
            setSelectedAssignmentIds((prev) => {
              const next = new Set(prev);
              if (next.has(id)) next.delete(id);
              else next.add(id);
              return next;
            });
          }}
          onToggleAllAssignments={(checked) => {
            if (!checked) setSelectedAssignmentIds(new Set());
            else {
              setSelectedAssignmentIds(new Set(
                visibleAssignments.filter((a) => a.is_active).map((a) => a.id),
              ));
            }
          }}
          onEndSelected={handleEndSelected}
          onAssignPerson={() => {
            setHighlightPeople(true);
            setTimeout(() => setHighlightPeople(false), 2000);
          }}
          dimEnded={status === 'all'}
        />
      )}

      <p className="text-xs text-gray-500 sr-only">{rightPaneLabel}</p>
    </div>
  );
}
