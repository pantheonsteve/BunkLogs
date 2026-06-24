/**
 * Specialist self-reflection form — Step 7_9, Story 29.
 *
 * Mirrors the Camper Care self-reflection form with two differences:
 *   - No `bunk_concerns_bunks` field (Specialists have no caseload).
 *   - Template may include an optional `camper_observation` field linking
 *     to recent camper notes (criterion 8); rendered generically by ReflectionField.
 *
 * Edit window: until rollover boundary (today). Locked after.
 * Visibility: Specialist, Leadership Team, Admin — NOT Unit Head (Decision S7).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import ReflectionField from '../../components/templates/ReflectionField';
import ReflectionFieldList from '../../components/templates/ReflectionFieldList';
import {
  buildDefaultAnswers,
  validateReflectionAnswers,
} from '../../utils/reflection/reflectionFormValidation';
import { fetchReflection, fetchTemplateById, newClientSubmissionId } from '../../api/counselor';
import {
  createSpecialistSelfReflection,
  patchSpecialistSelfReflection,
} from '../../api/specialist';

const DAY_OFF_FIELD_KEY = 'day_off';

function flattenError(err, fallback) {
  const body = err?.response?.data;
  if (!body) return err?.message || fallback;
  if (typeof body === 'string') return body;
  if (typeof body.detail === 'string') return body.detail;
  if (typeof body === 'object') {
    try { return JSON.stringify(body); } catch { return fallback; }
  }
  return fallback;
}

export default function SpecialistSelfReflectionPage() {
  const { reflectionId } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(reflectionId);

  const [template, setTemplate] = useState(null);
  const [answers, setAnswers] = useState({});
  const [existingReflection, setExistingReflection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const clientIdRef = useRef(newClientSubmissionId());

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (isEdit && reflectionId) {
        const reflection = await fetchReflection(reflectionId);
        setExistingReflection(reflection);
        if (reflection.template?.id) {
          const tpl = await fetchTemplateById(reflection.template.id);
          setTemplate(tpl);
          setAnswers(reflection.answers || buildDefaultAnswers(tpl.schema));
        }
      } else {
        // New: load template from dashboard context (template_id from self_reflection.template_id)
        // For now we load a known slug; the backend returns it in the dashboard payload.
        // The form fetches the full template once we have the ID.
        const dashRes = await import('../../api/specialist').then(m =>
          m.fetchSpecialistDashboard(),
        );
        const templateId = dashRes?.self_reflection?.template_id;
        if (templateId) {
          const tpl = await fetchTemplateById(templateId);
          setTemplate(tpl);
          setAnswers(buildDefaultAnswers(tpl.schema));
        }
      }
    } catch (err) {
      setSubmitError(flattenError(err, 'Could not load reflection form.'));
    } finally {
      setLoading(false);
    }
  }, [isEdit, reflectionId]);

  useEffect(() => { load(); }, [load]);

  const isDayOff = useMemo(
    () => Boolean(answers[DAY_OFF_FIELD_KEY]),
    [answers],
  );

  const nonDayOffFields = useMemo(() => {
    if (!template?.schema?.fields) return [];
    return template.schema.fields.filter((f) => f.key !== DAY_OFF_FIELD_KEY);
  }, [template]);

  const dayOffField = useMemo(
    () => template?.schema?.fields?.find((f) => f.key === DAY_OFF_FIELD_KEY),
    [template],
  );

  const handleAnswer = (key, value) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => { const e = { ...prev }; delete e[key]; return e; });
  };

  const validate = () => {
    if (!template || isDayOff) return true;
    const errs = validateReflectionAnswers(template.schema, answers);
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');
    if (!validate()) return;
    setSubmitting(true);
    try {
      if (isEdit && reflectionId) {
        await patchSpecialistSelfReflection(reflectionId, {
          answers: isDayOff ? undefined : answers,
          dayOff: isDayOff,
          language: existingReflection?.language || 'en',
        });
      } else {
        await createSpecialistSelfReflection({
          answers: isDayOff ? undefined : answers,
          dayOff: isDayOff,
          language: 'en',
          clientSubmissionId: clientIdRef.current,
        });
      }
      setSubmitted(true);
      setTimeout(() => navigate('/specialist'), 1500);
    } catch (err) {
      setSubmitError(flattenError(err, 'Could not save reflection.'));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="sp-sr-loading">
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (!template) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-3">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">My reflection</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">No reflection template configured.</p>
        <Link to="/specialist" className="text-sm text-blue-600 dark:text-blue-400 underline">
          Back to dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 pb-32 w-full max-w-[96rem] mx-auto" data-testid="sp-sr-form">
      <header className="mb-4">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="text-sm text-gray-500 dark:text-gray-400 mb-2 hover:underline"
        >
          ← Back
        </button>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">My reflection</h1>
      </header>

      {submitted && (
        <div
          role="status"
          className="rounded-md border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/30 px-3 py-2 text-sm text-green-900 dark:text-green-100 mb-4"
        >
          Reflection saved! Returning to dashboard…
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {dayOffField && (
          <ReflectionField
            field={dayOffField}
            answer={answers[dayOffField.key]}
            onChange={(v) => handleAnswer(dayOffField.key, v)}
            error={fieldErrors[dayOffField.key]}
            readonly={submitting}
          />
        )}

        {!isDayOff && (
          <ReflectionFieldList
            fields={nonDayOffFields}
            answers={answers}
            errors={fieldErrors}
            onChange={handleAnswer}
            readonly={submitting}
          />
        )}

        {submitError && (
          <p role="alert" className="text-sm text-red-700 dark:text-red-300">{submitError}</p>
        )}

        <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center justify-end gap-2 max-w-[96rem] mx-auto">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="inline-flex items-center px-3 min-h-[44px] rounded-lg border border-gray-300 dark:border-gray-700 text-sm text-gray-800 dark:text-gray-100"
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || submitted}
            data-testid="sp-sr-submit"
            className="inline-flex items-center px-4 min-h-[44px] rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
          >
            {submitting ? 'Saving…' : 'Save reflection'}
          </button>
        </div>
      </form>
    </div>
  );
}
