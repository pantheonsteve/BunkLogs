import { useMemo, useState } from 'react';

import api from '../../../api';
import Button from '../../../components/ui/Button';
import Modal from '../../../components/ui/Modal';
import Note from '../../../components/ui/Note';

/**
 * Tag the memberships of the people currently selected on the People list.
 *
 * Tags hang off Membership, not Person, so a selection of people has to
 * be resolved down to memberships first — scoped to the active program
 * when one is chosen, otherwise every active membership they hold. The
 * affected count is shown before applying so "set" can't silently wipe
 * tags on a membership the admin wasn't thinking about.
 */
function parseTags(text) {
  const seen = new Set();
  return (text || '')
    .split(/[,\n]/)
    .map((t) => t.trim().toLowerCase())
    .filter((t) => t && !seen.has(t) && seen.add(t));
}

export default function BulkTagModal({ people, programId, programName, onClose, onApplied }) {
  const [operation, setOperation] = useState('add');
  const [tagsText, setTagsText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const membershipIds = useMemo(() => {
    const ids = [];
    for (const person of people) {
      for (const m of person?.memberships || []) {
        if (!m.is_active) continue;
        if (programId && String(m.program_id) !== String(programId)) continue;
        ids.push(m.id);
      }
    }
    return ids;
  }, [people, programId]);

  const tags = parseTags(tagsText);
  const canApply = membershipIds.length > 0
    && (operation === 'set' || tags.length > 0)
    && !busy;

  const apply = async () => {
    setBusy(true);
    setError('');
    try {
      const { data } = await api.post('/api/v1/memberships/bulk-tag/', {
        operation,
        membership_ids: membershipIds,
        tags,
      });
      onApplied(data?.updated ?? membershipIds.length);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not update tags.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title="Tag memberships"
      description={
        programId
          ? `${membershipIds.length} membership${membershipIds.length === 1 ? '' : 's'} in ${programName || 'the selected program'}`
          : `${membershipIds.length} active membership${membershipIds.length === 1 ? '' : 's'} across all programs`
      }
      onClose={onClose}
      dismissible={!busy}
      data-testid="bulk-tag-modal"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
          <div className="flex-1" />
          <Button onClick={apply} disabled={!canApply} data-testid="bulk-tag-apply">
            {busy ? 'Applying…' : 'Apply'}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        {membershipIds.length === 0 && (
          <Note tone="warn">
            None of the selected people have an active membership here, so there
            is nothing to tag.
          </Note>
        )}
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
          Operation
          <select
            value={operation}
            onChange={(e) => setOperation(e.target.value)}
            data-testid="bulk-tag-operation"
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          >
            <option value="add">Add tags</option>
            <option value="remove">Remove tags</option>
            <option value="set">Replace all tags</option>
          </select>
        </label>
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
          Tags (comma-separated)
          <input
            value={tagsText}
            onChange={(e) => setTagsText(e.target.value)}
            data-testid="bulk-tag-input"
            placeholder="veteran, shabbat-lead"
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          />
        </label>
        {operation === 'set' && (
          <Note tone="warn">
            Replacing removes every tag these memberships already have.
          </Note>
        )}
        {error && <Note tone="danger">{error}</Note>}
      </div>
    </Modal>
  );
}
