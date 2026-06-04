import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CheckCircle2, Circle, ClipboardList } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../api';

const CARD_BASE =
  'rounded-2xl border bg-white dark:bg-gray-900 shadow-sm overflow-hidden';
const CARD_PENDING =
  'border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-md transition-all';
const CARD_DONE =
  'border-emerald-200 dark:border-emerald-800 bg-emerald-50/60 dark:bg-emerald-950/25';

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
      return 'border-indigo-400 bg-indigo-50 dark:bg-indigo-950/50 text-indigo-950 dark:text-indigo-100 shadow-sm';
    }
    if (subject.covered) {
      return 'border-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 text-emerald-950 dark:text-emerald-100 shadow-sm';
    }
    return 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 hover:border-indigo-300 dark:hover:border-indigo-500';
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
        className={`min-h-[48px] min-w-[48px] w-full flex items-center justify-center gap-1.5 px-2.5 py-2.5 rounded-xl border-2 text-sm font-semibold transition-colors ${pillStyle()}`}
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

function TaskStatusIcon({ done, star = false }) {
  if (done) {
    return star ? <IconCheck star /> : <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" aria-hidden="true" />;
  }
  return <Circle className="w-5 h-5 text-gray-400 dark:text-gray-500 shrink-0" aria-hidden="true" />;
}

function SelfSection({ task, onNavigate }) {
  const ss = task.self_status;
  const done = ss?.submitted;

  return (
    <article
      className={`${CARD_BASE} ${done ? CARD_DONE : CARD_PENDING} ${!done ? 'cursor-pointer' : ''}`}
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
      <div
        className={`h-1 ${done ? 'bg-emerald-500' : 'bg-gradient-to-r from-indigo-500 via-blue-500 to-violet-500'}`}
        aria-hidden="true"
      />
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-base text-gray-900 dark:text-white">{task.template.name}</p>
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-0.5">Your reflection</p>
          </div>
          <TaskStatusIcon done={done} />
        </div>
        {done && ss.submitted_at ? (
          <p className="text-sm font-medium text-emerald-800 dark:text-emerald-300 mt-3">
            Submitted {new Date(ss.submitted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        ) : (
          <p className="text-sm text-indigo-700 dark:text-indigo-300 mt-3 font-medium">
            Tap to open form →
          </p>
        )}
      </div>
    </article>
  );
}

// ---------------------------------------------------------------------------
// Section: single_subject / multi_subject
// ---------------------------------------------------------------------------

function SubjectSection({ task, onPillTap }) {
  const { covered, total } = task.completion;
  const remaining = total - covered;

  const complete = remaining === 0;

  return (
    <article className={`${CARD_BASE} ${complete ? CARD_DONE : 'border-gray-200 dark:border-gray-700'}`}>
      <div
        className={`h-1 ${complete ? 'bg-emerald-500' : 'bg-gradient-to-r from-indigo-500 via-blue-500 to-violet-500'}`}
        aria-hidden="true"
      />
      <div className="p-5">
      <div className="flex items-center justify-between mb-4 gap-3">
        <div className="min-w-0">
          <p className="font-semibold text-base text-gray-900 dark:text-white">{task.template.name}</p>
          {task.assignment_group && (
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-0.5">{task.assignment_group.name}</p>
          )}
        </div>
        <span
          className={`shrink-0 text-xs font-bold px-2.5 py-1 rounded-full tabular-nums ${
            complete
              ? 'bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-200'
              : 'bg-amber-100 dark:bg-amber-900/60 text-amber-900 dark:text-amber-200'
          }`}
        >
          {covered}/{total}
        </span>
      </div>

      <div
        className="grid gap-2.5"
        style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(88px, 1fr))' }}
      >
        {task.subjects.map((subject) => (
          <SubjectPill key={subject.person_id} subject={subject} onTap={() => onPillTap(task, subject)} />
        ))}
      </div>
      </div>
    </article>
  );
}

// ---------------------------------------------------------------------------
// Section: group
// ---------------------------------------------------------------------------

function GroupSection({ task, onNavigate }) {
  const done = task.completion.covered === task.completion.total;

  return (
    <article
      className={`${CARD_BASE} ${done ? CARD_DONE : CARD_PENDING} ${!done ? 'cursor-pointer' : ''}`}
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
      <div
        className={`h-1 ${done ? 'bg-emerald-500' : 'bg-gradient-to-r from-indigo-500 via-blue-500 to-violet-500'}`}
        aria-hidden="true"
      />
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-base text-gray-900 dark:text-white">{task.template.name}</p>
            {task.assignment_group && (
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-0.5">{task.assignment_group.name}</p>
            )}
          </div>
          <TaskStatusIcon done={done} />
        </div>
        {!done ? (
          <p className="text-sm text-indigo-700 dark:text-indigo-300 mt-3 font-medium">
            Tap to complete group reflection →
          </p>
        ) : null}
      </div>
    </article>
  );
}

// ---------------------------------------------------------------------------
// Summary bar
// ---------------------------------------------------------------------------

function AllDoneCelebration() {
  return (
    <div
      className="flex items-start gap-4 rounded-2xl border border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-950/40 px-5 py-5 shadow-sm"
      data-testid="tasks-all-done-celebration"
      role="status"
    >
      <CheckCircle2 className="w-8 h-8 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
      <div>
        <p className="text-lg font-semibold text-emerald-950 dark:text-emerald-50">
          You&apos;re all caught up — thank you!
        </p>
        <p className="text-sm text-emerald-900 dark:text-emerald-200 mt-1">
          Every reflection for today is submitted. Your camp team appreciates you showing up.
        </p>
      </div>
    </div>
  );
}

function SummaryBar({ tasks }) {
  const total = tasks.length;
  const completed = tasks.filter((t) => t.completion.covered >= t.completion.total).length;
  const waiting = total - completed;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
  const allDone = total > 0 && waiting === 0;

  return (
    <section className="mb-6 space-y-4" aria-label="Today's progress">
      {allDone ? <AllDoneCelebration /> : null}
      <div className={`${CARD_BASE} border-gray-200 dark:border-gray-700 p-5`}>
        <div className="flex flex-wrap items-end justify-between gap-3 mb-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              Today&apos;s progress
            </p>
            <p className="text-xl font-semibold text-gray-900 dark:text-white mt-0.5 tabular-nums">
              {completed}
              <span className="text-gray-500 dark:text-gray-400 font-medium text-base">
                {' '}
                / {total} assignments
              </span>
            </p>
          </div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
            {waiting > 0 ? (
              <span className="text-amber-800 dark:text-amber-200">
                {waiting} remaining
              </span>
            ) : (
              <span className="text-emerald-800 dark:text-emerald-200">Complete</span>
            )}
          </p>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${
              allDone ? 'bg-emerald-500' : 'bg-indigo-600 dark:bg-indigo-500'
            }`}
            style={{ width: `${pct}%` }}
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`${pct}% complete`}
          />
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Props:
//   variant: 'page' — standalone /tasks layout (narrow column, gray backdrop)
//            'embedded' — inside CounselorDashboard card (full width)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Notes requiring response section (Step 7_19, FA8 — Notes are distinct from tasks)
// ---------------------------------------------------------------------------

function ObservationsRequiringResponseSection() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    api.get('/api/v1/observations/inbox/').then(r => {
      const inbox = r.data.results ?? r.data;
      setItems(inbox.filter(n => n.unread).slice(0, 5));
    }).catch(() => {});
  }, []);

  if (items.length === 0) return null;

  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
        Observations requiring response
      </h2>
      <div className={`${CARD_BASE} border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-800`}>
        {items.map(item => (
          <Link
            key={item.id}
            to={`/observations/${item.id}`}
            className="flex items-center gap-3 px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors"
          >
            <span className="w-2.5 h-2.5 rounded-full bg-violet-600 dark:bg-violet-400 shrink-0" />
            <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate flex-1">
              {item.preview ?? item.body?.slice(0, 80) ?? 'Observation'}
            </span>
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400 shrink-0">
              From {item.author?.name ?? item.author?.full_name}
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}

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
        <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex gap-4 min-w-0">
            <div className="hidden sm:flex shrink-0 w-12 h-12 rounded-xl bg-indigo-100 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 items-center justify-center">
              <ClipboardList className="w-6 h-6 text-indigo-700 dark:text-indigo-300" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                My work
              </p>
              <h1 className="text-2xl sm:text-3xl font-semibold text-gray-900 dark:text-white mt-0.5">
                My Tasks
              </h1>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-200 mt-1">{headingLabel}</p>
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-2 max-w-2xl">
                Tap a camper or assignment below to file today&apos;s reflections. Completed work
                stays visible so you can review or edit.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 shrink-0 sm:pt-1">
            <Link
              to="/my-reflections"
              data-testid="tasks-my-reflections-link"
              className="inline-flex items-center rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-4 py-2 text-sm font-medium text-gray-800 dark:text-gray-100 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              My reflections
            </Link>
            {showCoverageLink && (
              <Link
                to="/groups/performance"
                data-testid="tasks-coverage-link"
                className="inline-flex items-center rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-4 py-2 text-sm font-medium text-gray-800 dark:text-gray-100 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                Performance →
              </Link>
            )}
          </div>
        </header>
      )}

      {loading && (
        <p className="text-gray-700 dark:text-gray-300 text-sm font-medium">Loading tasks…</p>
      )}

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
            <p className="text-sm text-gray-700 dark:text-gray-300 text-center py-16 rounded-2xl border border-dashed border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900">
              No tasks for today.
            </p>
          )}

          <div
            className={
              embedded
                ? 'grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5'
                : 'grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5'
            }
            data-testid="tasks-list"
          >
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

          <ObservationsRequiringResponseSection />
        </>
      )}
    </>
  );

  if (embedded) {
    return <div className="w-full">{inner}</div>;
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 pb-24 w-full max-w-[80rem] mx-auto">
      {inner}
    </div>
  );
}
