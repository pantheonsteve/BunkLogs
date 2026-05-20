/**
 * i18n key constants for visibility UI. Step 7_5 wires react-i18next; until then
 * callers pass English fallbacks via the second argument to `t()`.
 */
export const VISIBILITY_I18N_KEYS = {
  audienceDisclosure: {
    prefix: 'visibility.audienceDisclosure.prefix',
    contextHint: 'visibility.audienceDisclosure.contextHint',
  },
  sensitivePlaceholder: {
    one: 'visibility.sensitivePlaceholder.one',
    other: 'visibility.sensitivePlaceholder.other',
  },
};

/** @param {string} key @param {string} fallback */
export function t(key, fallback) {
  return fallback;
}
