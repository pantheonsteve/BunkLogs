import { VISIBILITY_I18N_KEYS, t } from './visibilityI18n';

/**
 * Count-only placeholder when the viewer cannot read sensitive notes.
 *
 * @param {{ count: number, gatingRole: string }} props
 */
export default function SensitiveNotePlaceholder({ count = 0, gatingRole }) {
  if (!count || count < 1 || !gatingRole) return null;

  const template =
    count === 1
      ? t(
          VISIBILITY_I18N_KEYS.sensitivePlaceholder.one,
          '{{count}} sensitive note ({{role}})',
        )
      : t(
          VISIBILITY_I18N_KEYS.sensitivePlaceholder.other,
          '{{count}} sensitive notes ({{role}})',
        );

  const text = template
    .replace('{{count}}', String(count))
    .replace('{{role}}', gatingRole);

  return (
    <p
      data-testid="sensitive-note-placeholder"
      className="text-sm italic text-gray-500 dark:text-gray-400"
    >
      {text}
    </p>
  );
}
