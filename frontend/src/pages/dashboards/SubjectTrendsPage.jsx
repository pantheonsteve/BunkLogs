import { useCallback, useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import api from '../../api';
import SubjectTrendGrid from '../../dashboards/trends/SubjectTrendGrid';

function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function isoDaysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** Returns true if the template has at least one field tagged as primary_rating or category_ratings. */
function hasTrendSupport(template) {
  const fields = template?.schema?.fields;
  if (!Array.isArray(fields)) return false;
  return fields.some(
    (f) =>
      f?.dashboard_role === 'primary_rating' ||
      f?.dashboard_role === 'category_ratings',
  );
}

export default function SubjectTrendsPage() {
  const { groupId } = useParams();
  const [search, setSearch] = useSearchParams();
  const [templates, setTemplates] = useState([]);
  const [templateId, setTemplateId] = useState(() => search.get('template') || '');
  const [category, setCategory] = useState(() => search.get('category') || '');
  const [dateStart, setDateStart] = useState(() => isoDaysAgo(13));
  const [dateEnd, setDateEnd] = useState(todayIso);
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load templates with subject mode and assignment group types, then filter to
  // those that actually expose a rating field — others can't drive the trend grid.
  useEffect(() => {
    let cancelled = false;
    api
      .get('/api/v1/templates/', { params: { is_active: 'true' } })
      .then(({ data }) => {
        if (cancelled) return;
        const list = Array.isArray(data) ? data : (data.results ?? []);
        const filtered = list.filter(
          (t) =>
            ['single_subject', 'multi_subject'].includes(t.subject_mode) &&
            (t.assignment_group_types || []).length > 0 &&
            hasTrendSupport(t),
        );
        setTemplates(filtered);
        if (!templateId && filtered.length > 0) {
          setTemplateId(String(filtered[0].id));
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const load = useCallback(async () => {
    if (!groupId || !templateId) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get('/api/v1/dashboards/subject-trends/', {
        params: {
          assignment_group: groupId,
          template: templateId,
          date_start: dateStart,
          date_end: dateEnd,
          category: category || undefined,
        },
      });
      setPayload(data);
    } catch (e) {
      const status = e.response?.status;
      if (status === 403) setError('access');
      else setError(e.response?.data?.detail || e.message || 'Failed to load trends');
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [groupId, templateId, dateStart, dateEnd, category]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCategoryChange = (newCategory) => {
    setCategory(newCategory);
    const next = new URLSearchParams(search);
    if (newCategory) next.set('category', newCategory);
    else next.delete('category');
    setSearch(next, { replace: true });
  };

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Subject Trend Grid
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Per-subject color patterns across days. Hover any cell for the rating, who logged
            it, and a link to the full reflection.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {templates.length > 0 && (
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
              <span>Template</span>
              <select
                value={templateId}
                onChange={(e) => setTemplateId(e.target.value)}
                className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
              >
                {templates.map((t) => (
                  <option key={t.id} value={String(t.id)}>{t.name}</option>
                ))}
              </select>
            </label>
          )}
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
            <span>From</span>
            <input
              type="date"
              value={dateStart}
              onChange={(e) => setDateStart(e.target.value)}
              className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
            <span>To</span>
            <input
              type="date"
              value={dateEnd}
              onChange={(e) => setDateEnd(e.target.value)}
              className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
            />
          </label>
          <button
            type="button"
            onClick={load}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500"
          >
            Refresh
          </button>
        </div>
      </div>

      {templates.length === 0 && !loading && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/20 p-4 text-amber-900 dark:text-amber-100 text-sm">
          No templates with trend tracking support are configured for this organization.
          Templates must have a <strong>primary_rating</strong> or <strong>category_ratings</strong> field to appear here.
        </div>
      )}

      {loading && <p className="text-gray-500 dark:text-gray-400 text-sm">Loading…</p>}

      {!loading && error === 'access' && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/20 p-4 text-amber-900 dark:text-amber-100 text-sm">
          You do not have permission to view trends for this group.
        </div>
      )}

      {!loading && error && error !== 'access' && (
        <p className="text-rose-600 dark:text-rose-400 text-sm">{error}</p>
      )}

      {!loading && payload && (
        <SubjectTrendGrid
          payload={payload}
          category={category}
          onCategoryChange={handleCategoryChange}
        />
      )}
    </div>
  );
}
