/**
 * Help center manifest. Article bodies live in docs/features/*.md;
 * metadata here drives the index, search, and sort order.
 */

const articleModules = import.meta.glob('../../../docs/features/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
});

/** @type {import('./helpTypes').HelpArticleMeta[]} */
export const HELP_ARTICLE_META = [
  {
    slug: 'logs-reflections-observations',
    title: 'Log Entries, Reflections, and Observations',
    summary:
      'Three ways staff capture input about people and groups—and where each one appears in the app.',
    tags: ['getting-started', 'dashboards'],
    sortOrder: 10,
  },
  {
    slug: 'form-types',
    title: 'Form types (subject modes)',
    summary:
      'Self-reflection vs one person vs several people vs group—and which dashboard each uses.',
    tags: ['templates', 'getting-started'],
    sortOrder: 20,
  },
  {
    slug: 'templates-and-assignments',
    title: 'Templates & assignments',
    summary:
      'Create, publish, and assign forms; delete unused templates or archive forms that have responses.',
    tags: ['templates', 'assignments'],
    sortOrder: 30,
  },
  {
    slug: 'viewing-responses',
    title: 'Viewing form responses',
    summary:
      'Find submitted answers via Bunk Logs, Reflections, group dashboards, and person profiles.',
    tags: ['dashboards', 'templates'],
    sortOrder: 40,
  },
  {
    slug: 'concern-inbox',
    title: 'Concerns Inbox',
    summary:
      'Triage open-concern text and low ratings from completed reflection forms.',
    tags: ['dashboards', 'supervise'],
    sortOrder: 50,
  },
];

const contentBySlug = Object.fromEntries(
  Object.entries(articleModules).map(([path, raw]) => {
    const match = path.match(/\/([^/]+)\.md$/);
    const fileSlug = match?.[1];
    return fileSlug && fileSlug !== 'README' ? [fileSlug, raw] : null;
  }).filter(Boolean),
);

/** @returns {import('./helpTypes').HelpArticle[]} */
export function listHelpArticles() {
  return HELP_ARTICLE_META
    .filter((meta) => contentBySlug[meta.slug])
    .map((meta) => ({
      ...meta,
      content: contentBySlug[meta.slug],
    }))
    .sort((a, b) => a.sortOrder - b.sortOrder);
}

/** @param {string} slug */
export function getHelpArticle(slug) {
  const meta = HELP_ARTICLE_META.find((a) => a.slug === slug);
  const content = contentBySlug[slug];
  if (!meta || !content) return null;
  return { ...meta, content };
}
