import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../api';

// ---------------------------------------------------------------------------
// Icons (inline SVG to avoid extra deps)
// ---------------------------------------------------------------------------

function IconCircle() {
  return (
    <svg
      aria-hidden="true"
      className="w-4 h-4 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      viewBox="0 0 24 24"
    >
      <circle cx="12" cy="12" r="9" />
    </svg>
  );
}

function IconCheck({ star = false }) {
  return (
    <span className="inline-flex items-center gap-0.5">
      <svg
        aria-hidden="true"
        className="w-4 h-4 shrink-0 text-green-600"
        fill="none"
        stroke="currentColor"
        strokeWidth={2.5}
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
      </svg>
      {star && (
        <svg
          aria-hidden="true"
          className="w-3 h-3 shrink-0 text-blue-500"
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.286 3.97a1 1 0 00.95.69h4.178c.969 0 1.371 1.24.588 1.81l-3.385 2.46a1 1 0 00-.364 1.118l1.287 3.97c.3.921-.755 1.688-1.54 1.118l-3.385-2.46a1 1 0 00-1.175 0l-3.385 2.46c-.784.57-1.838-.197-1.539-1.118l1.287-3.97a1 1 0 00-.364-1.118L2.049 9.397c-.783-.57-.38-1.81.588-1.81h4.178a1 1 0 00.95-.69l1.284-3.97z" />
        </svg>
      )}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Subject pill popover
// ---------------------------------------------------------------------------

function CoveragePopover({ subject, onClose, onView }) {
  const ref = useRef(null);

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [onClose]);

  return (
    <div
      ref={ref}
      role="dialog"
      aria-label={`Coverage details for ${subject.preferred_name}`}
      className="absolute z-10 top-full left-1/2 -translate-x-1/2 mt-1 w-52 rounded-lg shadow-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-3 text-xs"
    >
      <p className="font-medium text-gray-800 dark:text-gray-100 mb-1">{subject.name}</p>
      {subject.covered_by_name && (
        <p className="text-gray-600 dark:text-gray-400">
          Logged by <span className="font-medium">{subject.covered_by_name}</span>
        </p>
      )}
      <div className="mt-2 flex gap-2">
        {subject.covered_by_me && onView && (
          <button
            type="button"
            onClick={() => {
              onView(subject);
              onClose();
            }}
            className="text-blue-600 dark:text-blue-400 underline"
          >
            View
          </button>
        )}
        <button type="button" onClick={onClose} className="text-gray-500 dark:text-gray-400">
          Close
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SubjectPill
// ---------------------------------------------------------------------------

function SubjectPill({ subject, onTap }) {
  const [popoverOpen, setPopoverOpen] = useState(false);
  const navigate = useNavigate();

  function pillStyle() {
    if (subject.covered_by_me) {
      return 'border-blue-400 bg-blue-50 dark:bg-blue-950/40 text-blue-900 dark:text-blue-100';
    }
    if (subject.covered) {
      return 'border-green-400 bg-green-50 dark:bg-green-950/40 text-green-900 dark:text-green-100';
    }
    return 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100';
  }

  function statusIcon() {
    if (subject.covered_by_me) return <IconCheck star />;
    if (subject.covered) return <IconCheck />;
    return (
      <span className="text-gray-400 dark:text-gray-500">
        <IconCircle />
      </span>
    );
  }

  function ariaLabel() {
    if (subject.covered_by_me) return `${subject.name}, logged by you`;
    if (subject.covered) {
      return subject.covered_by_name
        ? `${subject.name}, logged by ${subject.covered_by_name}`
        : `${subject.name}, logged`;
    }
    return `${subject.name}, not yet logged`;
  }

  function handleClick() {
    if (subject.covered) {
      setPopoverOpen(true);
    } else {
      onTap(subject);
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        aria-label={ariaLabel()}
        onClick={handleClick}
        className={`min-h-[44px] min-w-[44px] w-full flex items-center justify-center gap-1 px-2 py-2 rounded-lg border text-sm font-medium transition-colors ${pillStyle()}`}
      >
        {statusIcon()}
        <span className="truncate">{subject.preferred_name}</span>
      </button>
      {popoverOpen && (
        <CoveragePopover
          subject={subject}
          onClose={() => setPopoverOpen(false)}
          onView={(s) => navigate(`/reflections/${s.reflection_id}`)}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section: self
// ---------------------------------------------------------------------------

function SelfSection({ task, onNavigate }) {
  const ss = task.self_status;
  const done = ss?.submitted;

  return (
    <div
      className={`rounded-xl border p-4 cursor-pointer transition-colors ${
        done
          ? 'border-green-300 bg-green-50 dark:bg-green-950/30 dark:border-green-800'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-300 dark:hover:border-blue-600'
      }`}
      role="button"
      tabIndex={0}
      aria-label={`${task.template.name} — ${done ? 'completed' : 'not yet submitted'}`}
      onClick={() => !done && onNavigate(task)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          if (!done) onNavigate(task);
        }
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm text-gray-900 dark:text-white">{task.template.name}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Your reflection</p>
        </div>
        <span className="shrink-0 mt-0.5">{done ? <IconCheck /> : <span className="text-gray-400"><IconCircle /></span>}</span>
      </div>
      {done && ss.submitted_at && (
        <p className="text-xs text-green-700 dark:text-green-400 mt-2">
          Submitted {new Date(ss.submitted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section: single_subject / multi_subject
// ---------------------------------------------------------------------------

function SubjectSection({ task, onPillTap }) {
  const { covered, total } = task.completion;
  const remaining = total - covered;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="font-medium text-sm text-gray-900 dark:text-white">{task.template.name}</p>
          {task.assignment_group && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{task.assignment_group.name}</p>
          )}
        </div>
        <span
          className={`text-xs font-medium px-2 py-0.5 rounded-full ${
            remaining === 0
              ? 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300'
              : 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300'
          }`}
        >
          {covered}/{total}
        </span>
      </div>

      <div
        className="grid gap-2"
        style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(80px, 1fr))' }}
      >
        {task.subjects.map((subject) => (
          <SubjectPill key={subject.person_id} subject={subject} onTap={() => onPillTap(task, subject)} />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section: group
// ---------------------------------------------------------------------------

function GroupSection({ task, onNavigate }) {
  const done = task.completion.covered === task.completion.total;

  return (
    <div
      className={`rounded-xl border p-4 cursor-pointer transition-colors ${
        done
          ? 'border-green-300 bg-green-50 dark:bg-green-950/30 dark:border-green-800'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-300 dark:hover:border-blue-600'
      }`}
      role="button"
      tabIndex={0}
      aria-label={`${task.template.name} for ${task.assignment_group?.name} — ${done ? 'completed' : 'pending'}`}
      onClick={() => !done && onNavigate(task)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          if (!done) onNavigate(task);
        }
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm text-gray-900 dark:text-white">{task.template.name}</p>
          {task.assignment_group && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{task.assignment_group.name}</p>
          )}
        </div>
        <span className="shrink-0 mt-0.5">{done ? <IconCheck /> : <span className="text-gray-400"><IconCircle /></span>}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Summary bar
// ---------------------------------------------------------------------------

function SummaryBar({ tasks }) {
  const total = tasks.length;
  const completed = tasks.filter((t) => t.completion.covered >= t.completion.total).length;
  const waiting = total - completed;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 mb-6">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-gray-900 dark:text-white">
          {waiting > 0 ? `${waiting} task${waiting !== 1 ? 's' : ''} waiting` : 'All done!'}
        </p>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {completed}/{total} completed
        </span>
      </div>
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
        <div
          className="bg-blue-500 h-2 rounded-full transition-all"
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${pct}% complete`}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Props:
//   variant: 'page' — standalone /tasks layout (narrow column, gray backdrop)
//            'embedded' — inside CounselorDashboard card (full width)
// ---------------------------------------------------------------------------

export default function ReflectionTasksPanel({ variant = 'page' }) {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const embedded = variant === 'embedded';

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await api.get('/api/v1/reflections/my-tasks/');
      setTasks(data.tasks || []);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        typeof detail === 'string'
          ? detail
          : 'Could not load your tasks. Please try again.',
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  function buildFormUrl(task, subject = null) {
    const params = new URLSearchParams({
      template: task.template.id,
      program: task.program_slug,
      period_start: task.period.start,
      period_end: task.period.end,
    });
    if (task.assignment_group) {
      params.set('assignment_group', task.assignment_group.id);
    }
    if (subject) {
      params.set('subject', subject.person_id);
      params.set('subject_name', subject.name);
    }
    if (task.subject_mode === 'group' && task.assignment_group) {
      params.set('subject_group', task.assignment_group.id);
    }
    return `/reflect?${params.toString()}`;
  }

  function handleSelfNavigate(task) {
    navigate(buildFormUrl(task));
  }

  function handleGroupNavigate(task) {
    navigate(buildFormUrl(task));
  }

  function handlePillTap(task, subject) {
    navigate(buildFormUrl(task, subject));
  }

  const today = new Date();
  const headingLabel = today.toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });

  // 3.27: surface /supervisor/coverage only when the viewer is an author of
  // at least one roster group. Plain self-only reflectors don't see the link
  // because the page would be empty for them.
  const showCoverageLink = useMemo(
    () =>
      Array.isArray(tasks)
      && tasks.some((t) => t.assignment_group),
    [tasks],
  );

  const inner = (
    <>
      {!embedded && (
        <header className="mb-6 flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Today</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{headingLabel}</p>
          </div>
          {showCoverageLink && (
            <Link
              to="/supervisor/coverage"
              data-testid="tasks-coverage-link"
              className="shrink-0 inline-flex items-center gap-1 mt-1 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Coverage →
            </Link>
          )}
        </header>
      )}

      {loading && <p className="text-gray-500 dark:text-gray-400 text-sm">Loading tasks…</p>}

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-950/40 dark:border-red-800 px-4 py-3 text-sm text-red-900 dark:text-red-100"
        >
          {error}
        </div>
      )}

      {!loading && !error && tasks !== null && (
        <>
          <SummaryBar tasks={tasks} />

          {tasks.length === 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-12">No tasks for today.</p>
          )}

          <div className={`space-y-4 ${embedded ? 'lg:grid lg:grid-cols-2 lg:gap-4 lg:space-y-0' : ''}`} data-testid="tasks-list">
            {tasks.map((task) => {
              if (task.subject_mode === 'self') {
                return <SelfSection key={task.id} task={task} onNavigate={handleSelfNavigate} />;
              }
              if (task.subject_mode === 'group') {
                return <GroupSection key={task.id} task={task} onNavigate={handleGroupNavigate} />;
              }
              return <SubjectSection key={task.id} task={task} onPillTap={handlePillTap} />;
            })}
          </div>
        </>
      )}
    </>
  );

  if (embedded) {
    return <div className="w-full">{inner}</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 px-4 py-6 pb-24">
      <div className="max-w-lg mx-auto">{inner}</div>
    </div>
  );
}
