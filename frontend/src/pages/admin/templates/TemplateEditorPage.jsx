import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, BarChart2, ChevronDown, Plus, X, AlertTriangle } from 'lucide-react';
import api from '../../../api';
import FieldList from '../../../components/templates/FieldList';
import FieldInspector from '../../../components/templates/FieldInspector';
import FieldTypePicker from '../../../components/templates/FieldTypePicker';
import LivePreview from '../../../components/templates/LivePreview';
import DashboardPreviewModal from '../../../dashboards/DashboardPreviewModal';

/* ── helpers ─────────────────────────────────────────────────── */

let _uid = 0;
function uid() { return `fid_${++_uid}`; }

function addIds(fields) {
  return (fields || []).map((f) => ({ ...f, _id: f._id || uid() }));
}

function stripIds(fields) {
  return fields.map(({ _id, ...rest }) => rest);
}

function fieldDefaults(type, languages) {
  const lang = (languages || ['en'])[0];
  const base = { type, key: '', required: true, _id: uid() };
  const promptBase = { ...base, prompts: { [lang]: '' } };
  const scaleBase = {
    ...base,
    scale: [1, 5],
    scale_labels: { [lang]: ['1', '2', '3', '4', '5'] },
  };

  switch (type) {
    case 'text': return { ...promptBase, max_length: 500 };
    case 'textarea': return { ...promptBase, max_length: 1000 };
    case 'text_list': return { ...promptBase, min_items: 1, max_items: 5 };
    case 'single_choice': return { ...promptBase, required: true, options: [] };
    case 'multiple_choice': return { ...promptBase, required: false, options: [] };
    case 'yes_no': return { ...promptBase, follow_up_on: false };
    case 'date': return { ...promptBase, required: false };
    case 'number': return { ...promptBase, required: false };
    case 'section_header': return { ...base, prompts: { [lang]: '' }, required: undefined };
    case 'instructions': return { ...base, prompts: { [lang]: '' }, required: undefined };
    case 'rating_group': return { ...scaleBase, categories: [], required: true };
    case 'single_rating': return { ...scaleBase, required: true };
    default: return promptBase;
  }
}

function clientValidate(schema, languages) {
  const errors = [];
  const fields = schema?.fields || [];
  const usedKeys = new Set();

  fields.forEach((f, idx) => {
    const loc = `Field ${idx + 1} (${f.type})`;
    if (!f.key || !f.key.trim()) {
      errors.push(`${loc}: field key is required.`);
    } else if (usedKeys.has(f.key)) {
      errors.push(`${loc}: duplicate key "${f.key}".`);
    } else {
      usedKeys.add(f.key);
    }

    const needsPrompt = !['rating_group', 'single_rating'].includes(f.type);
    if (needsPrompt) {
      for (const lang of languages) {
        if (!f.prompts?.[lang]) {
          errors.push(`${loc}: missing "${lang}" prompt.`);
        }
      }
    }

    if (f.type === 'rating_group') {
      if (!f.categories || f.categories.length === 0) {
        errors.push(`${loc}: add at least one category.`);
      }
    }

    if ((f.type === 'single_choice' || f.type === 'multiple_choice') && (!f.options || f.options.length === 0)) {
      errors.push(`${loc}: add at least one option.`);
    }
  });

  return errors;
}

/* ── Toast ───────────────────────────────────────────────────── */
function Toast({ message, onClose }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onClose, 4000);
    return () => clearTimeout(t);
  }, [message, onClose]);
  if (!message) return null;
  return (
    <div
      role="status"
      className="fixed bottom-6 right-6 z-50 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 px-4 py-2 rounded-lg shadow-lg text-sm flex items-center gap-2"
    >
      <span>{message}</span>
      <button type="button" onClick={onClose} className="ml-2 opacity-70 hover:opacity-100"><X size={14} /></button>
    </div>
  );
}

/* ── AddLanguageModal ─────────────────────────────────────────── */
function AddLanguageModal({ onAdd, onClose, existing }) {
  const [code, setCode] = useState('');
  const COMMON = ['en', 'es', 'fr', 'he', 'ru', 'pt'];
  const available = COMMON.filter((c) => !existing.includes(c));
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-xs p-6">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Add language</h3>
        <div className="flex flex-wrap gap-2 mb-3">
          {available.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCode(c)}
              className={`px-3 py-1 rounded-full text-sm border ${code === c ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300'}`}
            >
              {c}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="or type code, e.g. de"
          className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-1.5 text-sm mb-4"
          value={code}
          onChange={(e) => setCode(e.target.value.toLowerCase().slice(0, 5))}
        />
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="text-sm text-gray-600 dark:text-gray-400 px-3 py-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800">Cancel</button>
          <button
            type="button"
            disabled={!code || existing.includes(code)}
            onClick={() => { onAdd(code); onClose(); }}
            className="text-sm bg-blue-600 text-white px-4 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            Add
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Main editor ─────────────────────────────────────────────── */
export default function TemplateEditorPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  // Remote state
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [remote, setRemote] = useState(null);
  const [responseCount, setResponseCount] = useState(0);

  // Draft state
  const [name, setName] = useState('');
  const [fields, setFields] = useState([]);
  const [languages, setLanguages] = useState(['en']);
  const [isActive, setIsActive] = useState(true);
  const [dirty, setDirty] = useState(false);

  // UI state
  const [language, setLanguage] = useState('en');
  const [selectedFieldId, setSelectedFieldId] = useState(null);
  const [showTypePicker, setShowTypePicker] = useState(false);
  const [showAddLang, setShowAddLang] = useState(false);
  const [showDashPreview, setShowDashPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validationErrors, setValidationErrors] = useState([]);
  const [toast, setToast] = useState('');

  const showToast = useCallback((msg) => {
    setToast(msg);
  }, []);

  // Load template
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api
      .get(`/api/v1/templates/${id}/`)
      .then(({ data }) => {
        setRemote(data);
        setName(data.name || '');
        setFields(addIds(data.schema?.fields || []));
        setLanguages(data.languages?.length ? data.languages : ['en']);
        setIsActive(data.is_active !== false);
        setLanguage((data.languages || ['en'])[0]);
        setDirty(false);
        // Count responses
        return api.get('/api/v1/reflections/', { params: { template: id } });
      })
      .then(({ data }) => {
        const count = data?.count ?? (Array.isArray(data) ? data.length : 0);
        setResponseCount(count);
      })
      .catch((err) => {
        if (!loadError) setLoadError(err.response?.data?.detail || 'Could not load template.');
      })
      .finally(() => setLoading(false));
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const schema = { fields: fields.map(({ _id, ...rest }) => rest) };
  const schemaWithIds = { fields };

  // Keyboard shortcut: Cmd+S to save
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        if (dirty) handleSave(true);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [dirty, fields, name, languages, isActive]); // eslint-disable-line react-hooks/exhaustive-deps

  const markDirty = useCallback(() => setDirty(true), []);

  const handleFieldChange = useCallback((updatedField) => {
    setFields((prev) =>
      prev.map((f) => (f._id === updatedField._id ? updatedField : f)),
    );
    markDirty();
  }, [markDirty]);

  const handleReorder = useCallback((newFields) => {
    setFields(newFields);
    markDirty();
  }, [markDirty]);

  const handleAddField = useCallback((type) => {
    const newField = fieldDefaults(type, languages);
    setFields((prev) => [...prev, newField]);
    setSelectedFieldId(newField._id);
    markDirty();
  }, [languages, markDirty]);

  const handleDeleteField = useCallback(() => {
    setFields((prev) => prev.filter((f) => f._id !== selectedFieldId));
    setSelectedFieldId(null);
    markDirty();
  }, [selectedFieldId, markDirty]);

  const selectedField = fields.find((f) => f._id === selectedFieldId) || null;

  const handleSave = useCallback(async (stayOnPage = false) => {
    const errs = clientValidate({ fields: stripIds(fields) }, languages);
    if (errs.length > 0) {
      setValidationErrors(errs);
      return;
    }
    setValidationErrors([]);
    setSaving(true);
    try {
      const payload = {
        name,
        schema: { fields: stripIds(fields) },
        languages,
        is_active: isActive,
      };
      const { data } = await api.patch(`/api/v1/templates/${id}/`, payload);
      const versionMsg = data.created_new_version
        ? `Published as v${data.version}`
        : `Saved (still v${data.version})`;
      showToast(versionMsg);
      setRemote(data);
      setDirty(false);
      if (!stayOnPage) {
        navigate('/admin/templates');
      }
    } catch (err) {
      const body = err.response?.data;
      const msg =
        typeof body === 'string' ? body :
        body?.schema ? `Schema error: ${JSON.stringify(body.schema)}` :
        body?.detail || 'Save failed.';
      showToast(msg);
    } finally {
      setSaving(false);
    }
  }, [fields, languages, name, isActive, id, navigate, showToast]);

  const addLanguage = useCallback((code) => {
    setLanguages((prev) => [...prev, code]);
    markDirty();
  }, [markDirty]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500 dark:text-gray-400 text-sm">
        Loading template…
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 dark:text-red-400 mb-4">{loadError}</p>
          <Link to="/admin/templates" className="text-blue-600 underline text-sm">
            Back to templates
          </Link>
        </div>
      </div>
    );
  }

  const version = remote?.version ?? 1;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col">
      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-3 sticky top-0 z-30">
        <div className="max-w-[1400px] mx-auto flex items-center gap-3">
          <Link
            to="/admin/templates"
            className="text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
            aria-label="Back to templates"
          >
            <ArrowLeft size={18} />
          </Link>

          {/* Editable template name */}
          <input
            type="text"
            aria-label="Template name"
            value={name}
            onChange={(e) => { setName(e.target.value); markDirty(); }}
            className="flex-1 min-w-0 text-base font-semibold bg-transparent border-none outline-none text-gray-900 dark:text-white placeholder-gray-400"
            placeholder="Template name"
          />

          <div className="flex items-center gap-2 shrink-0">
            {/* Status badge */}
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
              isActive
                ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400'
                : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
            }`}>
              {isActive ? `Published v${version}` : 'Archived'}
            </span>

            {dirty && (
              <span className="text-xs text-amber-600 dark:text-amber-400 font-medium">
                Unsaved changes
              </span>
            )}

            {remote?.created_at && (
              <span className="text-xs text-gray-400 dark:text-gray-500 hidden lg:block">
                {new Date(remote.created_at).toLocaleDateString()}
              </span>
            )}

            {/* Language switcher */}
            <div className="flex items-center gap-1 border border-gray-200 dark:border-gray-700 rounded-lg p-0.5">
              {languages.map((lang) => (
                <button
                  key={lang}
                  type="button"
                  onClick={() => setLanguage(lang)}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                    language === lang
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                  }`}
                >
                  {lang}
                </button>
              ))}
              <button
                type="button"
                onClick={() => setShowAddLang(true)}
                className="px-1.5 py-1 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                aria-label="Add language"
              >
                <Plus size={13} />
              </button>
            </div>

            <button
              type="button"
              onClick={() => setShowDashPreview(true)}
              className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 flex items-center gap-1.5 transition-colors"
              aria-label="Preview dashboard"
              data-testid="dash-preview-btn"
            >
              <BarChart2 size={14} />
              Dashboard
            </button>

            <button
              type="button"
              onClick={() => handleSave(false)}
              disabled={!dirty || saving}
              className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              data-testid="save-btn"
            >
              {saving ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        </div>
      </header>

      {/* Validation errors banner */}
      {validationErrors.length > 0 && (
        <div className="bg-red-50 dark:bg-red-950/40 border-b border-red-200 dark:border-red-800 px-4 py-3">
          <div className="max-w-[1400px] mx-auto">
            <p className="text-sm font-medium text-red-700 dark:text-red-400 mb-1 flex items-center gap-1">
              <AlertTriangle size={14} /> Fix these before saving:
            </p>
            <ul className="list-disc list-inside space-y-0.5">
              {validationErrors.map((e, i) => (
                <li key={i} className="text-xs text-red-600 dark:text-red-400">{e}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Split-pane body */}
      <div className="flex-1 flex overflow-hidden max-w-[1400px] mx-auto w-full">
        {/* Left pane — ~58% */}
        <div className="flex-[58] min-w-0 border-r border-gray-200 dark:border-gray-700 flex overflow-hidden">
          {/* Field list */}
          <div className="w-52 lg:w-64 border-r border-gray-200 dark:border-gray-700 flex flex-col p-3 overflow-hidden">
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
              Fields ({fields.length})
            </p>
            <FieldList
              fields={fields}
              selectedId={selectedFieldId}
              onSelect={setSelectedFieldId}
              onReorder={handleReorder}
              onAddField={() => setShowTypePicker(true)}
              language={language}
              languages={languages}
            />
          </div>

          {/* Field inspector */}
          <div className="flex-1 min-w-0 p-4 overflow-hidden">
            <FieldInspector
              field={selectedField}
              onChange={handleFieldChange}
              onDelete={handleDeleteField}
              language={language}
              languages={languages}
            />
          </div>
        </div>

        {/* Right pane — ~42% */}
        <div className="flex-[42] min-w-0 overflow-y-auto p-5 space-y-5">
          <LivePreview
            schema={schemaWithIds}
            language={language}
            selectedFieldId={selectedFieldId}
          />

          {/* Versioning warning */}
          {responseCount > 0 ? (
            <div className="rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/30 px-4 py-3 text-sm text-amber-800 dark:text-amber-200 flex items-start gap-2">
              <AlertTriangle size={16} className="shrink-0 mt-0.5" />
              <span>
                {responseCount} response{responseCount !== 1 ? 's' : ''} on v{version}.
                Saving will publish this as v{version + 1}. v{version} stays available for existing data.
              </span>
            </div>
          ) : (
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              Editing v{version} in place.
            </p>
          )}
        </div>
      </div>

      {/* Modals */}
      <FieldTypePicker
        open={showTypePicker}
        onClose={() => setShowTypePicker(false)}
        onPick={handleAddField}
      />

      {showAddLang && (
        <AddLanguageModal
          existing={languages}
          onAdd={addLanguage}
          onClose={() => setShowAddLang(false)}
        />
      )}

      {showDashPreview && (
        <DashboardPreviewModal
          schemaFields={fields}
          language={language}
          onClose={() => setShowDashPreview(false)}
        />
      )}

      <Toast message={toast} onClose={() => setToast('')} />
    </div>
  );
}
