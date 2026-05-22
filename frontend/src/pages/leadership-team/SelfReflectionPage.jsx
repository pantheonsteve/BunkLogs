/**
 * LT Self-Reflection form — Step 7_12, Story 50.
 *
 * Biweekly cadence by default. Supports a "Private" toggle that sets
 * ``is_private=true`` server-side, which the backend translates to
 * ``team_visibility=supervisors_only`` + ``is_sensitive=true`` so only
 * the author and admins can see the row.
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
  fetchDashboard,
  submitSelfReflection,
  updateSelfReflection,
} from '../../api/leadershipTeam';
import { useAuth } from '../../auth/AuthContext';

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

export default function LeadershipTeamSelfReflectionPage() {
  const { reflectionId: editIdParam } = useParams();
  const navigate = useNavigate();
  const { orgSlug } = useAuth();
  const isEdit = Boolean(editIdParam);

  const [template, setTemplate] = useState(null);
  const [answers, setAnswers] = useState({});
  const [language, setLanguage] = useState('en');
  const [isPrivate, setIsPrivate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const clientSubmissionId = useRef(newClientSubmissionId());

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const dashboard = await fetchDashboard(orgSlug);
      const selfMeta = dashboard?.self_reflection;
      if (!selfMeta?.template_id) {
        setError('No Leadership Team reflection template is configured.');
        return;
      }
      const tpl = await fetchTemplateById(selfMeta.template_id);
      setTemplate(tpl);

      if (isEdit) {
        const reflection = await fetchReflection(editIdParam);
        const ans = reflection.answers || {};
        setAnswers(ans);
        setLanguage(reflection.language || 'en');
        setIsPrivate(reflection.team_visibility === 'supervisors_only' || Boolean(reflection.is_sensitive));
      } else if (selfMeta.reflection_id) {
        navigate(`/leadership-team/self-reflection/${selfMeta.reflection_id}/edit`, { replace: true });
        return;
      } else {
        setAnswers(buildDefaultAnswers(tpl.schema));
      }
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) setError('You do not have Leadership Team access.');
      else setError(flattenError(err, 'Could not load the reflection form.'));
    } finally {
      setLoading(false);
    }
  }, [orgSlug, isEdit, editIdParam, navigate]);

  useEffect(() => { load(); }, [load]);

  const isDayOff = useMemo(() => Boolean(answers[DAY_OFF_FIELD_KEY]), [answers]);

  const updateAnswer = (key, value) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => { const next = { ...prev }; delete next[key]; return next; });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!template) return;
    if (!isDayOff) {
      const { ok, errors } = validateReflectionAnswers(template.schema, answers);
      if (!ok) {
        setFieldErrors(errors);
        return;
      }
    }
    setSubmitting(true);
    try {
      const payload = {
        answers: isDayOff ? undefined : answers,
        day_off: isDayOff || undefined,
        language,
        is_private: isPrivate || undefined,
      };
      if (isEdit) {
        await updateSelfReflection(orgSlug, editIdParam, payload);
      } else {
        await submitSelfReflection(orgSlug, {
          ...payload,
          client_submission_id: clientSubmissionId.current,
        });
      }
      navigate('/leadership-team');
    } catch (err) {
      setError(flattenError(err, 'Could not save the reflection.'));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen" data-testid="lt-self-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error && !template) {
    return (
      <div className="p-6" data-testid="lt-self-error">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <Link
          to="/leadership-team"
          className="mt-3 inline-block text-sm text-indigo-600 dark:text-indigo-400 underline"
        >
          Back to LT dashboard
        </Link>
      </div>
    );
  }

  const fields = (template?.schema?.fields ?? []).filter(f => f.key !== DAY_OFF_FIELD_KEY);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <Link
          to="/leadership-team"
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
        >
          ← Back to LT dashboard
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mt-2 mb-6">
          {isEdit ? 'Edit Leadership reflection' : 'New Leadership reflection'}
        </h1>

        <form onSubmit={handleSubmit} noValidate>
          <label className="flex items-center gap-2 mb-4 cursor-pointer">
            <input
              type="checkbox"
              checked={isDayOff}
              onChange={(e) => updateAnswer(DAY_OFF_FIELD_KEY, e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
              data-testid="lt-self-day-off"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">Day off</span>
          </label>

          {!isDayOff && fields.map((field) => (
            <div key={field.key} className="mb-6">
              <ReflectionField
                field={field}
                answer={answers[field.key]}
                onChange={(v) => updateAnswer(field.key, v)}
                error={fieldErrors[field.key]}
                language={language}
              />
            </div>
          ))}

          <label className="flex items-center gap-2 mb-4 cursor-pointer">
            <input
              type="checkbox"
              checked={isPrivate}
              onChange={(e) => setIsPrivate(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
              data-testid="lt-self-private"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Private — only admins and I can see this
            </span>
          </label>

          {error && (
            <p className="text-red-600 dark:text-red-400 text-sm mb-3" data-testid="lt-self-submit-error">
              {error}
            </p>
          )}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium py-2 px-4"
              data-testid="lt-self-submit"
            >
              {submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Submit reflection'}
            </button>
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium py-2 px-4"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
