import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import api from '../api';
import ErrorPanel from '../components/ui/ErrorPanel';
import LoadingState from '../components/ui/LoadingState';

const ROLE_OPTIONS = [
  { value: '', label: 'All roles' },
  { value: 'camper', label: 'Camper' },
  { value: 'counselor', label: 'Counselor' },
  { value: 'junior_counselor', label: 'Junior Counselor' },
  { value: 'specialist', label: 'Specialist' },
  { value: 'general_counselor', label: 'General Counselor' },
  { value: 'unit_head', label: 'Unit Head' },
  { value: 'leadership_team', label: 'Leadership Team' },
  { value: 'kitchen_staff', label: 'Kitchen Staff' },
  { value: 'maintenance', label: 'Maintenance' },
  { value: 'housekeeping', label: 'Housekeeping' },
  { value: 'camper_care', label: 'Camper Care' },
  { value: 'health_center', label: 'Health Center' },
  { value: 'special_diets', label: 'Special Diets' },
  { value: 'madrich', label: 'Madrich' },
  { value: 'faculty', label: 'Faculty' },
  { value: 'admin', label: 'Admin' },
];

function parseTagsInput(text) {
  if (!text) return [];
  const parts = text
    .split(/[,\n]/)
    .map((p) => p.trim().toLowerCase())
    .filter(Boolean);
  const seen = new Set();
  const out = [];
  for (const p of parts) {
    if (!seen.has(p)) {
      seen.add(p);
      out.push(p);
    }
  }
  return out;
}

function tagsToInput(tags) {
  return Array.isArray(tags) ? tags.join(', ') : '';
}

function MembershipRow({ membership, onSave, isSelected, onToggleSelect }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(tagsToInput(membership.tags));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const reset = () => {
    setDraft(tagsToInput(membership.tags));
    setError(null);
    setEditing(false);
  };

  const submit = async () => {
    setSaving(true);
    setError(null);
    try {
      const tags = parseTagsInput(draft);
      await onSave(membership.id, tags);
      setEditing(false);
    } catch (e) {
      setError(e.response?.data?.tags?.[0] || e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <tr className="bg-white dark:bg-gray-900/40">
      <td className="px-3 py-2">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={(ev) => onToggleSelect(membership.id, ev.target.checked)}
          aria-label={`Select ${membership.person_name}`}
        />
      </td>
      <td className="px-3 py-2 font-medium text-gray-900 dark:text-white">
        {membership.person_name}
        {membership.person_email && (
          <p className="text-xs text-gray-500 dark:text-gray-400">{membership.person_email}</p>
        )}
      </td>
      <td className="px-3 py-2 text-gray-600 dark:text-gray-300">{membership.role}</td>
      <td className="px-3 py-2 text-gray-600 dark:text-gray-300 text-xs">{membership.program_slug}</td>
      <td className="px-3 py-2">
        {!editing && (
          <div className="flex flex-wrap gap-1">
            {(membership.tags || []).length === 0 ? (
              <span className="text-gray-400 italic text-sm">no tags</span>
            ) : (
              (membership.tags || []).map((t) => (
                <span
                  key={t}
                  className="inline-flex items-center rounded-full bg-indigo-100 dark:bg-indigo-900/40 px-2 py-0.5 text-xs font-medium text-indigo-800 dark:text-indigo-200"
                >
                  {t}
                </span>
              ))
            )}
          </div>
        )}
        {editing && (
          <div className="flex flex-col gap-1">
            <input
              type="text"
              value={draft}
              onChange={(ev) => setDraft(ev.target.value)}
              placeholder="comma-separated tags"
              className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
              autoFocus
            />
            {error && <p className="text-xs text-rose-600 dark:text-rose-400">{error}</p>}
          </div>
        )}
      </td>
      <td className="px-3 py-2 text-right whitespace-nowrap">
        {!editing ? (
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="text-indigo-600 dark:text-indigo-400 text-sm hover:underline"
          >
            Edit
          </button>
        ) : (
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={submit}
              disabled={saving}
              className="rounded-md bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button
              type="button"
              onClick={reset}
              disabled={saving}
              className="rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 text-xs"
            >
              Cancel
            </button>
          </div>
        )}
      </td>
    </tr>
  );
}

export default function MembershipManagementPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [memberships, setMemberships] = useState([]);
  const [program, setProgram] = useState('');
  const [role, setRole] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [search, setSearch] = useState('');
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkOp, setBulkOp] = useState('add');
  const [bulkTags, setBulkTags] = useState('');
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkMessage, setBulkMessage] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (program) params.set('program', program);
      if (role) params.set('role', role);
      if (search) params.set('search', search);
      for (const t of parseTagsInput(tagFilter)) {
        params.append('tag', t);
      }
      const { data } = await api.get(`/api/v1/memberships/?${params.toString()}`);
      const items = Array.isArray(data) ? data : data?.results || [];
      setMemberships(items);
      setSelectedIds((prev) => {
        const visible = new Set(items.map((m) => m.id));
        const next = new Set();
        for (const id of prev) if (visible.has(id)) next.add(id);
        return next;
      });
    } catch (e) {
      const status = e.response?.status;
      if (status === 403) {
        setError('access');
      } else {
        setError(e.response?.data?.detail || e.message || 'Failed to load memberships');
      }
      setMemberships([]);
    } finally {
      setLoading(false);
    }
  }, [program, role, search, tagFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const saveTags = useCallback(async (membershipId, tags) => {
    const { data } = await api.patch(`/api/v1/memberships/${membershipId}/`, { tags });
    setMemberships((prev) => prev.map((m) => (m.id === membershipId ? { ...m, ...data } : m)));
  }, []);

  const toggleSelect = useCallback((id, checked) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(
    (checked) => {
      if (!checked) {
        setSelectedIds(new Set());
        return;
      }
      setSelectedIds(new Set(memberships.map((m) => m.id)));
    },
    [memberships],
  );

  const allSelected = useMemo(
    () => memberships.length > 0 && memberships.every((m) => selectedIds.has(m.id)),
    [memberships, selectedIds],
  );

  const submitBulk = useCallback(async () => {
    setBulkBusy(true);
    setBulkMessage(null);
    try {
      const tags = parseTagsInput(bulkTags);
      const ids = Array.from(selectedIds);
      if (ids.length === 0) {
        setBulkMessage({ type: 'error', text: 'Select at least one membership.' });
        return;
      }
      if (bulkOp !== 'set' && tags.length === 0) {
        setBulkMessage({ type: 'error', text: 'Provide at least one tag.' });
        return;
      }
      const { data } = await api.post('/api/v1/memberships/bulk-tag/', {
        operation: bulkOp,
        membership_ids: ids,
        tags,
      });
      setBulkMessage({
        type: 'success',
        text: `Updated ${data.updated} membership${data.updated === 1 ? '' : 's'}.`,
      });
      setBulkTags('');
      await load();
    } catch (e) {
      setBulkMessage({
        type: 'error',
        text: e.response?.data?.detail || e.message || 'Bulk update failed',
      });
    } finally {
      setBulkBusy(false);
    }
  }, [bulkOp, bulkTags, selectedIds, load]);

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
      {/* 3.27: back-link to /admin, matching templates and groups pages. */}
      <Link
        to="/admin"
        data-testid="memberships-admin-back-link"
        className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4"
      >
        ← Admin
      </Link>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Memberships</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Tag memberships with demographic and grouping labels (e.g. international,
            domestic, israeli, waterfront, arts, sports).
          </p>
        </div>
      </div>

          <section className="mb-6 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <label className="flex flex-col gap-1 text-sm text-gray-700 dark:text-gray-300">
                <span>Program slug</span>
                <input
                  type="text"
                  value={program}
                  onChange={(ev) => setProgram(ev.target.value.trim())}
                  placeholder="e.g. crane-lake-summer-2026"
                  className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm text-gray-700 dark:text-gray-300">
                <span>Role</span>
                <select
                  value={role}
                  onChange={(ev) => setRole(ev.target.value)}
                  className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
                >
                  {ROLE_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm text-gray-700 dark:text-gray-300">
                <span>Tag filter</span>
                <input
                  type="text"
                  value={tagFilter}
                  onChange={(ev) => setTagFilter(ev.target.value)}
                  placeholder="comma-separated; ALL must match"
                  className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm text-gray-700 dark:text-gray-300">
                <span>Name search</span>
                <input
                  type="text"
                  value={search}
                  onChange={(ev) => setSearch(ev.target.value)}
                  placeholder="first / last / preferred"
                  className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
                />
              </label>
            </div>
          </section>

          {selectedIds.size > 0 && (
            <section className="mb-6 rounded-lg border border-indigo-200 dark:border-indigo-900/50 bg-indigo-50 dark:bg-indigo-950/30 p-4">
              <div className="flex flex-col md:flex-row md:items-end gap-3">
                <div className="text-sm text-indigo-900 dark:text-indigo-100">
                  <p className="font-medium">{selectedIds.size} selected</p>
                  <p className="text-xs">Bulk update tags on the selected memberships.</p>
                </div>
                <label className="flex flex-col gap-1 text-sm text-indigo-900 dark:text-indigo-100">
                  <span>Operation</span>
                  <select
                    value={bulkOp}
                    onChange={(ev) => setBulkOp(ev.target.value)}
                    className="rounded-md border border-indigo-300 dark:border-indigo-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm"
                  >
                    <option value="add">Add tag(s)</option>
                    <option value="remove">Remove tag(s)</option>
                    <option value="set">Set tag(s) (replace)</option>
                  </select>
                </label>
                <label className="flex flex-col gap-1 text-sm text-indigo-900 dark:text-indigo-100 flex-1">
                  <span>Tags</span>
                  <input
                    type="text"
                    value={bulkTags}
                    onChange={(ev) => setBulkTags(ev.target.value)}
                    placeholder="comma-separated"
                    className="rounded-md border border-indigo-300 dark:border-indigo-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm"
                  />
                </label>
                <button
                  type="button"
                  onClick={submitBulk}
                  disabled={bulkBusy}
                  className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
                >
                  {bulkBusy ? 'Applying…' : 'Apply'}
                </button>
              </div>
              {bulkMessage && (
                <p
                  className={`mt-2 text-sm ${
                    bulkMessage.type === 'success'
                      ? 'text-emerald-700 dark:text-emerald-300'
                      : 'text-rose-700 dark:text-rose-300'
                  }`}
                >
                  {bulkMessage.text}
                </p>
              )}
            </section>
          )}

          {loading && <LoadingState>Loading…</LoadingState>}

          {!loading && error === 'access' && (
            <div className="rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/20 p-4 text-amber-900 dark:text-amber-100">
              <p className="font-medium">Access restricted</p>
              <p className="text-sm mt-1">
                Membership management requires an organization <strong>admin</strong> membership.
              </p>
              <Link to="/dashboard" className="text-sm underline mt-2 inline-block">
                Back to dashboard
              </Link>
            </div>
          )}

          {!loading && error && error !== 'access' && (
            <ErrorPanel>{error}</ErrorPanel>
          )}

          {!loading && !error && (
            <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-800/80">
                  <tr>
                    <th className="px-3 py-2">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        onChange={(ev) => toggleSelectAll(ev.target.checked)}
                        aria-label="Select all visible"
                      />
                    </th>
                    <th className="text-left px-3 py-2 font-medium">Person</th>
                    <th className="text-left px-3 py-2 font-medium">Role</th>
                    <th className="text-left px-3 py-2 font-medium">Program</th>
                    <th className="text-left px-3 py-2 font-medium">Tags</th>
                    <th className="text-right px-3 py-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {memberships.map((m) => (
                    <MembershipRow
                      key={m.id}
                      membership={m}
                      onSave={saveTags}
                      isSelected={selectedIds.has(m.id)}
                      onToggleSelect={toggleSelect}
                    />
                  ))}
                </tbody>
              </table>
              {memberships.length === 0 && (
                <p className="p-4 text-gray-500 dark:text-gray-400 text-sm">
                  No memberships match these filters.
                </p>
              )}
            </div>
          )}
    </main>
  );
}
