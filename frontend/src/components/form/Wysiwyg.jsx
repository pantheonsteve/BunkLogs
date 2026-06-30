import { forwardRef, lazy, Suspense } from 'react';

// Quill (~200 KB gzipped chunk) is the single largest editor dependency. It
// lives in WysiwygEditor and is loaded on demand the first time a rich-text
// field actually renders, rather than being pulled into every route that
// imports this widget. React.lazy forwards refs to the underlying forwardRef
// editor, so the imperative API (getQuill/setContent) keeps working.
const WysiwygEditor = lazy(() => import('./WysiwygEditor'));

function EditorFallback({ readOnly }) {
  return (
    <div
      style={{ minHeight: readOnly ? '120px' : '300px' }}
      className="flex items-center justify-center bg-gray-50 dark:bg-gray-900 text-sm text-gray-400"
      aria-busy="true"
    >
      Loading editor…
    </div>
  );
}

const Wysiwyg = forwardRef((props, ref) => (
  <Suspense fallback={<EditorFallback readOnly={props.readOnly} />}>
    <WysiwygEditor {...props} ref={ref} />
  </Suspense>
));

Wysiwyg.displayName = 'Wysiwyg';

export default Wysiwyg;
