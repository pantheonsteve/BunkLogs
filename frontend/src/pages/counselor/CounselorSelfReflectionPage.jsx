/**
 * Counselor self-reflection form — Step 7_6e (Stories 5 + 6).
 *
 * URL shapes:
 *
 *   /counselor/self-reflection
 *     → If no submission exists for today, render a POST form.
 *       If today's submission exists, redirect to the edit URL.
 *
 *   /counselor/self-reflection/:reflectionId/edit
 *     → PATCH /api/v1/counselor/self-reflection/:reflectionId/
 *
 * "Day off" UX (Story 5 criterion 3):
 *   The seeded template includes a ``day_off`` yes_no field. We render it
 *   as a prominent toggle at the top of the form, separate from the
 *   schema's normal field rendering. When ON, the rest of the form is
 *   hidden and the submit button reads "Mark day off"; payload to the
 *   server is the shortcut ``{ day_off: true }``. When OFF, normal
 *   schema fields render.
 *
 * Template resolution:
 *   We hit `GET /counselor/dashboard/` (cached 30s) to discover the
 *   active self-reflection template ID + whether a row already exists
 *   today, then fetch the template schema by ID. This avoids the
 *   ambiguity in `/reflections/template-for-me/` which would pick the
 *   wrong template if the org has both a single-subject (camper) and a
 *   self template both keyed `role=counselor`.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import AudienceDisclosure from '../../components/AudienceDisclosure';
import ReflectionField from '../../components/templates/ReflectionField';
import {
  buildDefaultAnswers,
  prepareReflectionAnswersForSubmit,
  validateReflectionAnswers,
} from '../../utils/reflection/reflectionFormValidation';
import {
  COUNSELOR_SELF_REFLECTION_AUDIENCE,
  createSelfReflection,
  fetchCounselorDashboard,
  fetchReflection,
  fetchTemplateById,
  newClientSubmissionId,
  patchSelfReflection,
} from '../../api/counselor';

const DAY_OFF_FIELD_KEY = 'day_off';

function flattenError(err, fallback) {
  const body = err?.response?.data;
  if (!body) return err?.message || fallback;
  if (typeof body === 'string') return body;
  if (typeof body.detail === 'string') return body.detail;
  if (typeof body === 'object') {
    try {
      return JSON.stringify(body);
    } catch (_) {
      return fallback;
    }
  }
  return fallback;
}

function withoutDayOffField(schema) {
  if (!schema?.fields) return schema;
  return {
    ...schema,
    fields: schema.fields.filter((f) => f?.key !== DAY_OFF_FIELD_KEY),
  };
}

export default function CounselorSelfReflectionPage() {
  const navigate = useNavigate();
  const { reflectionId: editIdParam } = useParams();
  const isEdit = !!editIdParam;
  const editReflectionId = isEdit ? Number(editIdParam) : null;

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [schema, setSchema] = useState(null);
  const [templateMeta, setTemplateMeta] = useState(null);

  const [dayOff, setDayOff] = useState(false);
  const [answers, setAnswers] = useState({});
  const [language, setLanguage] = useState('en');

  const [fieldErrors, setFieldErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Stable UUID across retries for create mode (Step 7_6c idempotency).
  const clientSubmissionIdRef = useRef(null);
  if (!isEdit && clientSubmissionIdRef.current === null) {
    clientSubmissionIdRef.current = newClientSubmissionId();
  }

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      if (isEdit) {
        const reflection = await fetchReflection(editReflectionId);
        const templateId = reflection.template || reflection.template_meta?.id;
        if (!templateId) {
          setLoadError('Reflection has no template attached.');
          return;
        }
        const template = await fetchTemplateById(templateId);
        setSchema(template.schema);
        setTemplateMeta({
          id: template.id,
          name: template.name,
          slug: template.slug,
          version: template.version,
          languages: template.languages || ['en'],
        });

        const existingAnswers = reflection.answers || {};
        const isDayOff = !!existingAnswers[DAY_OFF_FIELD_KEY];
        setDayOff(isDayOff);
        const defaults = buildDefaultAnswers(template.schema);
        // When the row is a day-off shortcut, keep the rest of the answers
        // at their defaults so flipping the toggle reveals a clean form.
        setAnswers(isDayOff ? defaults : { ...defaults, ...existingAnswers });
        setLanguage(reflection.language || 'en');
      } else {
        const dashboard = await fetchCounselorDashboard();
        const selfSection = dashboard?.sections?.self_reflection;
        if (selfSection?.reflection_id) {
          // Already submitted today — bounce to the edit URL so the user
          // can refine, day-off-toggle, or change language. ``replace``
          // keeps the back stack tidy.
          navigate(
            `/counselor/self-reflection/${selfSection.reflection_id}/edit`,
            { replace: true },
          );
          return;
        }
        const tplMeta = selfSection?.template;
        if (!tplMeta?.id) {
          setLoadError('No counselor self-reflection template is configured.');
          return;
        }
        const template = await fetchTemplateById(tplMeta.id);
        setSchema(template.schema);
        setTemplateMeta({
          id: template.id,
          name: template.name,
          slug: template.slug,
          version: template.version,
          languages: template.languages || ['en'],
        });
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

  const visibleSchema = useMemo(
    () => (schema ? withoutDayOffField(schema) : null),
    [schema],
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
      const payloadAnswers = dayOff
        ? undefined
        : prepareReflectionAnswersForSubmit(schema, answers, {
            omitKeys: [DAY_OFF_FIELD_KEY],
          });
      if (isEdit) {
        await patchSelfReflection(editReflectionId, {
          dayOff,
          answers: payloadAnswers,
          language,
        });
      } else {
        await createSelfReflection({
          dayOff,
          answers: payloadAnswers,
          language,
          clientSubmissionId: clientSubmissionIdRef.current,
        });
      }
      navigate('/counselor', { replace: true });
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
              onClick={() => navigate('/counselor')}
              className="text-xs text-blue-600 dark:text-blue-400 mb-1 flex items-center gap-1"
            >
              ← Back to dashboard
            </button>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
              My self-reflection
            </h1>
            {templateMeta ? (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {templateMeta.name}
              </p>
            ) : null}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <Link
              to="/counselor/self-reflection/history"
              data-testid="self-reflection-history-link"
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
            >
              History
            </Link>
            {langChoices.length > 1 ? (
              <div
                className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden"
                data-testid="self-reflection-language"
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
            ) : null}
          </div>
        </header>

        {loading ? (
          <p
            className="text-gray-600 dark:text-gray-400"
            data-testid="self-reflection-loading"
          >
            Loading form…
          </p>
        ) : loadError ? (
          <div
            className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-800 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
            role="alert"
            data-testid="self-reflection-load-error"
          >
            {loadError}
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="space-y-2"
            data-testid="self-reflection-form"
          >
            <AudienceDisclosure audience={COUNSELOR_SELF_REFLECTION_AUDIENCE} />

            <fieldset
              className="mb-4 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-3"
              data-testid="self-reflection-day-off-fieldset"
            >
              <legend className="text-xs font-medium text-gray-600 dark:text-gray-400 px-1">
                Quick action
              </legend>
              <label className="flex items-center gap-3 cursor-pointer mt-1">
                <input
                  type="checkbox"
                  data-testid="self-reflection-day-off-toggle"
                  checked={dayOff}
                  onChange={(e) => {
                    setDayOff(e.target.checked);
                    if (e.target.checked) {
                      setFieldErrors({});
                    }
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

            {submitError ? (
              <p
                className="text-red-600 text-sm"
                role="alert"
                data-testid="self-reflection-submit-error"
              >
                {submitError}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={submitting}
              data-testid="self-reflection-submit"
              className="w-full sm:w-auto mt-4 min-h-[48px] px-6 rounded-lg bg-blue-600 text-white font-medium text-sm disabled:opacity-50"
            >
              {submitting
                ? 'Submitting…'
                : dayOff
                  ? isEdit
                    ? 'Mark day off'
                    : 'Mark day off'
                  : isEdit
                    ? 'Save changes'
                    : 'Submit reflection'}
            </button>
          </form>
        )}
    </div>
  );
}
