import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import api from '../api';
import Header from '../partials/Header';
import Sidebar from '../partials/Sidebar';
import PrivacyChip from '../components/reflection/PrivacyChip';

function promptText(field) {
  if (!field?.prompts || typeof field.prompts !== 'object') return '';
  const v = Object.values(field.prompts)[0];
  return typeof v === 'string' ? v : '';
}

function categoryLabel(cat) {
  if (!cat?.labels || typeof cat.labels !== 'object') return cat?.key || '';
  const v = Object.values(cat.labels)[0];
  return typeof v === 'string' ? v : cat.key || '';
}

function formatAnswer(field, value) {
  if (value === undefined || value === null || value === '') return '—';
  if (field.type === 'rating_group' && value && typeof value === 'object') {
    return Object.entries(value)
      .map(([k, v]) => {
        const cat = (field.categories || []).find((c) => c.key === k);
        const label = cat ? categoryLabel(cat) : k;
        return `${label}: ${v}`;
      })
      .join('; ');
  }
  if (Array.isArray(value)) return value.join(', ') || '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function formatDateTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function ErrorPanel({ title, body, backHref, backLabel }) {
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-900 p-5">
      <h2 className="text-base font-semibold text-amber-900 dark:text-amber-100 mb-1">
        {title}
      </h2>
      <p className="text-sm text-amber-900 dark:text-amber-100">{body}</p>
      <div className="mt-4">
        <Link
          to={backHref}
          className="text-sm font-medium text-amber-900 dark:text-amber-100 underline"
        >
          {backLabel}
        </Link>
      </div>
    </div>
  );
}

export default function ReflectionDetailPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const returnTo = searchParams.get('returnTo') || '/my-reflections';

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [reflection, setReflection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorState, setErrorState] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErrorState(null);
    api
      .get(`/api/v1/reflections/${id}/`)
      .then((r) => {
        if (cancelled) return;
        setReflection(r.data);
      })
      .catch((err) => {
        if (cancelled) return;
        const httpStatus = err.response?.status;
        if (httpStatus === 404) {
          setErrorState({
            title: 'Reflection not found',
            body:
              "We couldn't find that reflection. It may have been deleted, or you may have followed a stale link.",
          });
        } else if (httpStatus === 403) {
          setErrorState({
            title: 'You don\u2019t have access',
            body:
              'You do not have permission to view this reflection. If you think this is wrong, ask an admin.',
          });
        } else {
          setErrorState({
            title: 'Something went wrong',
            body:
              err.response?.data?.detail
              || 'Could not load this reflection. Please try again.',
          });
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const schema = reflection?.localized_schema;
  const fields = Array.isArray(schema?.fields) ? schema.fields : [];
  const templateName = reflection?.template_meta?.name;
  const periodStart = reflection?.period_start;
  const periodEnd = reflection?.period_end;
  const language = reflection?.language;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-2xl mx-auto">
          <div className="mb-4">
            <Link
              to={returnTo}
              className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 underline"
            >
              ← Back
            </Link>
          </div>

          {loading && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Loading reflection…
            </p>
          )}

          {!loading && errorState && (
            <ErrorPanel
              title={errorState.title}
              body={errorState.body}
              backHref={returnTo}
              backLabel="Back to where I was"
            />
          )}

          {!loading && !errorState && reflection && (
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
              <div className="flex flex-wrap items-center gap-3 mb-2">
                <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Reflection
                </h1>
                <PrivacyChip teamVisibility={reflection.team_visibility} />
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {templateName}
              </p>
              <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                #{reflection.id}
                {periodStart && (
                  <>
                    {' · '}
                    {formatDate(periodStart)}
                    {periodStart !== periodEnd && (
                      <>
                        {' → '}
                        {formatDate(periodEnd)}
                      </>
                    )}
                  </>
                )}
                {language && <> · {language}</>}
              </p>
              {reflection.submitted_at && (
                <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                  Submitted {formatDateTime(reflection.submitted_at)}
                </p>
              )}

              {fields.length === 0 ? (
                <p className="mt-6 text-sm text-gray-500 dark:text-gray-400 italic">
                  This reflection's template has no fields to display.
                </p>
              ) : (
                <ul className="mt-6 space-y-4">
                  {fields.map((field) => (
                    <li
                      key={field.key}
                      className="border-b border-gray-100 dark:border-gray-700 pb-3 last:border-0"
                    >
                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                        {field.type === 'rating_group'
                          ? 'Ratings'
                          : promptText(field) || field.key}
                      </p>
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                        {formatAnswer(field, reflection.answers?.[field.key])}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
