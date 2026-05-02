import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api';
import {
  validateReflectionAnswers,
  buildDefaultAnswers,
  ratingScaleValues,
  localizedOptionLabel,
} from '../utils/reflection/reflectionFormValidation';
import {
  reflectionDraftKey,
  loadReflectionDraft,
  saveReflectionDraft,
  clearReflectionDraft,
} from '../utils/reflection/reflectionDraftStorage';

function promptText(field) {
  if (!field.prompts || typeof field.prompts !== 'object') return '';
  const v = Object.values(field.prompts)[0];
  return typeof v === 'string' ? v : '';
}

function categoryLabel(cat) {
  if (!cat.labels || typeof cat.labels !== 'object') return cat.key || '';
  const v = Object.values(cat.labels)[0];
  return typeof v === 'string' ? v : cat.key || '';
}

function scaleLabelsList(field) {
  if (!field.scale_labels || typeof field.scale_labels !== 'object') return [];
  const row = Object.values(field.scale_labels)[0];
  return Array.isArray(row) ? row : [];
}

function mergeAnswers(defaults, draftAnswers) {
  if (!draftAnswers || typeof draftAnswers !== 'object') return defaults;
  return { ...defaults, ...draftAnswers };
}

export default function ReflectionFormPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const programParam = searchParams.get('program') || '';
  const roleParam = searchParams.get('role') || '';

  const [language, setLanguage] = useState('en');
  const [meta, setMeta] = useState(null);
  const [schema, setSchema] = useState(null);
  const [programSlug, setProgramSlug] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [answers, setAnswers] = useState({});
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const draftKey = useMemo(() => {
    if (!meta?.id || !periodStart || !periodEnd) return null;
    return reflectionDraftKey(meta.id, periodStart, periodEnd);
  }, [meta?.id, periodStart, periodEnd]);

  const fetchTemplate = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const params = { language };
      if (programParam) params.program = programParam;
      if (roleParam) params.role = roleParam;
      const { data } = await api.get('/api/v1/reflections/template-for-me/', { params });
      setMeta({
        id: data.id,
        name: data.name,
        cadence: data.cadence,
        languages: data.languages || [],
      });
      setSchema(data.schema);
      setProgramSlug(data.program_slug || '');
      setAnswers(buildDefaultAnswers(data.schema));
    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      const msg =
        typeof detail === 'string'
          ? detail
          : status === 403
            ? 'You do not have access to reflections for this organization.'
            : status === 404
              ? 'No reflection template is available for your role or program.'
              : 'Could not load reflection template.';
      setLoadError(msg);
      setMeta(null);
      setSchema(null);
      setProgramSlug('');
      setAnswers({});
    } finally {
      setLoading(false);
    }
  }, [language, programParam, roleParam]);

  useEffect(() => {
    fetchTemplate();
  }, [fetchTemplate]);

  useEffect(() => {
    if (!meta?.id || !schema || !periodStart || !periodEnd) return;
    const key = reflectionDraftKey(meta.id, periodStart, periodEnd);
    const draft = loadReflectionDraft(key);
    const defaults = buildDefaultAnswers(schema);
    setAnswers((prev) => {
      if (draft?.answers && typeof draft.answers === 'object') {
        return mergeAnswers(defaults, draft.answers);
      }
      return mergeAnswers(defaults, prev);
    });
  }, [meta?.id, schema, periodStart, periodEnd]);

  useEffect(() => {
    if (!draftKey || !schema) return;
    const t = setTimeout(() => {
      saveReflectionDraft(draftKey, { answers, updatedAt: Date.now() });
    }, 300);
    return () => clearTimeout(t);
  }, [answers, draftKey, schema]);

  const updateAnswer = (key, value) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const renderField = (field) => {
    const err = fieldErrors[field.key];
    const commonLabel = (
      <label className="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-1">
        {field.type === 'rating_group' ? null : promptText(field)}
      </label>
    );

    if (field.type === 'text') {
      return (
        <div key={field.key} className="mb-5">
          {commonLabel}
          <input
            type="text"
            data-testid={`reflect-input-${field.key}`}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            value={answers[field.key] ?? ''}
            onChange={(e) => updateAnswer(field.key, e.target.value)}
          />
          {err ? <p className="text-red-600 text-xs mt-1">{err}</p> : null}
        </div>
      );
    }

    if (field.type === 'textarea') {
      const v = answers[field.key] ?? '';
      const max = field.max_length;
      return (
        <div key={field.key} className="mb-5">
          {commonLabel}
          <textarea
            rows={4}
            data-testid={`reflect-input-${field.key}`}
            maxLength={typeof max === 'number' ? max : undefined}
            className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            value={v}
            onChange={(e) => updateAnswer(field.key, e.target.value)}
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>{err || ''}</span>
            {typeof max === 'number' ? (
              <span>
                {v.length}/{max}
              </span>
            ) : (
              <span>{v.length} characters</span>
            )}
          </div>
        </div>
      );
    }

    if (field.type === 'text_list') {
      const items = Array.isArray(answers[field.key]) ? [...answers[field.key]] : [];
      const maxItems = typeof field.max_items === 'number' ? field.max_items : 12;
      const minItems = typeof field.min_items === 'number' ? field.min_items : 1;
      return (
        <div key={field.key} className="mb-5">
          {commonLabel}
          <div className="space-y-2">
            {items.map((line, idx) => (
              <input
                key={idx}
                type="text"
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                value={line}
                onChange={(e) => {
                  const next = [...items];
                  next[idx] = e.target.value;
                  updateAnswer(field.key, next);
                }}
              />
            ))}
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            {items.length < maxItems ? (
              <button
                type="button"
                className="text-sm text-blue-600 dark:text-blue-400"
                onClick={() => updateAnswer(field.key, [...items, ''])}
              >
                + Add line
              </button>
            ) : null}
            {items.length > minItems ? (
              <button
                type="button"
                className="text-sm text-gray-600 dark:text-gray-400"
                onClick={() => updateAnswer(field.key, items.slice(0, -1))}
              >
                Remove last
              </button>
            ) : null}
          </div>
          {err ? <p className="text-red-600 text-xs mt-1">{err}</p> : null}
        </div>
      );
    }

    if (field.type === 'rating_group') {
      const scale = ratingScaleValues(field);
      const labels = scaleLabelsList(field);
      const val = answers[field.key] && typeof answers[field.key] === 'object' ? answers[field.key] : {};
      const heading = promptText(field) || 'Ratings';
      return (
        <div key={field.key} className="mb-6">
          <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">{heading}</p>
          <div className="space-y-3">
            {(field.categories || []).map((cat) => (
              <div key={cat.key}>
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">{categoryLabel(cat)}</p>
                <div className="flex flex-wrap gap-2">
                  {scale.map((n, idx) => {
                    const label = labels[idx] ?? String(n);
                    const selected = val[cat.key] === n || val[cat.key] === String(n);
                    return (
                      <button
                        key={String(n)}
                        type="button"
                        title={label}
                        onClick={() =>
                          updateAnswer(field.key, {
                            ...val,
                            [cat.key]: n,
                          })
                        }
                        className={`min-h-[44px] min-w-[44px] px-3 rounded-lg border text-sm font-medium transition-colors ${
                          selected
                            ? 'border-blue-600 bg-blue-600 text-white'
                            : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100'
                        }`}
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
          {err ? <p className="text-red-600 text-xs mt-1">{err}</p> : null}
        </div>
      );
    }

    const options = Array.isArray(field.options) ? field.options : [];

    if (field.type === 'single_choice') {
      const v = answers[field.key] ?? '';
      return (
        <div key={field.key} className="mb-5">
          {commonLabel}
          <div className="space-y-2">
            {options.map((opt) => (
              <label key={opt.key} className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="radio"
                  name={`choice_${field.key}`}
                  checked={v === opt.key}
                  onChange={() => updateAnswer(field.key, opt.key)}
                />
                <span>{localizedOptionLabel(opt, opt.key)}</span>
              </label>
            ))}
          </div>
          {err ? <p className="text-red-600 text-xs mt-1">{err}</p> : null}
        </div>
      );
    }

    if (field.type === 'multiple_choice') {
      const v = Array.isArray(answers[field.key]) ? answers[field.key] : [];
      const toggle = (key) => {
        if (v.includes(key)) updateAnswer(field.key, v.filter((x) => x !== key));
        else updateAnswer(field.key, [...v, key]);
      };
      return (
        <div key={field.key} className="mb-5">
          {commonLabel}
          <div className="space-y-2">
            {options.map((opt) => (
              <label key={opt.key} className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={v.includes(opt.key)} onChange={() => toggle(opt.key)} />
                <span>{localizedOptionLabel(opt, opt.key)}</span>
              </label>
            ))}
          </div>
          {err ? <p className="text-red-600 text-xs mt-1">{err}</p> : null}
        </div>
      );
    }

    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');
    if (!schema || !meta?.id || !programSlug) {
      setSubmitError('Template not loaded.');
      return;
    }
    if (!periodStart || !periodEnd) {
      setSubmitError('Choose a period start and end date.');
      return;
    }
    if (periodEnd < periodStart) {
      setSubmitError('Period end must be on or after period start.');
      return;
    }

    const { ok, errors } = validateReflectionAnswers(schema, answers);
    setFieldErrors(errors);
    if (!ok) return;

    setSubmitting(true);
    try {
      const { data } = await api.post('/api/v1/reflections/', {
        program_slug: programSlug,
        template: meta.id,
        period_start: periodStart,
        period_end: periodEnd,
        answers,
        language,
      });
      if (draftKey) clearReflectionDraft(draftKey);
      navigate('/reflect/summary', {
        replace: true,
        state: {
          reflectionId: data.id,
          templateName: meta.name,
          periodStart,
          periodEnd,
          language,
          schema,
          answers: data.answers || answers,
        },
      });
    } catch (err) {
      const body = err.response?.data;
      const detail =
        typeof body?.detail === 'string'
          ? body.detail
          : body && typeof body === 'object'
            ? JSON.stringify(body)
            : err.message;
      setSubmitError(detail || 'Submit failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const langChoices = meta?.languages?.length ? meta.languages : ['en', 'es'];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 px-4 py-6 pb-24">
      <div className="max-w-lg mx-auto">
        <header className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Reflection</h1>
            {meta ? (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{meta.name}</p>
            ) : null}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs text-gray-500 uppercase tracking-wide">Language</span>
            <div className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
              {langChoices.map((code) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => setLanguage(code)}
                  className={`px-3 py-1.5 text-sm font-medium min-h-[44px] ${
                    language === code
                      ? 'bg-blue-600 text-white'
                      : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200'
                  }`}
                >
                  {code === 'es' ? 'Español' : code === 'en' ? 'English' : code}
                </button>
              ))}
            </div>
          </div>
        </header>

        {loading ? (
          <p className="text-gray-600 dark:text-gray-400">Loading form…</p>
        ) : loadError ? (
          <div
            className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-800 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
            role="alert"
          >
            {loadError}
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  Period start
                </label>
                <input
                  type="date"
                  data-testid="reflect-period-start"
                  required
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                  value={periodStart}
                  onChange={(e) => setPeriodStart(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  Period end
                </label>
                <input
                  type="date"
                  data-testid="reflect-period-end"
                  required
                  className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                  value={periodEnd}
                  onChange={(e) => setPeriodEnd(e.target.value)}
                />
              </div>
            </div>

            {(schema?.fields || []).map((field) => renderField(field))}

            {submitError ? (
              <p className="text-red-600 text-sm" role="alert">
                {submitError}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={submitting}
              className="w-full sm:w-auto mt-4 min-h-[48px] px-6 rounded-lg bg-blue-600 text-white font-medium text-sm disabled:opacity-50"
            >
              {submitting ? 'Submitting…' : 'Submit reflection'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
