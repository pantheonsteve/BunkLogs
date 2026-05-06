import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Copy, FileText } from 'lucide-react';
import api from '../../../api';

const ROLE_OPTIONS = [
  { value: '', label: 'No specific role' },
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
  { value: 'madrich', label: 'Madrich' },
  { value: 'faculty', label: 'Faculty' },
  { value: 'admin', label: 'Admin' },
];

const CADENCE_OPTIONS = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'biweekly', label: 'Biweekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'on_demand', label: 'On Demand' },
];

function inputClass() {
  return 'w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500';
}

function Label({ children, htmlFor }) {
  return (
    <label htmlFor={htmlFor} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
      {children}
    </label>
  );
}

export default function TemplateNewPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState(null); // null = chooser, 'blank' | 'clone'
  const [existing, setExisting] = useState([]);
  const [loadingExisting, setLoadingExisting] = useState(false);
  const [cloneSource, setCloneSource] = useState('');
  const [form, setForm] = useState({
    name: '',
    role: '',
    cadence: 'weekly',
    languages: 'en',
    description: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (mode !== 'clone') return;
    setLoadingExisting(true);
    api
      .get('/api/v1/templates/')
      .then(({ data }) => {
        const results = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
        setExisting(results);
      })
      .catch(() => setExisting([]))
      .finally(() => setLoadingExisting(false));
  }, [mode]);

  const handleClone = async () => {
    if (!cloneSource) { setError('Select a template to clone.'); return; }
    setSaving(true);
    setError('');
    try {
      const { data } = await api.post(`/api/v1/templates/${cloneSource}/clone/`);
      navigate(`/admin/templates/${data.id}/edit`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Clone failed.');
    } finally {
      setSaving(false);
    }
  };

  const handleCreate = async () => {
    if (!form.name.trim()) { setError('Template name is required.'); return; }
    setSaving(true);
    setError('');
    try {
      const langs = form.languages.split(/[\s,]+/).map((l) => l.trim()).filter(Boolean);
      const slug = form.name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
      const { data } = await api.post('/api/v1/templates/', {
        name: form.name.trim(),
        slug,
        role: form.role || undefined,
        cadence: form.cadence,
        languages: langs.length ? langs : ['en'],
        description: form.description,
        schema: { fields: [] },
        is_active: false,
      });
      navigate(`/admin/templates/${data.id}/edit`);
    } catch (err) {
      const body = err.response?.data;
      setError(
        typeof body === 'string' ? body :
        body?.name?.[0] || body?.detail || 'Create failed.'
      );
    } finally {
      setSaving(false);
    }
  };

  // Chooser
  if (!mode) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 px-4 py-6">
        <div className="max-w-xl mx-auto">
          <Link
            to="/admin/templates"
            className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-6"
          >
            <ArrowLeft size={14} /> Back
          </Link>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-2">New template</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">How do you want to start?</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => setMode('blank')}
              className="group flex flex-col items-center gap-3 p-6 rounded-xl border-2 border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-500 bg-white dark:bg-gray-900 text-left transition-colors"
            >
              <FileText size={32} className="text-gray-400 group-hover:text-blue-500 transition-colors" />
              <div className="text-center">
                <p className="font-medium text-gray-900 dark:text-white">Blank template</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Start from scratch</p>
              </div>
            </button>

            <button
              type="button"
              onClick={() => setMode('clone')}
              className="group flex flex-col items-center gap-3 p-6 rounded-xl border-2 border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-500 bg-white dark:bg-gray-900 text-left transition-colors"
            >
              <Copy size={32} className="text-gray-400 group-hover:text-blue-500 transition-colors" />
              <div className="text-center">
                <p className="font-medium text-gray-900 dark:text-white">Clone existing</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Copy from a global or org template</p>
              </div>
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (mode === 'clone') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 px-4 py-6">
        <div className="max-w-md mx-auto">
          <button
            type="button"
            onClick={() => setMode(null)}
            className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-6"
          >
            <ArrowLeft size={14} /> Back
          </button>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-6">Clone a template</h1>

          {loadingExisting ? (
            <p className="text-sm text-gray-500">Loading templates…</p>
          ) : (
            <div className="space-y-2 mb-6">
              {existing.map((tpl) => (
                <label
                  key={tpl.id}
                  className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    cloneSource === String(tpl.id)
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30'
                      : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="clone_source"
                    value={tpl.id}
                    checked={cloneSource === String(tpl.id)}
                    onChange={(e) => setCloneSource(e.target.value)}
                  />
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{tpl.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      v{tpl.version} {tpl.role ? `· ${tpl.role}` : ''}
                      {!tpl.organization ? ' · global' : ''}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          )}

          {error && <p className="text-sm text-red-600 mb-3">{error}</p>}

          <button
            type="button"
            onClick={handleClone}
            disabled={saving || !cloneSource}
            className="w-full py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Cloning…' : 'Clone and edit'}
          </button>
        </div>
      </div>
    );
  }

  // Blank form
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 px-4 py-6">
      <div className="max-w-md mx-auto">
        <button
          type="button"
          onClick={() => setMode(null)}
          className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-6"
        >
          <ArrowLeft size={14} /> Back
        </button>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-6">New blank template</h1>

        <div className="space-y-4">
          <div>
            <Label htmlFor="tpl-name">Template name *</Label>
            <input
              id="tpl-name"
              type="text"
              className={inputClass()}
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Weekly Counselor Reflection"
            />
          </div>

          <div>
            <Label htmlFor="tpl-role">Role</Label>
            <select
              id="tpl-role"
              className={inputClass()}
              value={form.role}
              onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
            >
              {ROLE_OPTIONS.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </div>

          <div>
            <Label htmlFor="tpl-cadence">Cadence</Label>
            <select
              id="tpl-cadence"
              className={inputClass()}
              value={form.cadence}
              onChange={(e) => setForm((f) => ({ ...f, cadence: e.target.value }))}
            >
              {CADENCE_OPTIONS.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          <div>
            <Label htmlFor="tpl-languages">Languages (comma-separated)</Label>
            <input
              id="tpl-languages"
              type="text"
              className={inputClass()}
              value={form.languages}
              onChange={(e) => setForm((f) => ({ ...f, languages: e.target.value }))}
              placeholder="en, es"
            />
          </div>

          <div>
            <Label htmlFor="tpl-description">Description (optional)</Label>
            <textarea
              id="tpl-description"
              rows={2}
              className={inputClass()}
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="button"
            onClick={handleCreate}
            disabled={saving}
            className="w-full py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 mt-2"
          >
            {saving ? 'Creating…' : 'Create and edit'}
          </button>
        </div>
      </div>
    </div>
  );
}
