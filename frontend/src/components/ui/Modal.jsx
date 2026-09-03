import { useCallback, useEffect, useRef } from 'react';

/**
 * Dialog shell for admin flows: scrim, escape-to-close, backdrop-click,
 * and a header / scrolling body / footer layout.
 *
 * `onClose` is omitted rather than disabled while a request is in
 * flight — pass `dismissible={false}` so an in-progress write can't be
 * abandoned halfway by a stray click or keystroke.
 */

const WIDTHS = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
};

export function ModalFooter({ className = '', children, ...rest }) {
  return (
    <div
      className={`flex items-center gap-2 px-5 py-3 border-t border-gray-100 dark:border-gray-800 ${className}`.trim()}
      {...rest}
    >
      {children}
    </div>
  );
}

export default function Modal({
  title,
  description,
  onClose,
  dismissible = true,
  width = 'md',
  footer,
  headerAction,
  className = '',
  children,
  ...rest
}) {
  const panelRef = useRef(null);

  const requestClose = useCallback(() => {
    if (dismissible && onClose) onClose();
  }, [dismissible, onClose]);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === 'Escape') requestClose();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [requestClose]);

  // Focus the panel so Escape works before the user clicks anything, and
  // so screen readers announce the dialog rather than the page behind it.
  useEffect(() => {
    panelRef.current?.focus();
  }, []);

  const widthCls = WIDTHS[width] || WIDTHS.md;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) requestClose();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === 'string' ? title : undefined}
        tabIndex={-1}
        className={`w-full ${widthCls} max-h-[86vh] flex flex-col rounded-xl bg-white dark:bg-gray-900 shadow-xl outline-none ${className}`.trim()}
        {...rest}
      >
        {(title || description) && (
          <div className="flex items-start gap-3 px-5 py-4 border-b border-gray-100 dark:border-gray-800">
            <div className="min-w-0 flex-1">
              {title && (
                <h2 className="text-base font-semibold text-gray-900 dark:text-white">
                  {title}
                </h2>
              )}
              {description && (
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{description}</p>
              )}
            </div>
            {headerAction && <div className="shrink-0">{headerAction}</div>}
          </div>
        )}
        <div className="px-5 py-4 overflow-y-auto flex-1">{children}</div>
        {footer && <ModalFooter>{footer}</ModalFooter>}
      </div>
    </div>
  );
}
