import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, Search } from 'lucide-react';
import { listHelpArticles } from '../../help/helpManifest';

function ArticleCard({ article }) {
  return (
    <Link
      to={`/help/${article.slug}`}
      data-testid={`help-card-${article.slug}`}
      className="group flex flex-col rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 shadow-sm hover:shadow-md hover:border-indigo-300 dark:hover:border-indigo-700 transition-all"
    >
      <div className="flex items-start gap-3 mb-2">
        <span className="inline-flex items-center justify-center w-9 h-9 rounded-lg bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 shrink-0">
          <BookOpen size={18} aria-hidden="true" />
        </span>
        <h2 className="text-base font-semibold text-gray-900 dark:text-white group-hover:text-indigo-700 dark:group-hover:text-indigo-300">
          {article.title}
        </h2>
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400 flex-1">
        {article.summary}
      </p>
      {article.tags?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {article.tags.map((tag) => (
            <span
              key={tag}
              className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </Link>
  );
}

export default function HelpIndexPage() {
  const articles = useMemo(() => listHelpArticles(), []);
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return articles;
    return articles.filter(
      (a) =>
        a.title.toLowerCase().includes(q) ||
        a.summary.toLowerCase().includes(q) ||
        (a.tags || []).some((t) => t.toLowerCase().includes(q)),
    );
  }, [articles, query]);

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-5xl mx-auto">
      <header className="mb-8 border-b-2 border-indigo-500/70 dark:border-indigo-400/60 pb-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Help</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Guides for admins and program leads—templates, dashboards, assignments, and more.
        </p>
      </header>

      <div className="relative mb-6">
        <label htmlFor="help-search" className="sr-only">
          Search guides
        </label>
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          aria-hidden="true"
        />
        <input
          id="help-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search guides…"
          data-testid="help-search"
          className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="help-empty">
          No guides match your search.
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4" data-testid="help-article-grid">
          {filtered.map((article) => (
            <ArticleCard key={article.slug} article={article} />
          ))}
        </div>
      )}
    </main>
  );
}
