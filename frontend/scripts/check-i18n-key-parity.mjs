#!/usr/bin/env node
/**
 * Cross-locale key parity check (Step 7_5, spec item #15).
 *
 * For every namespace under `frontend/src/locales/en/`, walks the leaf
 * keys and warns when any of them are missing from `<lang>/<ns>.json`
 * for each `<lang>` declared UI-supported in `frontend/src/i18n/index.js`
 * (currently `es` only — Hebrew is intentionally exempt because
 * `react-i18next` falls back to English at runtime).
 *
 * The script always exits 0: this is a developer guardrail, not a CI
 * gate. The plan keeps the lint warning-only while the codebase is
 * mid-localization.
 *
 * Run via `npm run lint:i18n`.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const localesDir = resolve(here, '..', 'src', 'locales');

const UI_SUPPORTED_TARGETS = ['es'];

function loadJson(path) {
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch (err) {
    return { __error: err.message };
  }
}

function leafKeys(obj, prefix = '') {
  if (obj === null || typeof obj !== 'object' || Array.isArray(obj)) {
    return [prefix];
  }
  return Object.entries(obj).flatMap(([key, value]) => {
    if (key.startsWith('_')) return [];
    const next = prefix ? `${prefix}.${key}` : key;
    return leafKeys(value, next);
  });
}

function listNamespaces(langDir) {
  return readdirSync(langDir)
    .filter((entry) => entry.endsWith('.json'))
    .map((entry) => entry.replace(/\.json$/, ''));
}

const enDir = resolve(localesDir, 'en');
const namespaces = listNamespaces(enDir);

let warnings = 0;
for (const ns of namespaces) {
  const enKeys = new Set(leafKeys(loadJson(resolve(enDir, `${ns}.json`))));
  for (const lang of UI_SUPPORTED_TARGETS) {
    const langPath = resolve(localesDir, lang, `${ns}.json`);
    const langBody = loadJson(langPath);
    if (langBody.__error) {
      console.warn(
        `[i18n-key-parity] WARN: ${lang}/${ns}.json could not be read: ${langBody.__error}`,
      );
      warnings += 1;
      continue;
    }
    const langKeys = new Set(leafKeys(langBody));
    const missing = [...enKeys].filter((k) => !langKeys.has(k));
    if (missing.length > 0) {
      console.warn(
        `[i18n-key-parity] WARN: ${missing.length} key(s) missing in ${lang}/${ns}.json:`,
      );
      for (const key of missing) console.warn(`  - ${key}`);
      warnings += missing.length;
    }
  }
}

if (warnings === 0) {
  console.log('[i18n-key-parity] OK: all UI-supported locales match the English baseline.');
} else {
  console.warn(`[i18n-key-parity] DONE: ${warnings} warning(s).`);
}

process.exit(0);
