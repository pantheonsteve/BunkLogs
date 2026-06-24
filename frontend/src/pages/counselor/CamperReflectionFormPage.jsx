/**
 * Camper reflection form — Step 7_6d (Stories 3 + 4).
 *
 * Two URL shapes:
 *
 *   /counselor/camper-reflections/new?subject=<id>&bunk=<id>&name=...
 *     → POST /api/v1/counselor/camper-reflections/  (new submission)
 *
 *   /counselor/camper-reflections/:reflectionId/edit
 *     → PATCH /api/v1/counselor/camper-reflections/:reflectionId/
 *
 * Both modes load the template schema (via /api/v1/templates/:id/) so the
 * form fields render from server-side config. Idempotency: a single
 * `client_submission_id` UUID is generated once on mount in create mode
 * and reused across retries so the backend's
 * ``find_existing_by_client_submission_id`` collapses duplicate submits
 * into a 200 (existing row) instead of a 201 (new row).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import AudienceDisclosure from '../../components/AudienceDisclosure';
import ReflectionFieldList from '../../components/templates/ReflectionFieldList';
import {
  buildDefaultAnswers,
  validateReflectionAnswers,
} from '../../utils/reflection/reflectionFormValidation';
import { useCounselorDraft } from '../../hooks/useCounselorDraft';
import { isQueuedSubmissionError } from '../../lib/submissionQueue/queue';
import {
  camperReflectionDraftKey,
} from '../../utils/counselor/counselorDraftStorage';
import {
  CAMPER_REFLECTION_AUDIENCE,
  createCamperReflection,
  fetchCamperReflections,
  fetchReflection,
  fetchTemplateById,
  newClientSubmissionId,
  patchCamperReflection,
} from '../../api/counselor';

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

export default function CamperReflectionFormPage() {
  const navigate = useNavigate();
  const { reflectionId: editIdParam } = useParams();
  const [searchParams] = useSearchParams();

  const isEdit = !!editIdParam;
  const editReflectionId = isEdit ? Number(editIdParam) : null;
  const subjectIdParam = isEdit ? null : Number(searchParams.get('subject'));
  const bunkIdParam = isEdit ? null : Number(searchParams.get('bunk'));
  const subjectNameParam = searchParams.get('name') || '';

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [schema, setSchema] = useState(null);
  const [templateMeta, setTemplateMeta] = useState(null);
  const [supportsPrivacy, setSupportsPrivacy] = useState(false);

  const [answers, setAnswers] = useState({});
  const [language, setLanguage] = useState('en');
  const [teamVisibility, setTeamVisibility] = useState('team');
  const [subjectName, setSubjectName] = useState(subjectNameParam);
  const [resolvedSubjectId, setResolvedSubjectId] = useState(subjectIdParam);
  const [resolvedBunkId, setResolvedBunkId] = useState(bunkIdParam);
  const [rosterDate, setRosterDate] = useState(null);

  const [fieldErrors, setFieldErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Persist a single client_submission_id across retries for new submissions.
  // ``useRef`` keeps the UUID stable even if the component re-renders mid-submit.
  const clientSubmissionIdRef = useRef(null);
  if (!isEdit && clientSubmissionIdRef.current === null) {
    clientSubmissionIdRef.current = newClientSubmissionId();
  }

  const draftKey = !isEdit && resolvedSubjectId && rosterDate
    ? camperReflectionDraftKey(resolvedSubjectId, rosterDate)
    : null;

  const { persistDraft, clearDraft } = useCounselorDraft({
    draftKey,
    enabled: !isEdit && !!draftKey,
    getSnapshot: () => ({
      answers,
      language,
      teamVisibility,
      clientSubmissionId: clientSubmissionIdRef.current,
    }),
    onRestore: (saved) => {
      if (saved.answers) {
        setAnswers((prev) => ({ ...prev, ...saved.answers }));
      }
      if (saved.language) setLanguage(saved.language);
      if (saved.teamVisibility) setTeamVisibility(saved.teamVisibility);
      if (saved.clientSubmissionId) {
        clientSubmissionIdRef.current = saved.clientSubmissionId;
      }
    },
  });

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
        setSupportsPrivacy(!!template.supports_privacy);
        const defaults = buildDefaultAnswers(template.schema);
        setAnswers({ ...defaults, ...(reflection.answers || {}) });
        setLanguage(reflection.language || 'en');
        setTeamVisibility(reflection.team_visibility || 'team');
        setResolvedSubjectId(reflection.subject || null);
        setResolvedBunkId(reflection.assignment_group || null);
      } else {
        // Pull today's roster to discover the active template id + verify
        // the camper is on a bunk the viewer authors. Cheaper than another
        // template-by-program endpoint for this v1 flow.
        const roster = await fetchCamperReflections();
        setRosterDate(roster.date || null);
        const templateRef = roster.template;
        if (!templateRef?.id) {
          setLoadError('No camper reflection template is configured for your program.');
          return;
        }
        const template = await fetchTemplateById(templateRef.id);
        setSchema(template.schema);
        setTemplateMeta({
          id: template.id,
          name: template.name,
          slug: template.slug,
          version: template.version,
          languages: template.languages || ['en'],
        });
        setSupportsPrivacy(!!template.supports_privacy);
        setAnswers(buildDefaultAnswers(template.schema));

        // Best-effort camper-name display from the roster if the link
        // didn't pass `?name=...`; non-fatal if missing.
        if (!subjectNameParam && subjectIdParam) {
          const bunk = roster.bunks?.find((b) => b.id === bunkIdParam);
          const row = bunk?.campers?.find((c) => c.id === subjectIdParam);
          if (row?.name) setSubjectName(row.name);
        }
      }
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) {
        setLoadError('You do not have permission to open this reflection.');
      } else if (status === 404) {
        setLoadError('Reflection not found.');
      } else {
        setLoadError(flattenError(err, 'Could not load the form.'));
      }
    } finally {
      setLoading(false);
    }
  }, [isEdit, editReflectionId, subjectIdParam, bunkIdParam, subjectNameParam]);

  useEffect(() => {
    load();
  }, [load]);

  const updateAnswer = useCallback((key, value) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => {
      if (!(key in prev)) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }, []);

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

    const { ok, errors } = validateReflectionAnswers(schema, answers);
    setFieldErrors(errors);
    if (!ok) return;

    setSubmitting(true);
    try {
      if (isEdit) {
        await patchCamperReflection(editReflectionId, {
          answers,
          language,
          teamVisibility: supportsPrivacy ? teamVisibility : undefined,
        });
      } else {
        if (!resolvedSubjectId || !resolvedBunkId) {
          setSubmitError('Missing camper or bunk reference.');
          setSubmitting(false);
          return;
        }
        await createCamperReflection({
          subjectId: resolvedSubjectId,
          assignmentGroupId: resolvedBunkId,
          answers,
          language,
          teamVisibility: supportsPrivacy ? teamVisibility : 'team',
          clientSubmissionId: clientSubmissionIdRef.current,
          date: rosterDate,
        });
      }
      clearDraft();
      navigate('/counselor/camper-reflections', { replace: true });
    } catch (err) {
      if (isQueuedSubmissionError(err)) {
        clearDraft();
        navigate('/counselor/camper-reflections', { replace: true });
        return;
      }
      if (err?.response?.status === 401) {
        persistDraft();
        setSubmitError('Session expired — your answers are saved. Please sign in again.');
        return;
      }
      const status = err?.response?.status;
      if (status === 403) {
        setSubmitError(flattenError(err, 'You can no longer edit this reflection.'));
      } else if (status === 400) {
        // Validation errors — try to surface field-level messages.
        const body = err?.response?.data;
        if (body && typeof body === 'object' && !Array.isArray(body)) {
          const fieldKeys = Object.keys(body).filter((k) => k !== 'detail');
          const next = {};
          for (const k of fieldKeys) {
            const v = body[k];
            next[k] = Array.isArray(v) ? v[0] : typeof v === 'string' ? v : JSON.stringify(v);
          }
          setFieldErrors(next);
          setSubmitError(typeof body.detail === 'string' ? body.detail : 'Please fix the errors and try again.');
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

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 pb-24 w-full max-w-[96rem] mx-auto">
        <header className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <button
              type="button"
              onClick={() => navigate('/counselor/camper-reflections')}
              className="text-xs text-blue-600 dark:text-blue-400 mb-1 flex items-center gap-1"
            >
              ← Back to roster
            </button>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
              {subjectName ? `About ${subjectName}` : 'Camper reflection'}
            </h1>
            {templateMeta ? (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {templateMeta.name}
              </p>
            ) : null}
          </div>
          {langChoices.length > 1 ? (
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs text-gray-500 uppercase tracking-wide">Language</span>
              <div
                className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden"
                data-testid="camper-reflection-language"
              >
                {langChoices.map((code) => (
                  <button
                    key={code}
                    type="button"
                    onClick={() => setLanguage(code)}
                    aria-pressed={language === code}
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
          ) : null}
        </header>

        {loading ? (
          <p
            className="text-gray-600 dark:text-gray-400"
            data-testid="camper-reflection-loading"
          >
            Loading form…
          </p>
        ) : loadError ? (
          <div
            className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-800 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
            role="alert"
            data-testid="camper-reflection-load-error"
          >
            {loadError}
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-2" data-testid="camper-reflection-form">
            <AudienceDisclosure audience={CAMPER_REFLECTION_AUDIENCE} />

            {supportsPrivacy ? (
              <fieldset
                className="mb-4 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-3"
                data-testid="camper-reflection-visibility"
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
                      data-testid={`camper-reflection-visibility-${opt.value}`}
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
              </fieldset>
            ) : null}

            <ReflectionFieldList
              fields={schema?.fields}
              answers={answers}
              errors={fieldErrors}
              language={language}
              onChange={updateAnswer}
            />

            {submitError ? (
              <p
                className="text-red-600 text-sm"
                role="alert"
                data-testid="camper-reflection-submit-error"
              >
                {submitError}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={submitting}
              data-testid="camper-reflection-submit"
              className="w-full sm:w-auto mt-4 min-h-[48px] px-6 rounded-lg bg-blue-600 text-white font-medium text-sm disabled:opacity-50"
            >
              {submitting ? 'Submitting…' : isEdit ? 'Save changes' : 'Submit reflection'}
            </button>
          </form>
        )}
    </div>
  );
}
