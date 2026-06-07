/**
 * Disambiguates groups that share a name across programs (e.g. Session 1 vs Session 2).
 * Primary line: group name. Secondary: program, then parent unit/division when present.
 */

export function groupContextLine(group, { programName } = {}) {
  const parts = [];
  const prog = programName || group?.program_name;
  if (prog) parts.push(prog);
  if (group?.parent_name) parts.push(group.parent_name);
  return parts.join(' · ');
}

export default function GroupDisplayName({
  group,
  programName,
  showProgram = true,
  showParent = true,
  className = '',
  nameClassName = '',
  subtitleClassName = 'text-sm text-gray-500 dark:text-gray-400 mt-0.5 truncate',
}) {
  if (!group) return null;

  const subtitleParts = [];
  const prog = programName || group.program_name;
  if (showProgram && prog) subtitleParts.push(prog);
  if (showParent && group.parent_name) subtitleParts.push(group.parent_name);
  const subtitle = subtitleParts.join(' · ');

  return (
    <div className={className}>
      <span className={nameClassName || 'font-medium text-gray-900 dark:text-white'}>
        {group.name}
      </span>
      {subtitle && (
        <p className={subtitleClassName} data-testid="group-display-context">
          {subtitle}
        </p>
      )}
    </div>
  );
}
