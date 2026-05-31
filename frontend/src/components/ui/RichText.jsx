/**
 * RichText — render stored rich-text safely as formatted HTML.
 *
 * Several content fields (bunk-log descriptions, `rich_text` reflection
 * answers, counselor elaborations) are authored with the Quill editor and
 * stored as HTML strings like `<p>Great day</p>`. Rendered as plain text
 * those tags show literally, so anywhere that displays one of these fields
 * should use this component instead of `{value}`.
 *
 * Uses `html-react-parser` to turn trusted HTML strings into React elements.
 *
 * When the value has no markup it's rendered as plain text (with line breaks
 * preserved), so it's safe to use for fields that may or may not be HTML.
 *
 * Note: this does not sanitize. Content originates from authenticated staff
 * via the Quill toolbar (formatting only), matching the app's existing trust model.
 */
import parse from 'html-react-parser';

const HTML_TAG_RE = /<[a-z][\s\S]*>/i;

export function hasHtmlMarkup(value) {
  return typeof value === 'string' && HTML_TAG_RE.test(value);
}

export default function RichText({ html, className = '', as: Tag = 'div', fallback = null }) {
  if (html == null || html === '') return fallback;
  const str = String(html);
  if (!hasHtmlMarkup(str)) {
    return <Tag className={`whitespace-pre-line ${className}`.trim()}>{str}</Tag>;
  }
  return <Tag className={className}>{parse(str)}</Tag>;
}
