import { useEffect, useRef, useState } from 'react';
import { MoreHorizontal } from 'lucide-react';

/**
 * The "⋯" menu that destructive and rare actions live in.
 *
 * Keeping Archive, Delete and Deactivate in here (rather than as loose
 * links beside routine buttons) is what stops five different treatments
 * for destructive actions reappearing across admin screens.
 *
 * `OverflowMenuItem` with `danger` renders the red treatment; the menu
 * closes on outside click, Escape, and after any item fires.
 */

export function OverflowMenuItem({ danger = false, className = '', children, ...rest }) {
  return (
    <button
      type="button"
      role="menuitem"
      className={`block w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent ${
        danger
          ? 'text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30'
          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
      } ${className}`.trim()}
      {...rest}
    >
      {children}
    </button>
  );
}

export function OverflowMenuSeparator() {
  return <div className="my-1 h-px bg-gray-100 dark:bg-gray-800" />;
}

export default function OverflowMenu({
  label = 'More actions',
  triggerTestId = 'overflow-menu-trigger',
  size = 'md',
  className = '',
  children,
  ...rest
}) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDocClick = (e) => {
      if (!wrapRef.current?.contains(e.target)) setOpen(false);
    };
    const onKeyDown = (e) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  return (
    <div ref={wrapRef} className={`relative inline-block ${className}`.trim()} {...rest}>
      <button
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        data-testid={triggerTestId}
        className={`inline-flex items-center justify-center rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${
          size === 'sm' ? 'w-7 h-7' : 'w-9 h-9'
        }`}
      >
        <MoreHorizontal size={size === 'sm' ? 14 : 16} aria-hidden="true" />
      </button>
      {open && (
        <div
          role="menu"
          data-testid="overflow-menu"
          onClick={() => setOpen(false)}
          className="absolute right-0 top-full mt-1.5 min-w-[15rem] p-1 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-lg z-40"
        >
          {children}
        </div>
      )}
    </div>
  );
}
