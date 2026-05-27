/**
 * Unit Head self-reflection form — Step 7_7, Stories 16 + 17 (edit).
 *
 * Mirrors `CounselorSelfReflectionPage`:
 *
 *   /unit-head/self-reflection
 *     → POST. If today's reflection already exists, redirect to edit URL.
 *   /unit-head/self-reflection/:reflectionId/edit
 *     → PATCH that row, inside today's edit window.
 *
 * UH-specific wrinkle: the seeded template's `bunk_concerns_bunks`
 * field uses `option_source: "supervised_bunks"`. The list of legal
 * bunks is what the *dashboard* endpoint already returns (and the
 * write API validates server-side), so we splice that list into the
 * schema before passing it to ReflectionField.
 *
 * The "day off" shortcut is rendered identically to the counselor
 * form for muscle-memory consistency.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import ReflectionField from '../../components/templates/ReflectionField';
import {
  buildDefaultAnswers,
  validateReflectionAnswers,
} from '../../utils/reflection/reflectionFormValidation';
import {
  fetchReflection,
  fetchTemplateById,
  newClientSubmissionId,
} from '../../api/counselor';
import {
  createUnitHeadSelfReflection,
  fetchUnitHeadDashboard,
  patchUnitHeadSelfReflection,
} from '../../api/unitHead';

const DAY_OFF_FIELD_KEY = 'day_off';
const BUNK_CONCERNS_FIELD_KEY = 'bunk_concerns_bunks';

function flattenError(err, fallback) {
  const body = err?.response?.data;
  if (!body) return err?.message || fallback;
  if (typeof body === 'string') return body;
  if (typeof body.detail === 'string') return body.detail;
  if (typeof body === 'object') {
    try {
      return JSON.stringify(body);
    } catch {
      return fallback;
    }
  }
  return fallback;
}

/** Replace `option_source: "supervised_bunks"` with concrete options. */
function injectBunkOptions(schema, bunks) {
  if (!schema?.fields) return schema;
  return {
    ...schema,
    fields: schema.fields.map((f) => {
      if (
        f?.type === 'multiple_choice'
        && f?.option_source === 'supervised_bunks'
      ) {
        return {
          ...f,
          options: bunks.map((b) => ({
            key: String(b.id),
            labels: {
              en: b.unit_name ? `${b.name} — ${b.unit_name}` : b.name,
            },
          })),
        };
      }
      return f;
    }),
  };
}

function withoutDayOffField(schema) {
  if (!schema?.fields) return schema;
  return {
    ...schema,
    fields: schema.fields.filter((f) => f?.key !== DAY_OFF_FIELD_KEY),
  };
}

export default function UnitHeadSelfReflectionPage() {
  const navigate = useNavigate();
  const { reflectionId: editIdParam } = useParams();
  const isEdit = !!editIdParam;
  const editReflectionId = isEdit ? Number(editIdParam) : null;

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [schema, setSchema] = useState(null);
  const [templateMeta, setTemplateMeta] = useState(null);
  const [supervisedBunks, setSupervisedBunks] = useState([]);

  const [dayOff, setDayOff] = useState(false);
  const [answers, setAnswers] = useState({});
  const [language, setLanguage] = useState('en');

  const [fieldErrors, setFieldErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const clientSubmissionIdRef = useRef(null);
  if (!isEdit && clientSubmissionIdRef.current === null) {
    clientSubmissionIdRef.current = newClientSubmissionId();
  }

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const dashboard = await fetchUnitHeadDashboard({ noCache: true });
      const bunkList = (dashboard?.bunks || []).map((b) => ({
        id: b.id,
        name: b.name,
        unit_name: b.unit_name,
      }));
      setSupervisedBunks(bunkList);

      const selfMeta = dashboard?.self_reflection;
      const templateId = selfMeta?.template_id;
      if (!templateId) {
        setLoadError('No Unit Head self-reflection template is configured.');
        return;
      }
      const template = await fetchTemplateById(templateId);
      setTemplateMeta({
        id: template.id,
        name: template.name,
        slug: template.slug,
        version: template.version,
        languages: template.languages || ['en'],
      });

      if (isEdit) {
        const reflection = await fetchReflection(editReflectionId);
        setSchema(template.schema);
        const existingAnswers = reflection.answers || {};
        const isDayOff = !!existingAnswers[DAY_OFF_FIELD_KEY];
        setDayOff(isDayOff);
        const defaults = buildDefaultAnswers(template.schema);
        setAnswers(isDayOff ? defaults : { ...defaults, ...existingAnswers });
        setLanguage(reflection.language || 'en');
      } else if (selfMeta?.reflection_id) {
        // Already submitted today — bounce to edit URL.
        navigate(
          `/unit-head/self-reflection/${selfMeta.reflection_id}/edit`,
          { replace: true },
        );
        return;
      } else {
        setSchema(template.schema);
        setAnswers(buildDefaultAnswers(template.schema));
      }
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) {
        setLoadError(
          err?.response?.data?.detail
          || 'You do not have permission to open this self-reflection.',
        );
      } else if (status === 404) {
        setLoadError('Reflection not found.');
      } else {
        setLoadError(flattenError(err, 'Could not load the form.'));
      }
    } finally {
      setLoading(false);
    }
  }, [isEdit, editReflectionId, navigate]);

  useEffect(() => {
    load();
  }, [load]);

  const enrichedSchema = useMemo(
    () => (schema ? injectBunkOptions(schema, supervisedBunks) : null),
    [schema, supervisedBunks],
  );

  const visibleSchema = useMemo(
    () => (enrichedSchema ? withoutDayOffField(enrichedSchema) : null),
    [enrichedSchema],
  );

  const updateAnswer = (key, value) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const langChoices = useMemo(
    () => (templateMeta?.languages?.length ? templateMeta.languages : ['en']),
    [templateMeta],
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');
    if (!schema || !templateMeta?.id) {
      setSubmitError('Template not loaded.');
      return;
    }

    if (!dayOff) {
      const { ok, errors } = validateReflectionAnswers(visibleSchema, answers);
      setFieldErrors(errors);
      if (!ok) return;
    }

    setSubmitting(true);
    try {
      const payloadAnswers = (() => {
        if (dayOff) return undefined;
        // Coerce bunk_concerns_bunks values to integers since the backend
        // validates against integer bunk IDs.
        const next = { ...answers };
        const raw = next[BUNK_CONCERNS_FIELD_KEY];
        if (Array.isArray(raw)) {
          next[BUNK_CONCERNS_FIELD_KEY] = raw
            .map((v) => Number(v))
            .filter((n) => Number.isFinite(n));
        }
        return next;
      })();
      if (isEdit) {
        await patchUnitHeadSelfReflection(editReflectionId, {
          dayOff,
          answers: payloadAnswers,
          language,
        });
      } else {
        await createUnitHeadSelfReflection({
          dayOff,
          answers: payloadAnswers,
          language,
          clientSubmissionId: clientSubmissionIdRef.current,
        });
      }
      navigate('/unit-head', { replace: true });
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) {
        setSubmitError(flattenError(err, 'You can no longer edit this reflection.'));
      } else if (status === 400) {
        const body = err?.response?.data;
        if (body && typeof body === 'object' && !Array.isArray(body)) {
          const next = {};
          for (const k of Object.keys(body)) {
            if (k === 'detail') continue;
            const v = body[k];
            next[k] = Array.isArray(v) ? v[0] : typeof v === 'string' ? v : JSON.stringify(v);
          }
          setFieldErrors(next);
          setSubmitError(
            typeof body.detail === 'string'
              ? body.detail
              : 'Please fix the errors and try again.',
          );
        } else {
          setSubmitError(flattenError(err, 'Submit failed.'));
        }
      } else {
        setSubmitError(flattenError(err, 'Submit failed.'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const dayOffLabel = useMemo(() => {
    if (!schema?.fields) return 'Day off today?';
    const field = schema.fields.find((f) => f?.key === DAY_OFF_FIELD_KEY);
    if (!field?.prompts) return 'Day off today?';
    return field.prompts[language] || field.prompts.en || 'Day off today?';
  }, [schema, language]);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 pb-24 w-full max-w-[96rem] mx-auto">
        <header className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <button
              type="button"
              onClick={() => navigate('/unit-head')}
              className="text-xs text-blue-600 dark:text-blue-400 mb-1 flex items-center gap-1"
            >
              ← Back to dashboard
            </button>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
              My self-reflection
            </h1>
            {templateMeta && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {templateMeta.name}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <Link
              to="/unit-head/self-reflection/history"
              data-testid="uh-self-reflection-history-link"
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
            >
              History
            </Link>
            {langChoices.length > 1 && (
              <div
                className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden"
                data-testid="uh-self-reflection-language"
              >
                {langChoices.map((code) => (
                  <button
                    key={code}
                    type="button"
                    aria-pressed={language === code}
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
            )}
          </div>
        </header>

        {loading ? (
          <p
            className="text-gray-600 dark:text-gray-400"
            data-testid="uh-self-reflection-loading"
          >
            Loading form…
          </p>
        ) : loadError ? (
          <div
            className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-800 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
            role="alert"
            data-testid="uh-self-reflection-load-error"
          >
            {loadError}
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="space-y-2"
            data-testid="uh-self-reflection-form"
          >
            <p className="rounded-lg bg-blue-50 dark:bg-blue-950/30 text-blue-900 dark:text-blue-100 text-xs px-3 py-2 mb-3">
              Visible to your Leadership Team and the bunks you flag in
              `bunk concerns`. Not visible to counselors or campers.
            </p>

            <fieldset
              className="mb-4 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-3"
              data-testid="uh-self-reflection-day-off-fieldset"
            >
              <legend className="text-xs font-medium text-gray-600 dark:text-gray-400 px-1">
                Quick action
              </legend>
              <label className="flex items-center gap-3 cursor-pointer mt-1">
                <input
                  type="checkbox"
                  data-testid="uh-self-reflection-day-off-toggle"
                  checked={dayOff}
                  onChange={(e) => {
                    setDayOff(e.target.checked);
                    if (e.target.checked) setFieldErrors({});
                  }}
                  className="h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:border-gray-600"
                />
                <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
                  {dayOffLabel}
                </span>
              </label>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Counts as complete for the day. You can switch back any time today.
              </p>
            </fieldset>

            {!dayOff && (visibleSchema?.fields || []).map((field) => (
              <ReflectionField
                key={field.key}
                field={field}
                language={language}
                answer={answers[field.key]}
                onChange={(val) => updateAnswer(field.key, val)}
                error={fieldErrors[field.key]}
              />
            ))}

            {submitError && (
              <p
                className="text-red-600 text-sm"
                role="alert"
                data-testid="uh-self-reflection-submit-error"
              >
                {submitError}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              data-testid="uh-self-reflection-submit"
              className="w-full sm:w-auto mt-4 min-h-[48px] px-6 rounded-lg bg-blue-600 text-white font-medium text-sm disabled:opacity-50"
            >
              {submitting
                ? 'Submitting…'
                : dayOff
                  ? 'Mark day off'
                  : isEdit
                    ? 'Save changes'
                    : 'Submit reflection'}
            </button>
          </form>
        )}
    </div>
  );
}
