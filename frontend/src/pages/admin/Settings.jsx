import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  getAdminSettings,
  patchAdminSettings,
  testAdminMaintenanceNotifications,
  listAdminPrograms,
  createAdminProgram,
  patchAdminProgram,
  endAdminProgram,
} from '../../api/admin';

/**
 * Step 7_13 PR2 — Settings + Programs (Story 58).
 *
 * Tabs:
 *   - Identity & Localization (Org name, supported languages, day rollover)
 *   - Tag vocabulary
 *   - Programs (list + create + End Program with typed-confirmation modal)
 *
 * "End Program" runs server-side as a single transaction that
 * deactivates Memberships, closes open orders/tickets, and writes an
 * audit row per touched record. We refuse client-side if the typed
 * confirmation doesn't match.
 */

const TABS = [
  { key: 'identity', label: 'Identity & Localization' },
  { key: 'tags', label: 'Tag vocabulary' },
  { key: 'notifications', label: 'Notifications' },
  { key: 'programs', label: 'Programs' },
];

const EMPTY_RECIPIENT = { email: '', instant: true, digest: false };

function legacyRecipientsFromSettings(settings) {
  const list = settings?.maintenance_notification_recipients;
  if (Array.isArray(list) && list.length > 0) {
    return list.map((r) => ({
      email: r.email || '',
      instant: Boolean(r.instant),
      digest: Boolean(r.digest),
    }));
  }
  const legacy = settings?.maintenance_digest_email;
  if (legacy) {
    return [{ email: legacy, instant: false, digest: true }];
  }
  return [{ ...EMPTY_RECIPIENT }];
}

function FieldInput({ label, value, onChange, type = 'text' }) {
  return (
    <label className="block text-xs font-medium text-gray-700">
      {label}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-gray-300 bg-white p-2 text-sm"
      />
    </label>
  );
}

function IdentityTab({ settings, onSaved }) {
  const [draft, setDraft] = useState({
    supported_languages: (settings?.supported_languages || ['en']).join(','),
    rollover_hour: settings?.rollover_hour ?? '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [pendingRollover, setPendingRollover] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    const langs = draft.supported_languages
      .split(',').map((s) => s.trim()).filter(Boolean);
    const rolloverHour = draft.rollover_hour === ''
      ? null
      : Number(draft.rollover_hour);
    const rolloverChanged = rolloverHour !== (settings?.rollover_hour ?? null);
    if (rolloverChanged && !pendingRollover) {
      setPendingRollover(true);
      return;
    }
    setSaving(true);
    setError('');
    try {
      const updated = await patchAdminSettings({
        supported_languages: langs,
        rollover_hour: rolloverHour,
      });
      onSaved(updated);
      setPendingRollover(false);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not save.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-3" data-testid="settings-identity">
      <FieldInput
        label="Supported languages (comma-separated, e.g. en,es,he)"
        value={draft.supported_languages}
        onChange={(v) => setDraft({ ...draft, supported_languages: v })}
      />
      <FieldInput
        label="Day rollover hour (0–23)"
        type="number"
        value={draft.rollover_hour}
        onChange={(v) => setDraft({ ...draft, rollover_hour: v })}
      />
      {pendingRollover && (
        <div
          data-testid="rollover-confirmation"
          className="rounded-md border border-amber-400 bg-amber-50 p-2 text-xs space-y-1"
        >
          <p>Changing the rollover hour affects how "today" is computed for everyone in this org.</p>
          <p>Click <strong>Confirm save</strong> again to apply.</p>
        </div>
      )}
      {error && <p className="text-sm text-red-700">{error}</p>}
      <button
        type="submit"
        disabled={saving}
        data-testid="settings-identity-save"
        className="px-3 py-1.5 rounded-md text-sm bg-indigo-600 text-white disabled:opacity-60"
      >
        {pendingRollover ? 'Confirm save' : (saving ? 'Saving…' : 'Save')}
      </button>
    </form>
  );
}

function TagsTab({ settings, onSaved }) {
  const [tags, setTags] = useState((settings?.tag_vocabulary || []).join('\n'));
  const [saving, setSaving] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await patchAdminSettings({
        tag_vocabulary: tags
          .split('\n').map((t) => t.trim().toLowerCase()).filter(Boolean),
      });
      onSaved(updated);
    } finally {
      setSaving(false);
    }
  };
  return (
    <form onSubmit={submit} className="space-y-3" data-testid="settings-tags">
      <label className="block text-xs font-medium">Tag vocabulary (one per line)
        <textarea
          rows={10}
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm bg-white"
        />
      </label>
      <button
        type="submit"
        disabled={saving}
        className="px-3 py-1.5 rounded-md text-sm bg-indigo-600 text-white disabled:opacity-60"
      >
        {saving ? 'Saving…' : 'Save tag vocabulary'}
      </button>
    </form>
  );
}

function NotificationsTab({ settings, onSaved }) {
  const orgSettings = settings?.settings || settings || {};
  const [recipients, setRecipients] = useState(() => legacyRecipientsFromSettings(orgSettings));
  const [digestTime, setDigestTime] = useState(
    orgSettings.maintenance_digest_time || '06:00',
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [testEmail, setTestEmail] = useState('');
  const [testing, setTesting] = useState(false);
  const [testMessage, setTestMessage] = useState('');
  const [testError, setTestError] = useState('');

  useEffect(() => {
    const rows = legacyRecipientsFromSettings(orgSettings);
    setRecipients(rows);
    setDigestTime(orgSettings.maintenance_digest_time || '06:00');
    const first = rows.find((r) => r.email.trim())?.email?.trim() || '';
    setTestEmail(first);
  }, [settings]);

  const updateRecipient = (index, field, value) => {
    setRecipients((rows) =>
      rows.map((row, i) => (i === index ? { ...row, [field]: value } : row)),
    );
  };

  const addRecipient = () => {
    setRecipients((rows) => [...rows, { ...EMPTY_RECIPIENT }]);
  };

  const removeRecipient = (index) => {
    setRecipients((rows) => rows.filter((_, i) => i !== index));
  };

  const submit = async (e) => {
    e.preventDefault();
    const cleaned = recipients
      .map((r) => ({
        email: r.email.trim().toLowerCase(),
        instant: Boolean(r.instant),
        digest: Boolean(r.digest),
      }))
      .filter((r) => r.email);
    setSaving(true);
    setError('');
    try {
      const updated = await patchAdminSettings({
        settings: {
          maintenance_notification_recipients: cleaned,
          maintenance_digest_time: digestTime.trim() || '06:00',
        },
      });
      onSaved(updated);
    } catch (err) {
      setError(
        err?.response?.data?.maintenance_notification_recipients
        || err?.response?.data?.maintenance_digest_time
        || err?.response?.data?.detail
        || 'Could not save.',
      );
    } finally {
      setSaving(false);
    }
  };

  const sendTest = async () => {
    setTesting(true);
    setTestMessage('');
    setTestError('');
    try {
      const result = await testAdminMaintenanceNotifications(testEmail.trim());
      setTestMessage(result?.detail || 'Test email sent.');
    } catch (err) {
      setTestError(err?.response?.data?.detail || 'Test email failed.');
    } finally {
      setTesting(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4" data-testid="settings-notifications">
      <p className="text-sm text-gray-600 dark:text-gray-400">
        Configure who receives instant alerts when a counselor submits a maintenance ticket,
        and who receives the daily digest of open tickets. Times use your org timezone.
      </p>
      <div className="overflow-x-auto rounded-md border bg-white dark:bg-gray-900">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs uppercase text-gray-500">
              <th className="p-2 font-medium">Email</th>
              <th className="p-2 font-medium">Instant alert</th>
              <th className="p-2 font-medium">Daily digest</th>
              <th className="p-2 w-16" />
            </tr>
          </thead>
          <tbody>
            {recipients.map((row, index) => (
              <tr key={index} className="border-b last:border-b-0" data-testid={`recipient-row-${index}`}>
                <td className="p-2">
                  <input
                    type="email"
                    value={row.email}
                    onChange={(e) => updateRecipient(index, 'email', e.target.value)}
                    placeholder="facilities@camp.com"
                    className="w-full rounded-md border border-gray-300 bg-white p-2 text-sm dark:bg-gray-800"
                  />
                </td>
                <td className="p-2 text-center">
                  <input
                    type="checkbox"
                    checked={row.instant}
                    onChange={(e) => updateRecipient(index, 'instant', e.target.checked)}
                    data-testid={`recipient-instant-${index}`}
                  />
                </td>
                <td className="p-2 text-center">
                  <input
                    type="checkbox"
                    checked={row.digest}
                    onChange={(e) => updateRecipient(index, 'digest', e.target.checked)}
                    data-testid={`recipient-digest-${index}`}
                  />
                </td>
                <td className="p-2 text-center">
                  <button
                    type="button"
                    onClick={() => removeRecipient(index)}
                    className="text-xs text-red-600 hover:underline"
                    disabled={recipients.length <= 1}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button
        type="button"
        onClick={addRecipient}
        data-testid="recipient-add"
        className="text-sm text-indigo-600 hover:underline"
      >
        Add recipient
      </button>
      <FieldInput
        label="Daily digest send time (HH:MM, 24-hour)"
        value={digestTime}
        onChange={setDigestTime}
      />
      <div className="rounded-md border border-gray-200 bg-gray-50 p-3 space-y-2 dark:border-gray-700 dark:bg-gray-900/40">
        <p className="text-xs font-medium text-gray-700 dark:text-gray-300">
          Test outbound email
        </p>
        <p className="text-xs text-gray-500">
          Sends a test message through the same Mailgun path used for maintenance alerts.
        </p>
        <FieldInput
          label="Send test to"
          type="email"
          value={testEmail}
          onChange={setTestEmail}
        />
        {testMessage && (
          <p className="text-sm text-green-700" data-testid="notifications-test-success">
            {testMessage}
          </p>
        )}
        {testError && (
          <p className="text-sm text-red-700" data-testid="notifications-test-error">
            {testError}
          </p>
        )}
        <button
          type="button"
          onClick={sendTest}
          disabled={testing || !testEmail.trim()}
          data-testid="settings-notifications-test"
          className="px-3 py-1.5 rounded-md text-sm border border-indigo-300 text-indigo-700 bg-white disabled:opacity-60 dark:bg-gray-900"
        >
          {testing ? 'Sending test…' : 'Send test email'}
        </button>
      </div>
      {error && <p className="text-sm text-red-700">{error}</p>}
      <button
        type="submit"
        disabled={saving}
        data-testid="settings-notifications-save"
        className="px-3 py-1.5 rounded-md text-sm bg-indigo-600 text-white disabled:opacity-60"
      >
        {saving ? 'Saving…' : 'Save notifications'}
      </button>
    </form>
  );
}

function ProgramsTab() {
  const [programs, setPrograms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [adding, setAdding] = useState(false);
  const [endingProgram, setEndingProgram] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listAdminPrograms();
      setPrograms(data.results || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-3" data-testid="settings-programs">
      <header className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Programs</h3>
        <button
          type="button"
          data-testid="programs-add"
          onClick={() => setAdding((v) => !v)}
          className="text-xs px-2 py-1 rounded-md bg-indigo-600 text-white"
        >
          {adding ? 'Cancel' : 'New program'}
        </button>
      </header>

      {adding && (
        <AddProgramForm
          onCreated={() => { setAdding(false); load(); }}
          onCancel={() => setAdding(false)}
        />
      )}

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : error ? (
        <p className="text-sm text-red-700">Could not load programs.</p>
      ) : programs.length === 0 ? (
        <p className="text-sm italic text-gray-500">No programs yet.</p>
      ) : (
        <ul className="divide-y rounded-md border bg-white dark:bg-gray-900">
          {programs.map((p) => (
            <li key={p.id} className="p-3 text-sm flex items-center justify-between" data-testid={`program-row-${p.id}`}>
              <div>
                <p className="font-medium">{p.name}</p>
                <p className="text-xs text-gray-500">{p.program_type} · {p.start_date || '—'} → {p.end_date || 'open'}</p>
              </div>
              {p.is_active ? (
                <button
                  type="button"
                  data-testid={`program-end-${p.id}`}
                  onClick={() => setEndingProgram(p)}
                  className="text-xs px-2 py-1 rounded-md border border-red-300 text-red-700 hover:bg-red-50"
                >
                  End program
                </button>
              ) : (
                <span className="text-xs px-2 py-0.5 rounded-full bg-gray-200 text-gray-700">ended</span>
              )}
            </li>
          ))}
        </ul>
      )}

      {endingProgram && (
        <EndProgramModal
          program={endingProgram}
          onClose={() => setEndingProgram(null)}
          onEnded={() => { setEndingProgram(null); load(); }}
        />
      )}
    </div>
  );
}

function AddProgramForm({ onCreated, onCancel }) {
  const [draft, setDraft] = useState({
    name: '',
    slug: '',
    program_type: '',
    start_date: '',
    end_date: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await createAdminProgram(draft);
      onCreated();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not create program.');
    } finally {
      setSaving(false);
    }
  };
  return (
    <form onSubmit={submit} className="rounded-md border border-indigo-200 bg-indigo-50/30 p-3 space-y-2" data-testid="program-add-form">
      <FieldInput label="Name" value={draft.name} onChange={(v) => setDraft({ ...draft, name: v })} />
      <FieldInput label="Slug" value={draft.slug} onChange={(v) => setDraft({ ...draft, slug: v })} />
      <FieldInput label="Program type (e.g. summer_camp)" value={draft.program_type} onChange={(v) => setDraft({ ...draft, program_type: v })} />
      <FieldInput label="Start date (yyyy-mm-dd)" value={draft.start_date} onChange={(v) => setDraft({ ...draft, start_date: v })} />
      <FieldInput label="End date (yyyy-mm-dd, optional)" value={draft.end_date} onChange={(v) => setDraft({ ...draft, end_date: v })} />
      {error && <p className="text-sm text-red-700">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="text-sm text-gray-600 hover:underline">Cancel</button>
        <button
          type="submit"
          disabled={saving}
          className="px-3 py-1.5 rounded-md text-sm bg-indigo-600 text-white disabled:opacity-60"
        >
          {saving ? 'Creating…' : 'Create program'}
        </button>
      </div>
    </form>
  );
}

function EndProgramModal({ program, onClose, onEnded }) {
  const [typed, setTyped] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [summary, setSummary] = useState(null);
  const expected = program.slug || program.name;
  const canSubmit = typed === expected && reason.trim();
  const submit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError('');
    try {
      const data = await endAdminProgram(program.id, reason);
      setSummary(data?.summary || null);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not end program.');
    } finally {
      setSubmitting(false);
    }
  };
  return (
    <div
      role="dialog"
      data-testid="end-program-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => { if (e.target === e.currentTarget && !submitting) onClose(); }}
    >
      <div className="w-full max-w-md rounded-xl bg-white p-5 shadow-lg space-y-3 dark:bg-gray-900">
        <h2 className="text-lg font-semibold text-red-800">End program: {program.name}</h2>
        {summary ? (
          <div className="space-y-2 text-sm" data-testid="end-program-summary">
            <p>This action ran in a single transaction.</p>
            <ul className="list-disc pl-5 text-sm">
              <li>{summary.memberships_deactivated} memberships deactivated</li>
              <li>{summary.orders_closed} Camper Care orders closed</li>
              <li>{summary.maintenance_tickets_closed} maintenance tickets closed</li>
              <li>Ended at {summary.ended_at}</li>
            </ul>
            <button
              type="button"
              onClick={onEnded}
              className="px-3 py-1.5 rounded-md text-sm bg-indigo-600 text-white"
            >
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-2">
            <p className="text-sm">This will deactivate all memberships in this program and close
              any open orders/tickets. Type <strong>{expected}</strong> to confirm.</p>
            <FieldInput label="Type to confirm" value={typed} onChange={setTyped} />
            <label className="block text-xs font-medium">Reason
              <textarea
                rows={3}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm bg-white"
              />
            </label>
            {error && <p className="text-sm text-red-700">{error}</p>}
            <div className="flex justify-end gap-2">
              <button type="button" disabled={submitting} onClick={onClose} className="text-sm text-gray-600 hover:underline">Cancel</button>
              <button
                type="submit"
                disabled={!canSubmit || submitting}
                data-testid="end-program-confirm"
                className="px-3 py-1.5 rounded-md text-sm bg-red-600 text-white disabled:opacity-50"
              >
                {submitting ? 'Ending…' : 'End program'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default function AdminSettings() {
  const [searchParams] = useSearchParams();
  const [settings, setSettings] = useState(null);
  const [error, setError] = useState(null);
  const initialTab = searchParams.get('tab');
  const [tab, setTab] = useState(
    TABS.some((t) => t.key === initialTab) ? initialTab : 'identity',
  );
  const load = useCallback(async () => {
    try {
      const data = await getAdminSettings();
      setSettings(data);
    } catch (err) {
      setError(err);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-4xl mx-auto" data-testid="admin-settings">
      <header className="mb-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
      </header>
      <nav className="border-b border-gray-200 dark:border-gray-700 flex gap-3 mb-4">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            data-testid={`settings-tab-${t.key}`}
            onClick={() => setTab(t.key)}
            className={`pb-2 -mb-px text-sm font-medium border-b-2 ${
              tab === t.key
                ? 'border-indigo-500 text-indigo-700 dark:text-indigo-200'
                : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>
      {error ? (
        <p className="text-sm text-red-700">Could not load settings.</p>
      ) : !settings ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : (
        <>
          {tab === 'identity' && <IdentityTab settings={settings} onSaved={(s) => setSettings({ ...settings, ...s })} />}
          {tab === 'tags' && <TagsTab settings={settings} onSaved={(s) => setSettings({ ...settings, ...s })} />}
          {tab === 'notifications' && (
            <NotificationsTab
              settings={settings}
              onSaved={(s) => setSettings({ ...settings, settings: { ...(settings.settings || {}), ...s.settings } })}
            />
          )}
          {tab === 'programs' && <ProgramsTab />}
        </>
      )}
    </main>
  );
}
