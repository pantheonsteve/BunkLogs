import { ChevronDown } from 'lucide-react';

import { useAdminProgram } from '../../context/AdminProgramContext';
import { useTerm } from '../../context/OrgBrandingContext';
import { programShortLabel } from '../../lib/programLabel';

/**
 * The single program control for the whole admin, mounted in the topbar.
 * Every admin page inherits it, so the ~90-character program name no
 * longer has to be repeated under each row of a list.
 *
 * The trigger shows the derived short label ("2026-27"); the native
 * dropdown keeps the full names, which is where an admin actually needs
 * to tell two similarly-dated programs apart. The select is laid over the
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

  return (
    <div
      className="relative inline-flex items-center gap-1.5 pl-3 pr-2 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors"
      data-testid="admin-program-switcher"
    >
      <span className="text-sm font-semibold text-gray-900 dark:text-white whitespace-nowrap">
        {short}
      </span>
      {program && !program.is_active && (
        <span className="text-xs text-gray-500 dark:text-gray-400">(Ended)</span>
      )}
      <ChevronDown size={14} className="text-gray-400" aria-hidden="true" />
      <select
        value={programId}
        onChange={(e) => setProgramId(e.target.value)}
        aria-label={`${label} in scope`}
        title={program?.name || ''}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
      >
        {programs.map((p) => (
          <option key={p.id} value={String(p.id)}>
            {p.name}
            {p.is_active ? '' : ' (Ended)'}
          </option>
        ))}
      </select>
    </div>
  );
}
