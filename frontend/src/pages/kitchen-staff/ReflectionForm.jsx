/**
 * Kitchen Staff reflection form — Step 7_11, Stories 39-41.
 *
 * Renders in the user's preferred language (Story 39).
 * Audience disclosure copy adapts to language (Story 40 criterion 10).
 * On edit: prompts in current preference, field contents in original language
 * (Story 41 criterion 4). Language field unchanged unless user explicitly changes it.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import ReflectionField from '../../components/templates/ReflectionField';
import {
  buildDefaultAnswers,
  validateReflectionAnswers,
} from '../../utils/reflection/reflectionFormValidation';
import { fetchReflection, fetchTemplateById, newClientSubmissionId } from '../../api/counselor';
import { fetchTemplate, submitReflection, updateReflection } from '../../api/kitchenStaff';
import { useAuth } from '../../auth/AuthContext';

const DAY_OFF_FIELD_KEY = 'day_off';

const LANGUAGE_NAMES = { en: 'English', es: 'Spanish', he: 'Hebrew' };

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

export default function KitchenStaffReflectionForm() {
  const { reflectionId } = useParams();
  const navigate = useNavigate();
  const { t, i18n } = useTranslation('kitchen_staff');
  const { orgSlug, user } = useAuth();
  const isEdit = Boolean(reflectionId);

  const [template, setTemplate] = useState(null);
  const [answers, setAnswers] = useState({});
  const [existingReflection, setExistingReflection] = useState(null);
  const [reflectionLanguage, setReflectionLanguage] = useState(i18n.language || 'en');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [showLangConfirm, setShowLangConfirm] = useState(false);
  const [pendingLang, setPendingLang] = useState(null);
  const clientSubmissionId = useRef(newClientSubmissionId());

  // Load template (localized to current UI language) and, on edit, the existing reflection
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const uiLang = i18n.language || 'en';
        let tpl;
        if (isEdit) {
          // For edits load the existing reflection to populate answers
          const reflection = await fetchReflection(reflectionId, orgSlug);
          if (!cancelled) setExistingReflection(reflection);
          setReflectionLanguage(reflection.language || uiLang);
          tpl = await fetchTemplateById(reflection.template, orgSlug);
        } else {
          tpl = await fetchTemplate(orgSlug, uiLang);
        }
        if (!cancelled) {
          setTemplate(tpl);
          if (isEdit && existingReflection) {
            setAnswers(existingReflection.answers || {});
          } else if (tpl?.schema?.fields) {
            setAnswers(buildDefaultAnswers(tpl.schema.fields));
          }
        }
      } catch {
        if (!cancelled) setSubmitError(t('form.saveFailed'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reflectionId, orgSlug, i18n.language]);

  const isDayOff = useMemo(() => Boolean(answers[DAY_OFF_FIELD_KEY]), [answers]);

  const handleFieldChange = useCallback((key, value) => {
    setAnswers(prev => ({ ...prev, [key]: value }));
    setFieldErrors(prev => { const n = { ...prev }; delete n[key]; return n; });
  }, []);

  const handleLangChangeRequest = useCallback((newLang) => {
    if (isEdit && newLang !== reflectionLanguage) {
      setPendingLang(newLang);
      setShowLangConfirm(true);
    } else {
      setReflectionLanguage(newLang);
    }
  }, [isEdit, reflectionLanguage]);

  const handleLangConfirm = useCallback(() => {
    if (pendingLang) setReflectionLanguage(pendingLang);
    setPendingLang(null);
    setShowLangConfirm(false);
  }, [pendingLang]);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    setSubmitError('');
    setFieldErrors({});

    if (!isDayOff && template?.schema?.fields) {
      const errors = validateReflectionAnswers(template.schema.fields, answers);
      if (Object.keys(errors).length > 0) {
        setFieldErrors(errors);
        return;
      }
    }

    setSubmitting(true);
    try {
      if (isEdit) {
        await updateReflection(orgSlug, reflectionId, {
          answers: isDayOff ? undefined : answers,
          day_off: isDayOff || undefined,
          language: reflectionLanguage,
        });
      } else {
        await submitReflection(orgSlug, {
          answers: isDayOff ? undefined : answers,
          day_off: isDayOff,
          language: reflectionLanguage,
          client_submission_id: clientSubmissionId.current,
        });
      }
      navigate('/kitchen-staff');
    } catch (err) {
      setSubmitError(flattenError(err, t('form.saveFailed')));
    } finally {
      setSubmitting(false);
    }
  }, [
    isDayOff, template, answers, isEdit, orgSlug, reflectionId,
    reflectionLanguage, navigate, t,
  ]);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen" data-testid="ks-form-loading">
        <p className="text-gray-500 dark:text-gray-400">{t('dashboard.loading')}</p>
      </div>
    );
  }

  const fields = (template?.schema?.fields ?? []).filter(f => f.key !== DAY_OFF_FIELD_KEY);
  const langName = LANGUAGE_NAMES[reflectionLanguage] ?? reflectionLanguage;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <h1
          className="text-2xl font-bold text-gray-900 dark:text-white mb-6"
          data-testid="ks-form-heading"
        >
          {isEdit ? t('form.editReflection') : t('form.newReflection')}
        </h1>

        {/* Story 40 criterion 10: Audience disclosure */}
        <div
          className="mb-6 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 px-4 py-3 text-sm text-blue-800 dark:text-blue-300"
          data-testid="ks-audience-disclosure"
        >
          {t('form.audienceDisclosure', { language: langName })}
        </div>

        <form onSubmit={handleSubmit} noValidate>
          {/* Day-off toggle */}
          <label className="flex items-center gap-2 mb-6 cursor-pointer" data-testid="ks-day-off-label">
            <input
              type="checkbox"
              checked={isDayOff}
              onChange={e => handleFieldChange(DAY_OFF_FIELD_KEY, e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-indigo-600"
              data-testid="ks-day-off-checkbox"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">{t('form.dayOff')}</span>
          </label>

          {/* Reflection fields */}
          {!isDayOff && fields.map(field => (
            <div key={field.key} className="mb-6">
              {/* Story 39 criterion 4: show "(English only)" on untranslated fields */}
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {field.prompts?.[i18n.language] ?? field.prompts?.en ?? field.key}
                {field.prompts && !field.prompts[i18n.language] && i18n.language !== 'en' && (
                  <span className="ml-2 text-xs text-gray-400">{t('form.languageNote')}</span>
                )}
              </label>
              <ReflectionField
                field={field}
                value={answers[field.key]}
                onChange={val => handleFieldChange(field.key, val)}
                error={fieldErrors[field.key]}
                language={i18n.language}
              />
            </div>
          ))}

          {submitError && (
            <p className="text-red-600 dark:text-red-400 text-sm mb-4" data-testid="ks-submit-error">
              {submitError}
            </p>
          )}

          <div className="flex gap-3 mt-6">
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium py-2 px-4 transition-colors"
              data-testid="ks-submit-button"
            >
              {submitting ? t('form.submitting') : t('form.submit')}
            </button>
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium py-2 px-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              {t('form.cancel')}
            </button>
          </div>
        </form>

        {/* Story 41 criterion 6: language change confirmation dialog */}
        {showLangConfirm && (
          <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" data-testid="ks-lang-confirm">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 max-w-sm w-full mx-4">
              <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
                {t('form.languageChangedTitle')}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                {t('form.languageChangedBody', { lang: LANGUAGE_NAMES[pendingLang] ?? pendingLang })}
              </p>
              <div className="flex gap-3">
                <button
                  onClick={handleLangConfirm}
                  className="flex-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2 px-4"
                >
                  {t('form.languageChangedConfirm')}
                </button>
                <button
                  onClick={() => { setShowLangConfirm(false); setPendingLang(null); }}
                  className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium py-2 px-4"
                >
                  {t('form.languageChangedCancel')}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
