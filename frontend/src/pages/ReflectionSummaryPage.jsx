import { Link, useLocation } from 'react-router-dom';

function promptText(field) {
  if (!field.prompts || typeof field.prompts !== 'object') return '';
  const v = Object.values(field.prompts)[0];
  return typeof v === 'string' ? v : '';
}

function categoryLabel(cat) {
  if (!cat.labels || typeof cat.labels !== 'object') return cat.key || '';
  const v = Object.values(cat.labels)[0];
  return typeof v === 'string' ? v : cat.key || '';
}

function formatAnswer(field, value) {
  if (value === undefined || value === null) return '—';
  if (field.type === 'rating_group' && value && typeof value === 'object') {
    return Object.entries(value)
      .map(([k, v]) => {
        const cat = (field.categories || []).find((c) => c.key === k);
        const label = cat ? categoryLabel(cat) : k;
        return `${label}: ${v}`;
      })
      .join('; ');
  }
  if (Array.isArray(value)) return value.join(', ') || '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export default function ReflectionSummaryPage() {
  const location = useLocation();
  const data = location.state;

  if (!data?.reflectionId) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 px-4 py-8">
        <div className="max-w-lg mx-auto rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
          <p className="text-gray-700 dark:text-gray-300 mb-4">
            No reflection summary to show. Submit a reflection from the form first.
          </p>
          <Link
            to="/reflect"
            className="text-blue-600 dark:text-blue-400 underline font-medium"
          >
            Open reflection form
          </Link>
        </div>
      </div>
    );
  }

  const { reflectionId, templateName, periodStart, periodEnd, language, schema, answers } = data;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 px-4 py-8">
      <div className="max-w-xl mx-auto rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 shadow-sm">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          Reflection submitted
        </h1>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
          Reference #{reflectionId} · {templateName} · {periodStart} → {periodEnd} · {language}
        </p>
        <ul className="space-y-4">
          {(schema?.fields || []).map((field) => (
            <li key={field.key} className="border-b border-gray-100 dark:border-gray-700 pb-3 last:border-0">
              <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                {field.type === 'rating_group' ? 'Ratings' : promptText(field)}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 whitespace-pre-wrap">
                {formatAnswer(field, answers[field.key])}
              </p>
            </li>
          ))}
        </ul>
        <Link
          to="/reflect"
          className="inline-block mt-8 text-blue-600 dark:text-blue-400 underline font-medium"
        >
          Submit another
        </Link>
      </div>
    </div>
  );
}
