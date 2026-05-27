import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../api';
import ReflectionField from '../components/templates/ReflectionField';
import {
  validateReflectionAnswers,
  buildDefaultAnswers,
} from '../utils/reflection/reflectionFormValidation';
import {
  reflectionDraftKey,
  loadReflectionDraft,
  saveReflectionDraft,
  clearReflectionDraft,
} from '../utils/reflection/reflectionDraftStorage';

function mergeAnswers(defaults, draftAnswers) {
  if (!draftAnswers || typeof draftAnswers !== 'object') return defaults;
  return { ...defaults, ...draftAnswers };
}

export default function ReflectionFormPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const programParam = searchParams.get('program') || '';
  const roleParam = searchParams.get('role') || '';

  // Pre-fill params from tasks home screen
  const templateParam = searchParams.get('template') || '';
  const assignmentGroupParam = searchParams.get('assignment_group') || '';
  const subjectParam = searchParams.get('subject') || '';
  const subjectGroupParam = searchParams.get('subject_group') || '';
  const subjectNameParam = searchParams.get('subject_name') || '';
  const periodStartParam = searchParams.get('period_start') || '';
  const periodEndParam = searchParams.get('period_end') || '';

  const isPrefilled = Boolean(templateParam && programParam);

  const [language, setLanguage] = useState('en');
  const [meta, setMeta] = useState(null);
  const [schema, setSchema] = useState(null);
  const [programSlug, setProgramSlug] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [answers, setAnswers] = useState({});
  const [periodStart, setPeriodStart] = useState(periodStartParam);
  const [periodEnd, setPeriodEnd] = useState(periodEndParam);
  const [teamVisibility, setTeamVisibility] = useState('team');
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const draftKey = useMemo(() => {
    const subjectKey = subjectParam ? `_s${subjectParam}` : '';
    const groupKey = assignmentGroupParam ? `_g${assignmentGroupParam}` : '';
    if (!meta?.id || !periodStart || !periodEnd) return null;
    return reflectionDraftKey(`${meta.id}${subjectKey}${groupKey}`, periodStart, periodEnd);
  }, [meta?.id, periodStart, periodEnd, subjectParam, assignmentGroupParam]);

  const fetchTemplate = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const params = { language };
      if (programParam) params.program = programParam;
      if (templateParam) params.template = templateParam;
      else if (roleParam) params.role = roleParam;
      const { data } = await api.get('/api/v1/reflections/template-for-me/', { params });
      setMeta({
        id: data.id,
        name: data.name,
        cadence: data.cadence,
        languages: data.languages || [],
        subject_mode: data.subject_mode || 'self',
        supports_privacy: Boolean(data.supports_privacy),
      });
      setSchema(data.schema);
      setProgramSlug(data.program_slug || '');
      setAnswers(buildDefaultAnswers(data.schema));
    } catch (err) {
      const httpStatus = err.response?.status;
      const detail = err.response?.data?.detail;
      const msg =
        typeof detail === 'string'
          ? detail
          : httpStatus === 403
            ? 'You do not have access to reflections for this organization.'
            : httpStatus === 404
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
  }, [language, programParam, roleParam, templateParam]);

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
    if (meta?.supports_privacy && (draft?.teamVisibility === 'supervisors_only' || draft?.teamVisibility === 'team')) {
      setTeamVisibility(draft.teamVisibility);
    } else if (!meta?.supports_privacy) {
      setTeamVisibility('team');
    }
  }, [meta?.id, meta?.supports_privacy, schema, periodStart, periodEnd]);

  useEffect(() => {
    if (!draftKey || !schema) return;
    const t = setTimeout(() => {
      saveReflectionDraft(draftKey, { answers, teamVisibility, updatedAt: Date.now() });
    }, 300);
    return () => clearTimeout(t);
  }, [answers, teamVisibility, draftKey, schema]);

  const updateAnswer = (key, value) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const renderField = (field) => (
    <ReflectionField
      key={field.key}
      field={field}
      language={language}
      answer={answers[field.key]}
      onChange={(val) => updateAnswer(field.key, val)}
      error={fieldErrors[field.key]}
    />
  );

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
      const payload = {
        program_slug: programSlug,
        template: meta.id,
        period_start: periodStart,
        period_end: periodEnd,
        answers,
        language,
      };
      if (meta?.supports_privacy) {
        payload.team_visibility = teamVisibility;
      }
      if (subjectParam) payload.subject = Number(subjectParam);
      if (assignmentGroupParam) payload.assignment_group = Number(assignmentGroupParam);
      if (subjectGroupParam) payload.subject_group = Number(subjectGroupParam);

      const { data } = await api.post('/api/v1/reflections/', payload);
      if (draftKey) clearReflectionDraft(draftKey);
      navigate('/reflect/summary', {
        replace: true,
        state: {
          reflectionId: data.id,
          templateName: meta.name,
          subjectName: subjectNameParam || null,
          periodStart,
          periodEnd,
          language,
          schema,
          answers: data.answers || answers,
          returnTo: isPrefilled ? '/tasks' : null,
          teamVisibility: meta?.supports_privacy ? teamVisibility : 'team',
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
    <div className="px-4 sm:px-6 lg:px-8 py-8 pb-24 w-full max-w-[96rem] mx-auto">
        <header className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            {isPrefilled && (
              <button
                type="button"
                onClick={() => navigate('/tasks')}
                className="text-xs text-blue-600 dark:text-blue-400 mb-1 flex items-center gap-1"
              >
                ← Back to tasks
              </button>
            )}
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
              {subjectNameParam ? `About ${subjectNameParam}` : 'Reflection'}
            </h1>
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

            {meta?.supports_privacy ? (
            <fieldset
              className="mb-4 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-3"
              data-testid="reflect-visibility"
            >
              <legend className="text-xs font-medium text-gray-600 dark:text-gray-400 px-1">
                Visible to
              </legend>
              <div className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden mt-1">
                {[
                  { value: 'team', label: 'My team' },
                  { value: 'supervisors_only', label: 'Supervisors only' },
                ].map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    aria-pressed={teamVisibility === opt.value}
                    data-testid={`reflect-visibility-${opt.value}`}
                    onClick={() => setTeamVisibility(opt.value)}
                    className={`flex-1 px-3 py-2 text-sm font-medium min-h-[44px] ${
                      teamVisibility === opt.value
                        ? 'bg-blue-600 text-white'
                        : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              {teamVisibility === 'supervisors_only' ? (
                <p
                  className="mt-2 text-xs text-gray-600 dark:text-gray-400"
                  data-testid="reflect-visibility-helper"
                >
                  Hidden from peer authors. Unit Heads, Camper Care, and admins can still see this entry.
                </p>
              ) : null}
            </fieldset>
            ) : null}

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
  );
}
