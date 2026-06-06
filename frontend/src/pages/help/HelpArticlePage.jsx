import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import HelpMarkdown from '../../help/HelpMarkdown';
import { getHelpArticle } from '../../help/helpManifest';

export default function HelpArticlePage() {
  const { slug } = useParams();
  const article = getHelpArticle(slug);

  if (!article) {
    return (
      <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto">
        <Link
          to="/help"
          className="inline-flex items-center gap-1 text-sm text-indigo-600 dark:text-indigo-400 hover:underline mb-6"
        >
          <ArrowLeft size={14} aria-hidden="true" />
          Back to Help
        </Link>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Guide not found</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
          That article does not exist or has been removed.
        </p>
      </main>
    );
  }

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto">
      <Link
        to="/help"
        data-testid="help-back-link"
        className="inline-flex items-center gap-1 text-sm text-indigo-600 dark:text-indigo-400 hover:underline mb-6"
      >
        <ArrowLeft size={14} aria-hidden="true" />
        Back to Help
      </Link>
      <article data-testid={`help-article-${article.slug}`}>
        <HelpMarkdown content={article.content} />
      </article>
    </main>
  );
}
