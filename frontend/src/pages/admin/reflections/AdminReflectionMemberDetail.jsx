/**
 * Admin Reflection member detail — Step 4_4 (TBE).
 *
 * One Madrich's full reflection history (all weekly periods), reusing
 * the org-admin-gated `admin_flow/reflections.py` endpoint so it works
 * without a Supervision relationship. Answers are rendered generically
 * (no template-schema lookup) since this surface is role-parameterized.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchAdminReflectionMember } from '../../../api/adminReflections';

function humanizeKey(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function AnswerValue({ value }) {
  if (Array.isArray(value)) {
    return (
      <ul className="list-disc list-inside text-sm text-gray-800 dark:text-gray-200">
        {value.map((item, i) => <li key={i}>{String(item)}</li>)}
      </ul>
    );
  }
  if (value !== null && typeof value === 'object') {
    return (
      <div className="flex flex-wrap gap-2 text-xs text-gray-700 dark:text-gray-300">
        {Object.entries(value).map(([k, v]) => (
          <span key={k} className="rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5">
            {humanizeKey(k)}: {String(v)}
          </span>
        ))}
      </div>
    );
  }
  return (
    <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
      {value === null || value === undefined || value === '' ? '—' : String(value)}
    </p>
  );
}

export default function AdminReflectionMemberDetail() {
  const { role, membershipId } = useParams();
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchAdminReflectionMember(role, membershipId);
      setPayload(data);
      setError(null);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) setError('Admin access required.');
      else if (status === 404) setError('Member not found.');
      else setError('Failed to load this member.');
    } finally {
      setLoading(false);
    }
  }, [role, membershipId]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="admin-reflection-member-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error || !payload) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="admin-reflection-member-error">
        <p className="text-red-600 dark:text-red-400">{error || 'Failed to load this member.'}</p>
        <Link
          to="/admin/reflections"
          className="mt-3 inline-block text-sm text-indigo-600 dark:text-indigo-400 underline"
        >
          Back to reflections
        </Link>
      </div>
    );
  }

  const { person_name: personName, grade_level: gradeLevel, role_label: roleLabel, history } = payload;

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <div>
        <Link
          to="/admin/reflections"
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
        >
          ← Back to reflections
        </Link>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white mt-2">{personName}</h1>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          {roleLabel}
          {gradeLevel != null && <> · Grade {gradeLevel}</>}
        </p>
      </div>

      <section aria-label="Reflection history" data-testid="admin-reflection-member-history">
        {history.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-sm text-gray-500 dark:text-gray-400">
            No reflections submitted yet.
          </div>
        ) : (
          <ul className="space-y-3">
            {history.map((entry) => (
              <li
                key={entry.reflection_id}
                className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
                data-testid={`admin-reflection-member-entry-${entry.reflection_id}`}
              >
                <div className="flex items-center justify-between gap-3 mb-2">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {entry.period_start} → {entry.period_end}
                  </p>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {entry.submitted_at ? `Submitted ${entry.submitted_at}` : entry.status}
                  </span>
                </div>
                <div className="space-y-2">
                  {Object.entries(entry.answers || {}).map(([key, value]) => (
                    <div key={key}>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {humanizeKey(key)}
                      </p>
                      <AnswerValue value={value} />
                    </div>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
