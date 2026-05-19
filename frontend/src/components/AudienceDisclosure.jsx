import { VISIBILITY_I18N_KEYS, t } from './visibilityI18n';

/**
 * Write-time audience disclosure shown above content forms.
 *
 * @param {{ audience: string[], contextHint?: string }} props
 * `audience` — role labels from the API (`audience_labels()`), e.g. ["Counselor", "Unit Head"].
 */
export default function AudienceDisclosure({ audience = [], contextHint }) {
  if (!audience?.length) return null;

  const prefix = t(
    VISIBILITY_I18N_KEYS.audienceDisclosure.prefix,
    'Visible to:',
  );
  const hint = contextHint
    ? t(VISIBILITY_I18N_KEYS.audienceDisclosure.contextHint, contextHint)
    : null;

  return (
    <div
      data-testid="audience-disclosure"
      className="mb-3 rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-800/60 dark:text-gray-200"
      role="note"
    >
      <p>
        <span className="font-medium">{prefix}</span>{' '}
        <span data-testid="audience-disclosure-labels">{audience.join(', ')}</span>
      </p>
      {hint ? (
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{hint}</p>
      ) : null}
    </div>
  );
}
