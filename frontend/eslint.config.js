/**
 * ESLint flat config — Step 7_5 i18n guardrail.
 *
 * The project did not previously ship ESLint, and adding the standard React
 * preset across the codebase would surface hundreds of unrelated lints. This
 * config is intentionally narrow: it only wires `eslint-plugin-i18next`
 * (its bundled `flat/recommended` rule set, re-graded to "warn") so that
 * hardcoded JSX strings produce a warning during local lint runs without
 * breaking CI. As the migration progresses (Step 7_6+), individual file
 * scopes can be tightened to "error" once they have been fully localized.
 *
 * Run with `npm run lint:i18n`.
 */
import i18next from 'eslint-plugin-i18next';

export default [
  i18next.configs['flat/recommended'],
  {
    files: ['src/**/*.{js,jsx,ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2024,
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    rules: {
      // Re-grade the recommended rule from error -> warn. We want guardrails
      // on hardcoded strings without breaking CI while the codebase is
      // still mid-localization.
      'i18next/no-literal-string': 'warn',
    },
  },
  {
    // Locale JSON files and the i18n bootstrap itself are deliberately
    // string-heavy; linting them for "no literal string" is nonsensical.
    ignores: [
      'src/locales/**',
      'src/i18n/**',
      'dist/**',
      'node_modules/**',
      // Tests intentionally contain literal user-visible strings to
      // assert the rendered output; lint them as a separate (future) pass.
      'src/**/__tests__/**',
      'src/**/*.test.{js,jsx,ts,tsx}',
    ],
  },
];
