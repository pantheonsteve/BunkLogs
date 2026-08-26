/**
 * Madrich "report a challenge" form — Step 4_8, MA7.
 *
 * Classroom select only renders when the Madrich belongs to more than
 * one classroom. Session date defaults from the classrooms endpoint
 * (upcoming/current Sunday) but is editable. The disclosure footer is
 * mandatory per MA7 — Madrichim must see who can read the submission
 * before they hit Submit.
 */

import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createChallenge, fetchClassrooms } from '../../api/madrichChallenges';
import { useAuth } from '../../auth/AuthContext';
import { useTerm } from '../../context/OrgBrandingContext';

const BODY_MAX = 2000;

const CATEGORY_OPTIONS = [
  { value: 'behavior', label: 'Student behavior' },
  { value: 'environment', label: 'Room environment' },
  { value: 'schedule', label: 'Schedule / timing' },
  { value: 'materials', label: 'Materials / curriculum' },
  { value: 'other', label: 'Other' },
];

function disclosure(term) {
  return `Faculty and the ${term('director')} can see who submitted this. `
    + 'Other Madrichim in your classroom cannot.';
}

function flattenError(err, fallback) {
  const body = err?.response?.data;
  if (!body) return err?.message || fallback;
  if (typeof body === 'string') return body;
  if (typeof body.detail === 'string') return body.detail;
  const firstField = Object.values(body)[0];
  if (Array.isArray(firstField) && typeof firstField[0] === 'string') return firstField[0];
  if (typeof firstField === 'string') return firstField;
  return fallback;
}

export default function MadrichChallengeForm() {
  const { orgSlug } = useAuth();
  const navigate = useNavigate();
  const term = useTerm();

  const [classrooms, setClassrooms] = useState([]);
  const [assignmentGroupId, setAssignmentGroupId] = useState('');
  const [sessionDate, setSessionDate] = useState('');
  const [category, setCategory] = useState('behavior');
  const [body, setBody] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    fetchClassrooms(orgSlug)
      .then((data) => {
        if (!active) return;
        const rooms = data?.classrooms || [];
        setClassrooms(rooms);
        if (rooms.length > 0) {
          setAssignmentGroupId(rooms[0].assignment_group_id);
          setSessionDate(rooms[0].session_date_default || '');
        }
      })
      .catch(() => {
        if (active) setError('Could not load your classrooms.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [orgSlug]);

  const handleClassroomChange = (value) => {
    setAssignmentGroupId(value);
    const room = classrooms.find((c) => String(c.assignment_group_id) === String(value));
    if (room?.session_date_default) setSessionDate(room.session_date_default);
  };

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!body.trim()) {
      setError('Please describe the challenge.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const challenge = await createChallenge(orgSlug, {
        assignment_group_id: Number(assignmentGroupId),
        session_date: sessionDate,
        category,
        body: body.trim(),
      });
      navigate(`/madrich/challenges/${challenge.id}`);
    } catch (err) {
      setError(flattenError(err, 'Could not submit this challenge.'));
    } finally {
      setSubmitting(false);
    }
  }, [orgSlug, assignmentGroupId, sessionDate, category, body, navigate]);

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="md-challenge-form-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (classrooms.length === 0) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="md-challenge-form-no-classroom">
        <p className="text-gray-500 dark:text-gray-400">You aren&apos;t assigned to a classroom yet.</p>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Report a challenge</h1>

      <div
        className="mb-6 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 px-4 py-3 text-sm text-blue-800 dark:text-blue-300"
        data-testid="md-challenge-disclosure"
      >
        {disclosure(term)}
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {classrooms.length > 1 && (
          <div>
            <label htmlFor="md-challenge-classroom" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Classroom
            </label>
            <select
              id="md-challenge-classroom"
              value={assignmentGroupId}
              onChange={(e) => handleClassroomChange(e.target.value)}
              className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
              data-testid="md-challenge-classroom-input"
            >
              {classrooms.map((c) => (
                <option key={c.assignment_group_id} value={c.assignment_group_id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <div>
          <label htmlFor="md-challenge-date" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Session date
          </label>
          <input
            id="md-challenge-date"
            type="date"
            value={sessionDate}
            onChange={(e) => setSessionDate(e.target.value)}
            className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
            data-testid="md-challenge-date-input"
          />
        </div>

        <div>
          <label htmlFor="md-challenge-category" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Category
          </label>
          <select
            id="md-challenge-category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
            data-testid="md-challenge-category-input"
          >
            {CATEGORY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="md-challenge-body" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            What happened?
          </label>
          <textarea
            id="md-challenge-body"
            value={body}
            onChange={(e) => setBody(e.target.value.slice(0, BODY_MAX))}
            maxLength={BODY_MAX}
            rows={6}
            placeholder="Describe the challenge…"
            className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
            data-testid="md-challenge-body-input"
          />
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 text-right">
            {body.length}/{BODY_MAX}
          </p>
        </div>

        {error && (
          <p className="text-red-600 dark:text-red-400 text-sm" data-testid="md-challenge-form-error">
            {error}
          </p>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="flex-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium py-2 px-4 transition-colors"
            data-testid="md-challenge-submit"
          >
            {submitting ? 'Submitting…' : 'Submit'}
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
  );
}
