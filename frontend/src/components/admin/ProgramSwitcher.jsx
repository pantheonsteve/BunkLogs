import { ChevronDown } from 'lucide-react';

import { useAdminProgram } from '../../context/AdminProgramContext';
import { useTerm } from '../../context/OrgBrandingContext';
import { programDisplayName, programShortLabel } from '../../lib/programLabel';

/**
 * The single program control for the whole admin, mounted in the topbar.
 * Every admin page inherits it, so the ~90-character program name no
 * longer has to be repeated under each row of a list.
 *
 * The trigger shows the short label (the admin-set alias, else "2026-27");
 * the native dropdown shows the alias or full name, which is where an
 * admin needs to tell two similarly-dated programs apart. The select is laid over the
 * visible label rather than styled directly, because a native select can
 * only render its selected option's own text.
 *
 * The label follows the tenant's vocabulary: "School year" at a religious
 * school, "Program" at camp.
 */
export default function ProgramSwitcher() {
  const { programs, programId, program, ready, setProgramId } = useAdminProgram();
  const term = useTerm();
  const label = term('program', { capitalize: true });

  if (!ready || programs.length === 0) return null;

  const short = programShortLabel(program) || label;
  // `is_active` stays true until an admin ends the program, so the date
  // check keeps a finished season from reading as live.
  const today = new Date().toLocaleDateString('en-CA');
  const live = Boolean(program?.is_active) && (!program.end_date || program.end_date >= today);

  return (
    <div
      className="relative inline-flex items-center gap-2 min-h-10 max-w-[14rem] px-3.5 rounded-lg border border-[#d9d6e4] dark:border-gray-600 bg-white dark:bg-gray-900 hover:border-violet-300 dark:hover:border-violet-700 focus-within:ring-2 focus-within:ring-brand transition-colors"
      data-testid="admin-program-switcher"
    >
      <span
        className={`w-2 h-2 rounded-full shrink-0 ${live ? 'bg-ok-ink' : 'bg-muted'}`}
        aria-hidden="true"
      />
      <span className="text-sm font-semibold text-ink truncate">
        {short}
      </span>
      {program && !program.is_active && (
        <span className="text-xs text-muted whitespace-nowrap">(Ended)</span>
      )}
      <ChevronDown size={16} className="text-ink-2 shrink-0" aria-hidden="true" />
      <select
        value={programId}
        onChange={(e) => setProgramId(e.target.value)}
        aria-label={`${label} in scope`}
        title={program?.name || ''}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
      >
        {programs.map((p) => (
          <option key={p.id} value={String(p.id)}>
            {programDisplayName(p)}
            {p.is_active ? '' : ' (Ended)'}
          </option>
        ))}
      </select>
    </div>
  );
}
