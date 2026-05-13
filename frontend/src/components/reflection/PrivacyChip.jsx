import { Lock } from 'lucide-react';

const TOOLTIP =
  'Filed privately. Only supervisors, admins, and (when subject_visible is on) the subject can read this entry.';

/**
 * PrivacyChip — shared indicator for ``Reflection.team_visibility === 'supervisors_only'``.
 *
 * Returns null for any other value (``'team'`` or missing) so callers can
 * unconditionally render ``<PrivacyChip teamVisibility={x} />`` without
 * branching at the call site.
 *
 * Sizes:
 *   - "sm" (default): pill with lock glyph + "Filed privately" label.
 *   - "icon": lock-only badge for very tight layouts (TrendCell uses this).
 *
 * The component is purely presentational. Visibility is enforced server-side
 * (see ``reflections_visible_to`` in backend/bunk_logs/core/permissions/visibility.py);
 * if a private reflection is in the payload at all, the viewer is allowed to see
 * it -- the chip is communication, not access control.
 */
export default function PrivacyChip({ teamVisibility, size = 'sm' }) {
  if (teamVisibility !== 'supervisors_only') return null;

  if (size === 'icon') {
    return (
      <span
        data-testid="privacy-chip"
        aria-label="Filed privately"
        title={TOOLTIP}
        className="inline-flex items-center justify-center rounded-full bg-indigo-600 text-white w-4 h-4 shadow-sm"
      >
        <Lock size={10} aria-hidden="true" />
      </span>
    );
  }

  return (
    <span
      data-testid="privacy-chip"
      title={TOOLTIP}
      className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200"
    >
      <Lock size={10} aria-hidden="true" />
      <span>Filed privately</span>
    </span>
  );
}
