import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * Rewrite intra-guide links like [Title](other-guide.md) to /help/other-guide.
 */
function rewriteHref(href) {
  if (!href || typeof href !== 'string') return href;
  if (href.startsWith('http://') || href.startsWith('https://') || href.startsWith('/')) {
    return href;
  }
  const mdMatch = href.match(/^([^#?]+\.md)(.*)$/);
  if (mdMatch) {
    const slug = mdMatch[1].replace(/\.md$/, '');
    return `/help/${slug}${mdMatch[2] || ''}`;
  }
  return href;
}

const proseClass =
  'help-prose max-w-none text-gray-700 dark:text-gray-300 ' +
  '[&_h1]:text-2xl [&_h1]:font-bold [&_h1]:text-gray-900 [&_h1]:dark:text-white [&_h1]:mb-4 ' +
  '[&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-gray-900 [&_h2]:dark:text-white [&_h2]:mt-8 [&_h2]:mb-3 ' +
  '[&_h3]:text-base [&_h3]:font-semibold [&_h3]:text-gray-800 [&_h3]:dark:text-gray-100 [&_h3]:mt-6 [&_h3]:mb-2 ' +
  '[&_p]:mb-4 [&_p]:leading-relaxed ' +
  '[&_ul]:list-disc [&_ul]:pl-6 [&_ul]:mb-4 [&_ol]:list-decimal [&_ol]:pl-6 [&_ol]:mb-4 ' +
  '[&_li]:mb-1 ' +
  '[&_a]:text-indigo-600 [&_a]:dark:text-indigo-400 [&_a]:underline hover:[&_a]:text-indigo-800 ' +
  '[&_code]:text-sm [&_code]:bg-gray-100 [&_code]:dark:bg-gray-800 [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded ' +
  '[&_pre]:bg-gray-100 [&_pre]:dark:bg-gray-900 [&_pre]:p-4 [&_pre]:rounded-lg [&_pre]:overflow-x-auto [&_pre]:mb-4 ' +
  '[&_table]:w-full [&_table]:text-sm [&_table]:mb-6 [&_th]:text-left [&_th]:font-semibold [&_th]:border-b [&_th]:border-gray-200 [&_th]:dark:border-gray-700 [&_th]:py-2 [&_th]:pr-3 ' +
  '[&_td]:py-2 [&_td]:pr-3 [&_td]:border-b [&_td]:border-gray-100 [&_td]:dark:border-gray-800 ' +
  '[&_hr]:my-8 [&_hr]:border-gray-200 [&_hr]:dark:border-gray-700';

export default function HelpMarkdown({ content }) {
  return (
    <div className={proseClass}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children, ...props }) {
            const resolved = rewriteHref(href);
            if (resolved?.startsWith('/')) {
              return (
                <Link to={resolved} {...props}>
                  {children}
                </Link>
              );
            }
            return (
              <a href={resolved} target="_blank" rel="noopener noreferrer" {...props}>
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
