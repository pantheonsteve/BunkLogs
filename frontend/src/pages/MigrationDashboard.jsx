import { useEffect, useState } from "react";

import api from "../api";

const apiUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/['"]/g, "").trim();

const PHASE_ORDER = [0, 1, 2, 3, 4, 5, 6];

const STATUS_CONFIG = {
  completed: {
    label: "Completed",
    bg: "bg-emerald-50 border-emerald-200",
    badge: "bg-emerald-100 text-emerald-800",
    icon: (
      <svg className="w-5 h-5 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  in_progress: {
    label: "In Progress",
    bg: "bg-amber-50 border-amber-200",
    badge: "bg-amber-100 text-amber-800",
    icon: (
      <svg className="w-5 h-5 text-amber-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6l4 2m6-2a10 10 0 11-20 0 10 10 0 0120 0z" />
      </svg>
    ),
  },
  pending: {
    label: "Pending",
    bg: "bg-white border-gray-200",
    badge: "bg-gray-100 text-gray-600",
    icon: (
      <svg className="w-5 h-5 text-gray-300 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
    ),
  },
  blocked: {
    label: "Blocked",
    bg: "bg-red-50 border-red-200",
    badge: "bg-red-100 text-red-700",
    icon: (
      <svg className="w-5 h-5 text-red-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
      </svg>
    ),
  },
};

function ProgressBar({ value, total, colorClass = "bg-emerald-500" }) {
  const pct = total === 0 ? 0 : Math.round((value / total) * 100);
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${colorClass} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-medium text-gray-500 w-16 text-right">
        {value}/{total} ({pct}%)
      </span>
    </div>
  );
}

function StepCard({ step, blockedBy }) {
  const isBlocked = blockedBy.length > 0 && step.status === "pending";
  const effectiveStatus = isBlocked ? "blocked" : step.status;
  const cfg = STATUS_CONFIG[effectiveStatus];

  return (
    <div className={`border rounded-lg p-4 ${cfg.bg} transition-colors`}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5">{cfg.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-gray-400">{step.id}</span>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cfg.badge}`}>
              {cfg.label}
            </span>
            {step.branch && (
              <span className="text-xs font-mono bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full border border-blue-100">
                {step.branch}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-800 leading-snug">{step.title}</p>
          {isBlocked && (
            <p className="mt-1.5 text-xs text-red-600">
              Blocked by: {blockedBy.join(", ")}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function PhaseSection({ phaseName, phaseNum, steps }) {
  const completed = steps.filter((s) => s.status === "completed").length;
  const inProgress = steps.filter((s) => s.status === "in_progress").length;
  const total = steps.length;

  // Build a set of completed step IDs in this phase so we can compute blockers
  const completedIds = new Set(steps.filter((s) => s.status === "completed").map((s) => s.id));

  // A step is blocked if any earlier step in the same phase is not completed
  const getBlockers = (step) => {
    return steps
      .filter((s) => s.step_num < step.step_num && s.status !== "completed")
      .map((s) => s.id);
  };

  const phaseColor =
    completed === total
      ? "text-emerald-700 bg-emerald-50 border-emerald-200"
      : inProgress > 0
      ? "text-amber-700 bg-amber-50 border-amber-200"
      : "text-gray-600 bg-gray-50 border-gray-200";

  return (
    <section className="mb-8">
      <div className={`flex items-center gap-3 mb-3 px-4 py-2.5 rounded-lg border ${phaseColor}`}>
        <span className="text-sm font-bold">Phase {phaseNum}</span>
        <span className="text-sm font-semibold">{phaseName}</span>
        <div className="flex-1 ml-2">
          <ProgressBar
            value={completed}
            total={total}
            colorClass={completed === total ? "bg-emerald-500" : inProgress > 0 ? "bg-amber-400" : "bg-gray-300"}
          />
        </div>
      </div>
      <div className="space-y-2 pl-1">
        {steps.map((step) => (
          <StepCard key={step.id} step={step} blockedBy={getBlockers(step)} />
        ))}
      </div>
    </section>
  );
}

export default function MigrationDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .get("/api/migration-status/")
      .then((res) => {
        setData(res.data);
        setLoading(false);
      })
      .catch((err) => {
        const status = err.response?.status;
        let message = err.message;
        if (status === 401) {
          message = "Please sign in (staff required).";
        } else if (status === 403) {
          message = "Staff access is required for the migration dashboard.";
        } else if (status) {
          message = `HTTP ${status}`;
        }
        setError(message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500 text-sm">Loading migration status…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md text-center">
          <p className="text-red-700 font-medium">Could not load migration status</p>
          <p className="text-red-500 text-sm mt-1">{error}</p>
          <p className="text-gray-500 text-xs mt-3">Make sure the backend is running at {apiUrl}</p>
        </div>
      </div>
    );
  }

  const { steps = [], git_available, has_uncommitted_changes, repo_root, error: apiError } = data;

  const totalSteps = steps.length;

  if (totalSteps === 0 && apiError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 max-w-lg text-center">
          <p className="text-amber-900 font-medium">No migration steps loaded</p>
          <p className="text-amber-800 text-sm mt-2">{apiError}</p>
          <p className="text-gray-500 text-xs mt-3">
            For local Podman, mount the monorepo root at <code className="font-mono">/repo</code> and set{" "}
            <code className="font-mono">BUNKLOGS_REPO_ROOT=/repo</code> (see{" "}
            <code className="font-mono">backend/docker-compose.local.yml</code>) so prompts and git metadata are
            available.
          </p>
        </div>
      </div>
    );
  }
  const completedSteps = steps.filter((s) => s.status === "completed").length;
  const inProgressSteps = steps.filter((s) => s.status === "in_progress").length;
  const pendingSteps = totalSteps - completedSteps - inProgressSteps;

  // Group steps by phase
  const byPhase = {};
  for (const step of steps) {
    if (!byPhase[step.phase]) byPhase[step.phase] = { name: step.phase_name, steps: [] };
    byPhase[step.phase].steps.push(step);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Migration Dashboard</h1>
            <p className="text-xs text-gray-500 mt-0.5">Strangler-Fig migration to multi-tenant architecture</p>
          </div>
          <div className="flex items-center gap-2">
            {!git_available && (
              <span className="text-xs bg-yellow-100 text-yellow-700 border border-yellow-200 px-2 py-1 rounded-full">
                Git unavailable — statuses may be inaccurate
              </span>
            )}
            {has_uncommitted_changes && (
              <span className="text-xs bg-blue-100 text-blue-700 border border-blue-200 px-2 py-1 rounded-full">
                Uncommitted changes present
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Overall summary */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-white border border-gray-200 rounded-xl p-5 text-center shadow-sm">
            <div className="text-3xl font-bold text-emerald-600">{completedSteps}</div>
            <div className="text-xs font-medium text-gray-500 mt-1 uppercase tracking-wide">Completed</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-5 text-center shadow-sm">
            <div className="text-3xl font-bold text-amber-500">{inProgressSteps}</div>
            <div className="text-xs font-medium text-gray-500 mt-1 uppercase tracking-wide">In Progress</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-5 text-center shadow-sm">
            <div className="text-3xl font-bold text-gray-400">{pendingSteps}</div>
            <div className="text-xs font-medium text-gray-500 mt-1 uppercase tracking-wide">Pending</div>
          </div>
        </div>

        {/* Overall progress bar */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 mb-8 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-gray-700">Overall Progress</span>
          </div>
          <ProgressBar value={completedSteps} total={totalSteps} />
        </div>

        {/* Phase sections */}
        {PHASE_ORDER.filter((p) => byPhase[p]).map((phaseNum) => (
          <PhaseSection
            key={phaseNum}
            phaseNum={phaseNum}
            phaseName={byPhase[phaseNum].name}
            steps={byPhase[phaseNum].steps}
          />
        ))}

        {/* Footer */}
        <div className="mt-8 pt-6 border-t border-gray-200 text-xs text-gray-400 text-center space-y-1">
          <p>Status is inferred from git log and branch names. A step shows "completed" when its ID appears in a commit message or merged branch name.</p>
          {repo_root && <p>Repo root: <code className="font-mono">{repo_root}</code></p>}
        </div>
      </div>
    </div>
  );
}
