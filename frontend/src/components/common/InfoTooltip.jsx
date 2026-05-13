import { useEffect, useRef, useState } from 'react';

/**
 * Small inline (i) info icon that opens a tooltip popover on hover, focus,
 * or click. Used to surface rubric / scoring guidance next to form labels.
 *
 * Originally extracted from BunkLogForm so the same affordance can be
 * reused on reflection template widgets that mirror the Bunk Log UI.
 *
 * @param {object} props
 * @param {string} props.text - Tooltip body text. Newlines are preserved.
 */
export default function InfoTooltip({ text }) {
  const [visible, setVisible] = useState(false);
  const tooltipRef = useRef(null);

  useEffect(() => {
    if (!visible) return undefined;
    const handleClick = (e) => {
      if (tooltipRef.current && !tooltipRef.current.contains(e.target)) {
        setVisible(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [visible]);

  if (!text) return null;

  return (
    <span className="relative inline-block align-middle ml-1">
      <button
        type="button"
        aria-label="Info"
        tabIndex={0}
        className="text-blue-500 hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 rounded-full p-0.5"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        onClick={() => setVisible((v) => !v)}
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path d="M18 10A8 8 0 11 2 10a8 8 0 0116 0zM9 8a1 1 0 112 0v4a1 1 0 11-2 0V8zm1-4a1.5 1.5 0 100 3 1.5 1.5 0 000-3z" />
        </svg>
      </button>
      {visible && (
        <div
          ref={tooltipRef}
          className="absolute z-20 left-1/2 -translate-x-1/2 mt-2 w-56 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded shadow-lg p-2 text-xs text-gray-800 dark:text-gray-100 whitespace-pre-line"
          style={{ minWidth: '180px' }}
        >
          {text}
        </div>
      )}
    </span>
  );
}
