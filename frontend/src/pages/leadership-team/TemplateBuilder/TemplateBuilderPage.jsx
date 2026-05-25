/**
 * LT Template Builder — Step 7_12, Story 51.
 *
 * Tier 1 field types only: text, textarea, text_list, single_choice,
 * multiple_choice, rating_group. The builder uses the LT-scoped API
 * (``/api/v1/leadership-team/templates/``) which permits any LT
 * viewer; admins also see these templates via the existing admin
 * surface and can step in if needed.
 *
 * Edit-while-draft is in place; once responses exist, PATCH auto-
 * creates a new version (parent_template chain). Publish runs a
 * server-side validation pass for prompts/keys and surfaces warnings
 * inline.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import ReflectionField from '../../../components/templates/ReflectionField';
import {
  archiveTemplate,
  cloneTemplate,
  createTemplate,
  getTemplate,
  patchTemplate,
  publishTemplate,
} from '../../../api/leadershipTeam';
import { useAuth } from '../../../auth/AuthContext';

const TIER_1_TYPES = [
  { value: 'text', label: 'Short text' },
  { value: 'textarea', label: 'Long text' },
  { value: 'text_list', label: 'Text list' },
  { value: 'single_choice', label: 'Single choice' },
  { value: 'multiple_choice', label: 'Multiple choice' },
  { value: 'rating_group', label: 'Rating group' },
];

const SUPPORTED_LANGUAGES = ['en', 'es', 'he'];

let _localUid = 0;
const newLocalId = () => `lt_fid_${++_localUid}`;

/**
 * Derive a Django SlugField-friendly slug from a human name.
 *
 * The LT builder hides slugs from the LT user; we pick one for them
 * so the POST body always carries one (the backend rejects missing
 * slug with 400). A short base36 timestamp suffix avoids accidentally
 * appending a "v2" to someone else's template that happened to share
 * the same kebab-cased name in the same org.
 */
function deriveSlug(name) {
  const base = (name || '')
    .toString()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80) || 'lt-template';
  const suffix = Date.now().toString(36).slice(-6);
  return `${base}-${suffix}`;
}

function defaultsFor(type, lang = 'en') {
  const base = { _id: newLocalId(), type, key: '', required: true };
  if (type === 'rating_group' || type === 'single_rating') {
    return {
      ...base,
      prompts: { [lang]: '' },
      scale: [1, 5],
      scale_labels: { [lang]: ['1', '2', '3', '4', '5'] },
      categories: [],
    };
  }
  if (type === 'single_choice' || type === 'multiple_choice') {
    return { ...base, prompts: { [lang]: '' }, options: [] };
  }
  if (type === 'text_list') {
    return { ...base, prompts: { [lang]: '' }, min_items: 0, max_items: 5 };
  }
  return { ...base, prompts: { [lang]: '' }, max_length: type === 'textarea' ? 1000 : 200 };
}

function addLocalIds(fields) {
  return (fields || []).map((f) => ({ ...f, _id: f._id || newLocalId() }));
}

function stripLocalIds(fields) {
  return (fields || []).map(({ _id, ...rest }) => rest);
}

function clientValidate(template, fields) {
  const issues = [];
  const seenKeys = new Set();
  const languages = template.languages?.length ? template.languages : ['en'];
  if (!template.name?.trim()) issues.push('Template name is required.');
  fields.forEach((f, idx) => {
    const loc = `Field ${idx + 1}`;
    if (!f.key?.trim()) issues.push(`${loc}: key is required.`);
    else if (seenKeys.has(f.key)) issues.push(`${loc}: duplicate key "${f.key}".`);
    else seenKeys.add(f.key);
    for (const lang of languages) {
      if (!f.prompts?.[lang]) issues.push(`${loc}: missing "${lang}" prompt.`);
    }
    if ((f.type === 'single_choice' || f.type === 'multiple_choice') && !(f.options?.length > 0)) {
      issues.push(`${loc}: add at least one option.`);
    }
    if (f.type === 'rating_group' && !(f.categories?.length > 0)) {
      issues.push(`${loc}: add at least one category.`);
    }
  });
  return issues;
}

function FieldEditor({ field, languages, onChange, onRemove }) {
  const update = (patch) => onChange({ ...field, ...patch });
  const updatePrompt = (lang, value) =>
    update({ prompts: { ...(field.prompts || {}), [lang]: value } });

  return (
    <div
      className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3 min-w-0 overflow-hidden"
      data-testid={`lt-fld-${field._id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
        <div className="flex flex-wrap items-center gap-2 min-w-0 flex-1">
          <select
            value={field.type}
            onChange={(e) => update({ type: e.target.value })}
            className="text-sm rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 max-w-full"
            data-testid={`lt-fld-type-${field._id}`}
          >
            {TIER_1_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <input
            type="text"
            value={field.key}
            onChange={(e) => update({ key: e.target.value })}
            placeholder="field_key"
            className="text-sm rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 min-w-[8rem] flex-1 max-w-full"
            data-testid={`lt-fld-key-${field._id}`}
          />
          <label className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 shrink-0">
            <input
              type="checkbox"
              checked={!!field.required}
              onChange={(e) => update({ required: e.target.checked })}
            />
            required
          </label>
        </div>
        <button
          type="button"
          onClick={onRemove}
          className="text-xs rounded-md border border-red-300 text-red-600 hover:bg-red-50 px-2 py-1 shrink-0"
          data-testid={`lt-fld-remove-${field._id}`}
        >
          Remove
        </button>
      </div>

      <div className="space-y-2">
        {languages.map((lang) => (
          <label key={lang} className="block text-xs text-gray-700 dark:text-gray-300">
            Prompt ({lang})
            <input
              type="text"
              value={field.prompts?.[lang] ?? ''}
              onChange={(e) => updatePrompt(lang, e.target.value)}
              className="mt-1 w-full text-sm rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700"
              data-testid={`lt-fld-prompt-${field._id}-${lang}`}
            />
          </label>
        ))}

        {(field.type === 'single_choice' || field.type === 'multiple_choice') && (
          <OptionsEditor
            options={field.options || []}
            languages={languages}
            onChange={(options) => update({ options })}
            fieldId={field._id}
          />
        )}

        {field.type === 'rating_group' && (
          <CategoriesEditor
            categories={field.categories || []}
            languages={languages}
            onChange={(categories) => update({ categories })}
            fieldId={field._id}
          />
        )}
      </div>
    </div>
  );
}

function OptionsEditor({ options, languages, onChange, fieldId }) {
  const addOption = () => onChange([
    ...options,
    { key: '', labels: Object.fromEntries(languages.map((l) => [l, ''])) },
  ]);
  const updateOption = (idx, patch) => onChange(options.map((o, i) => i === idx ? { ...o, ...patch } : o));
  const removeOption = (idx) => onChange(options.filter((_, i) => i !== idx));
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Options</p>
      {options.map((o, idx) => (
        <div
          key={idx}
          className="rounded-md border border-gray-100 dark:border-gray-700 p-2 space-y-2"
          data-testid={`lt-opt-${fieldId}-${idx}`}
        >
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              value={o.key}
              onChange={(e) => updateOption(idx, { key: e.target.value })}
              placeholder="option_key"
              className="text-xs rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 w-full sm:w-32"
            />
            <button
              type="button"
              onClick={() => removeOption(idx)}
              className="text-xs text-red-600 hover:underline sm:ml-auto"
            >
              Remove
            </button>
          </div>
          {languages.map((lang) => (
            <input
              key={lang}
              type="text"
              value={o.labels?.[lang] ?? ''}
              onChange={(e) => updateOption(idx, { labels: { ...(o.labels || {}), [lang]: e.target.value } })}
              placeholder={`label (${lang})`}
              className="text-xs rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 w-full"
            />
          ))}
        </div>
      ))}
      <button
        type="button"
        onClick={addOption}
        className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
        data-testid={`lt-opt-add-${fieldId}`}
      >
        + Add option
      </button>
    </div>
  );
}

function CategoriesEditor({ categories, languages, onChange, fieldId }) {
  const add = () => onChange([
    ...categories,
    { key: '', labels: Object.fromEntries(languages.map((l) => [l, ''])) },
  ]);
  const update = (idx, patch) => onChange(categories.map((c, i) => i === idx ? { ...c, ...patch } : c));
  const remove = (idx) => onChange(categories.filter((_, i) => i !== idx));
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Categories</p>
      {categories.map((c, idx) => (
        <div
          key={idx}
          className="rounded-md border border-gray-100 dark:border-gray-700 p-2 space-y-2"
          data-testid={`lt-cat-${fieldId}-${idx}`}
        >
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              value={c.key}
              onChange={(e) => update(idx, { key: e.target.value })}
              placeholder="category_key"
              className="text-xs rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 w-full sm:w-32"
            />
            <button
              type="button"
              onClick={() => remove(idx)}
              className="text-xs text-red-600 hover:underline sm:ml-auto"
            >
              Remove
            </button>
          </div>
          {languages.map((lang) => (
            <input
              key={lang}
              type="text"
              value={c.labels?.[lang] ?? ''}
              onChange={(e) => update(idx, { labels: { ...(c.labels || {}), [lang]: e.target.value } })}
              placeholder={`label (${lang})`}
              className="text-xs rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 w-full"
            />
          ))}
        </div>
      ))}
      <button
        type="button"
        onClick={add}
        className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
        data-testid={`lt-cat-add-${fieldId}`}
      >
        + Add category
      </button>
    </div>
  );
}

function PreviewPane({ template, fields, previewLanguage }) {
  return (
    <div className="space-y-4 min-w-0">
      {fields.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="lt-builder-preview-empty">
          Add a field to see a preview.
        </p>
      ) : (
        fields.map((field) => (
          <div key={field._id} data-testid={`lt-preview-${field._id}`}>
            <ReflectionField
              field={field}
              answer={undefined}
              onChange={() => {}}
              language={previewLanguage}
            />
          </div>
        ))
      )}
    </div>
  );
}

export default function TemplateBuilderPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { orgSlug } = useAuth();
  const isEdit = Boolean(id);

  const [template, setTemplate] = useState({
    name: '',
    role: 'leadership_team',
    languages: ['en'],
    cadence: 'biweekly',
    status: 'draft',
    schema: { fields: [] },
    is_active: true,
    version: 1,
  });
  const [fields, setFields] = useState([]);
  const [loading, setLoading] = useState(isEdit);
  const [error, setError] = useState('');
  const [warnings, setWarnings] = useState([]);
  const [saving, setSaving] = useState(false);
  const [previewLanguage, setPreviewLanguage] = useState('en');
  const [dirty, setDirty] = useState(false);
  const [showForceVersion, setShowForceVersion] = useState(false);
  const dirtyRef = useRef(false);
  dirtyRef.current = dirty;

  const load = useCallback(async () => {
    if (!isEdit) return;
    setLoading(true);
    try {
      const data = await getTemplate(orgSlug, id);
      setTemplate({
        id: data.id,
        name: data.name ?? '',
        role: data.role ?? 'leadership_team',
        languages: data.languages?.length ? data.languages : ['en'],
        cadence: data.cadence ?? 'biweekly',
        status: data.status ?? (data.is_active ? 'published' : 'archived'),
        schema: data.schema ?? { fields: [] },
        is_active: data.is_active,
        version: data.version ?? 1,
        slug: data.slug,
      });
      setFields(addLocalIds(data.schema?.fields ?? []));
      setPreviewLanguage(data.languages?.[0] ?? 'en');
    } catch (err) {
      if (err?.response?.status === 403) setError('You cannot edit this template.');
      else setError('Failed to load template.');
    } finally {
      setLoading(false);
    }
  }, [isEdit, orgSlug, id]);

  useEffect(() => { load(); }, [load]);

  const updateTemplate = (patch) => {
    setTemplate((prev) => ({ ...prev, ...patch }));
    setDirty(true);
  };

  const updateFields = (next) => {
    setFields(next);
    setDirty(true);
  };

  const onAddField = (type) => {
    updateFields([...fields, defaultsFor(type, template.languages[0] ?? 'en')]);
  };

  const onFieldChange = (idx, next) => {
    updateFields(fields.map((f, i) => i === idx ? next : f));
  };

  const onFieldRemove = (idx) => {
    updateFields(fields.filter((_, i) => i !== idx));
  };

  const move = (idx, direction) => {
    const target = idx + direction;
    if (target < 0 || target >= fields.length) return;
    const next = [...fields];
    [next[idx], next[target]] = [next[target], next[idx]];
    updateFields(next);
  };

  const validationIssues = useMemo(
    () => clientValidate(template, fields),
    [template, fields],
  );

  const buildPayload = () => {
    const payload = {
      name: template.name,
      role: template.role,
      languages: template.languages,
      cadence: template.cadence,
      schema: { fields: stripLocalIds(fields) },
    };
    if (!isEdit) {
      payload.slug = template.slug || deriveSlug(template.name);
    } else if (template.slug) {
      payload.slug = template.slug;
    }
    return payload;
  };

  const save = async ({ forceNewVersion = false } = {}) => {
    setError('');
    setWarnings([]);
    if (validationIssues.length > 0) {
      setError(validationIssues.join(' · '));
      return null;
    }
    setSaving(true);
    try {
      const payload = buildPayload();
      if (isEdit) {
        const data = await patchTemplate(orgSlug, id, payload, { forceNewVersion });
        if (data?.warnings?.length) setWarnings(data.warnings);
        if (data?.id && data.id !== Number(id)) {
          navigate(`/leadership-team/templates/${data.id}`);
          return data;
        }
        await load();
        setDirty(false);
        return data;
      }
      const created = await createTemplate(orgSlug, payload);
      if (created?.id) {
        navigate(`/leadership-team/templates/${created.id}`);
      }
      return created;
    } catch (err) {
      const status = err?.response?.status;
      if (status === 409) {
        setShowForceVersion(true);
        setError(err?.response?.data?.detail ?? 'Responses exist on this template — confirm a new version.');
        return null;
      }
      const detail = err?.response?.data?.errors
        ?? err?.response?.data?.detail
        ?? 'Failed to save template.';
      setError(Array.isArray(detail) ? detail.join(' · ') : (typeof detail === 'string' ? detail : JSON.stringify(detail)));
      return null;
    } finally {
      setSaving(false);
    }
  };

  const doPublish = async () => {
    if (dirtyRef.current) {
      const saved = await save();
      if (!saved) return;
    }
    setSaving(true);
    setError('');
    setWarnings([]);
    try {
      const data = await publishTemplate(orgSlug, id);
      if (data?.warnings?.length) setWarnings(data.warnings);
      await load();
    } catch (err) {
      if (err?.response?.status === 409) {
        setWarnings(err.response.data?.warnings ?? []);
        setError('Resolve warnings before publishing.');
      } else {
        setError(err?.response?.data?.detail ?? 'Publish failed.');
      }
    } finally {
      setSaving(false);
    }
  };

  const doArchive = async () => {
    setSaving(true);
    try {
      await archiveTemplate(orgSlug, id);
      navigate('/leadership-team/templates');
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Archive failed.');
    } finally {
      setSaving(false);
    }
  };

  const doClone = async () => {
    setSaving(true);
    try {
      const cloned = await cloneTemplate(orgSlug, id);
      if (cloned?.id) navigate(`/leadership-team/templates/${cloned.id}`);
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Clone failed.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen" data-testid="lt-builder-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  const status = template.status ?? 'draft';
  const isPublished = status === 'published';
  const isArchived = status === 'archived';

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <div className="flex-1 min-w-0">
            <Link
              to="/leadership-team/templates"
              className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
            >
              ← Template library
            </Link>
            <div className="flex items-center gap-2 mt-1">
              <input
                type="text"
                value={template.name}
                onChange={(e) => updateTemplate({ name: e.target.value })}
                placeholder="Template name"
                disabled={isArchived}
                className="text-lg font-semibold text-gray-900 dark:text-white bg-transparent border-b border-gray-200 dark:border-gray-700 focus:outline-none flex-1 min-w-0"
                data-testid="lt-builder-name"
              />
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200">
                {status} v{template.version}
              </span>
            </div>
          </div>
          <div className="flex gap-2 shrink-0">
            <button
              type="button"
              onClick={() => save()}
              disabled={saving || isArchived}
              className="text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-3 py-1.5"
              data-testid="lt-builder-save"
            >
              {saving ? 'Saving…' : isEdit ? 'Save' : 'Save draft'}
            </button>
            {isEdit && !isPublished && !isArchived && (
              <button
                type="button"
                onClick={doPublish}
                disabled={saving}
                className="text-sm rounded-lg bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white px-3 py-1.5"
                data-testid="lt-builder-publish"
              >
                Publish
              </button>
            )}
            {isEdit && isPublished && (
              <button
                type="button"
                onClick={doArchive}
                disabled={saving}
                className="text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1.5"
                data-testid="lt-builder-archive"
              >
                Archive
              </button>
            )}
            {isEdit && (
              <button
                type="button"
                onClick={doClone}
                disabled={saving}
                className="text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1.5"
                data-testid="lt-builder-clone"
              >
                Clone
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 grid grid-cols-1 xl:grid-cols-12 gap-4">
        <section className="xl:col-span-3 min-w-0 space-y-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">Settings</h2>
          <label className="block text-sm text-gray-700 dark:text-gray-300">
            Role
            <select
              value={template.role}
              onChange={(e) => updateTemplate({ role: e.target.value })}
              disabled={isArchived}
              className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
              data-testid="lt-builder-role"
            >
              {[
                'counselor', 'specialist', 'unit_head', 'leadership_team',
                'kitchen_staff', 'maintenance', 'housekeeping', 'camper_care',
                'health_center', 'madrich', 'general_counselor', 'faculty',
              ].map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </label>
          <label className="block text-sm text-gray-700 dark:text-gray-300">
            Cadence
            <select
              value={template.cadence}
              onChange={(e) => updateTemplate({ cadence: e.target.value })}
              disabled={isArchived}
              className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
              data-testid="lt-builder-cadence"
            >
              {['daily', 'weekly', 'biweekly', 'monthly', 'on_demand'].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </label>
          <fieldset className="border border-gray-200 dark:border-gray-700 rounded-md p-2">
            <legend className="text-xs text-gray-500 dark:text-gray-400 px-1">Languages</legend>
            {SUPPORTED_LANGUAGES.map((lang) => (
              <label key={lang} className="flex items-center gap-1 text-sm text-gray-700 dark:text-gray-300">
                <input
                  type="checkbox"
                  checked={template.languages.includes(lang)}
                  disabled={isArchived}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...new Set([...template.languages, lang])]
                      : template.languages.filter((l) => l !== lang);
                    updateTemplate({ languages: next.length ? next : ['en'] });
                  }}
                  data-testid={`lt-builder-lang-${lang}`}
                />
                {lang}
              </label>
            ))}
          </fieldset>
          <label className="block text-sm text-gray-700 dark:text-gray-300">
            Preview language
            <select
              value={previewLanguage}
              onChange={(e) => setPreviewLanguage(e.target.value)}
              className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
              data-testid="lt-builder-preview-lang"
            >
              {template.languages.map((lang) => (
                <option key={lang} value={lang}>{lang}</option>
              ))}
            </select>
          </label>
        </section>

        <section className="xl:col-span-5 min-w-0 space-y-3" aria-label="Fields">
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3 min-w-0 overflow-hidden">
            <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
              Fields
            </h2>
            <div className="flex flex-wrap gap-1 mb-3">
              {TIER_1_TYPES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => onAddField(t.value)}
                  disabled={isArchived}
                  className="text-xs rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                  data-testid={`lt-builder-add-${t.value}`}
                >
                  + {t.label}
                </button>
              ))}
            </div>
            <div className="space-y-2" data-testid="lt-builder-fields">
              {fields.map((field, idx) => (
                <div key={field._id} className="flex items-stretch gap-1">
                  <div className="flex flex-col gap-1 shrink-0">
                    <button
                      type="button"
                      onClick={() => move(idx, -1)}
                      disabled={idx === 0 || isArchived}
                      className="text-xs rounded border border-gray-300 dark:border-gray-600 px-1 text-gray-500 disabled:opacity-30"
                      data-testid={`lt-builder-up-${field._id}`}
                      aria-label="Move up"
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      onClick={() => move(idx, 1)}
                      disabled={idx === fields.length - 1 || isArchived}
                      className="text-xs rounded border border-gray-300 dark:border-gray-600 px-1 text-gray-500 disabled:opacity-30"
                      data-testid={`lt-builder-down-${field._id}`}
                      aria-label="Move down"
                    >
                      ↓
                    </button>
                  </div>
                  <div className="flex-1 min-w-0">
                    <FieldEditor
                      field={field}
                      languages={template.languages}
                      onChange={(next) => onFieldChange(idx, next)}
                      onRemove={() => onFieldRemove(idx)}
                    />
                  </div>
                </div>
              ))}
              {fields.length === 0 && (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-6" data-testid="lt-builder-empty">
                  No fields yet — add one above.
                </p>
              )}
            </div>
          </div>

          {validationIssues.length > 0 && (
            <div
              className="rounded-md border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-2 text-xs text-amber-900 dark:text-amber-200"
              data-testid="lt-builder-issues"
            >
              <p className="font-medium mb-1">Issues:</p>
              <ul className="list-disc list-inside space-y-0.5">
                {validationIssues.map((iss) => <li key={iss}>{iss}</li>)}
              </ul>
            </div>
          )}

          {warnings.length > 0 && (
            <div
              className="rounded-md border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-2 text-xs text-amber-900 dark:text-amber-200"
              data-testid="lt-builder-warnings"
            >
              <p className="font-medium mb-1">Warnings:</p>
              <ul className="list-disc list-inside space-y-0.5">
                {warnings.map((w) => <li key={w}>{w}</li>)}
              </ul>
            </div>
          )}

          {error && (
            <div
              className="rounded-md border border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20 p-2 text-xs text-red-700 dark:text-red-300"
              data-testid="lt-builder-error"
            >
              {error}
              {showForceVersion && (
                <button
                  type="button"
                  onClick={() => { setShowForceVersion(false); save({ forceNewVersion: true }); }}
                  className="ml-2 text-xs rounded-md bg-red-600 hover:bg-red-700 text-white px-2 py-1"
                  data-testid="lt-builder-force-version"
                >
                  Create new version
                </button>
              )}
            </div>
          )}
        </section>

        <section
          className="xl:col-span-4 min-w-0 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 xl:sticky xl:top-24 xl:self-start xl:max-h-[calc(100vh-7rem)] xl:overflow-y-auto"
          aria-label="Preview"
          data-testid="lt-builder-preview"
        >
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold text-gray-900 dark:text-white">Preview</h2>
            <span className="text-xs text-gray-500 dark:text-gray-400">{previewLanguage}</span>
          </div>
          <PreviewPane template={template} fields={fields} previewLanguage={previewLanguage} />
        </section>
      </main>
    </div>
  );
}
