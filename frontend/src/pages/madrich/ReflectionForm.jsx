/**
 * Madrich (TBE) weekly reflection form — Step 7_14, Stories 62 & 64.
 *
 * Story 62 contract:
 *   * Exactly 3 wins, exactly 2 improvements, 1 question/concern, 5 ratings (1-4).
 *   * No day-off shortcut (criterion 3) — every week's payload carries all sections.
 *   * Inline submit error from backend; client-side validation mirrors
 *     backend schema enforcement via `validateReflectionAnswers`.
 *
 * Story 64 visibility disclosure: rendered above the form so the
 * Madrich sees who can read the submission before they hit Submit.
 *
 * TBE Tier 1 scope: English only — no language picker / Hebrew copy.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import ReflectionField from '../../components/templates/ReflectionField';
import {
  buildDefaultAnswers,
  validateReflectionAnswers,
} from '../../utils/reflection/reflectionFormValidation';
import { fetchReflection, fetchTemplateById, newClientSubmissionId } from '../../api/counselor';
import { fetchTemplate, submitReflection, updateReflection } from '../../api/madrich';
import { useAuth } from '../../auth/AuthContext';

const LANGUAGE = 'en';
const AUDIENCE_DISCLOSURE =
  'Your Director(s) and any Temple Beth-El staff assigned to oversee Madrichim can read this reflection. Other Madrichim cannot.';

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

export default function MadrichReflectionForm() {
  const { reflectionId } = useParams();
  const navigate = useNavigate();
  const { orgSlug } = useAuth();
  const isEdit = Boolean(reflectionId);

  const [template, setTemplate] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const clientSubmissionId = useRef(newClientSubmissionId());

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        let tpl;
        let prefillAnswers = null;
        if (isEdit) {
          const reflection = await fetchReflection(reflectionId);
          if (!cancelled) prefillAnswers = reflection.answers || {};
          tpl = await fetchTemplateById(reflection.template);
        } else {
          tpl = await fetchTemplate(orgSlug, LANGUAGE);
        }
        if (!cancelled) {
          setTemplate(tpl);
          if (prefillAnswers !== null) {
            setAnswers(prefillAnswers);
          } else if (tpl?.schema) {
            setAnswers(buildDefaultAnswers(tpl.schema));
          }
        }
      } catch (err) {
        if (!cancelled) setSubmitError(flattenError(err, 'Could not load the reflection.'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [reflectionId, orgSlug, isEdit]);

  const handleFieldChange = useCallback((key, value) => {
    setAnswers(prev => ({ ...prev, [key]: value }));
    setFieldErrors(prev => { const n = { ...prev }; delete n[key]; return n; });
  }, []);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    setSubmitError('');
    setFieldErrors({});

    if (template?.schema) {
      const { ok, errors } = validateReflectionAnswers(template.schema, answers);
      if (!ok) {
        setFieldErrors(errors);
        return;
      }
    }

    setSubmitting(true);
    try {
      if (isEdit) {
        await updateReflection(orgSlug, reflectionId, {
          answers,
          language: LANGUAGE,
        });
      } else {
        await submitReflection(orgSlug, {
          answers,
          language: LANGUAGE,
          client_submission_id: clientSubmissionId.current,
        });
      }
      navigate('/madrich');
    } catch (err) {
      setSubmitError(flattenError(err, 'Could not save the reflection.'));
    } finally {
      setSubmitting(false);
    }
  }, [template, answers, isEdit, orgSlug, reflectionId, navigate]);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen" data-testid="md-form-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  const fields = template?.schema?.fields ?? [];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <h1
          className="text-2xl font-bold text-gray-900 dark:text-white mb-6"
          data-testid="md-form-heading"
        >
          {isEdit ? 'Edit weekly reflection' : 'This week\u2019s reflection'}
        </h1>

        <div
          className="mb-6 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 px-4 py-3 text-sm text-blue-800 dark:text-blue-300"
          data-testid="md-audience-disclosure"
        >
          {AUDIENCE_DISCLOSURE}
        </div>

        <form onSubmit={handleSubmit} noValidate>
          {fields.map(field => (
            <div key={field.key} className="mb-6">
              <ReflectionField
                field={field}
                answer={answers[field.key]}
                onChange={val => handleFieldChange(field.key, val)}
                error={fieldErrors[field.key]}
                language={LANGUAGE}
              />
            </div>
          ))}

          {submitError && (
            <p className="text-red-600 dark:text-red-400 text-sm mb-4" data-testid="md-submit-error">
              {submitError}
            </p>
          )}

          <div className="flex gap-3 mt-6">
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium py-2 px-4 transition-colors"
              data-testid="md-submit-button"
            >
              {submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Submit reflection'}
            </button>
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium py-2 px-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
