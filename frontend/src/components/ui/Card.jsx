/**
 * Panel primitive — the white bordered box most content sits in.
 *
 * `Card` is the shell, `CardHeader` the title strip with an optional
 * right-hand action slot, `CardBody` the padded content area. `as` swaps
 * the shell element (e.g. `section`) without changing its styling.
 */

import { twMerge } from 'tailwind-merge';

export function CardHeader({ title, subtitle, action, className = '', children, ...rest }) {
  return (
    <div
      className={`flex items-start gap-3 px-[18px] py-4 border-b border-line-soft ${className}`.trim()}
      {...rest}
    >
      <div className="min-w-0 flex-1">
        {title && (
          <h2 className="text-base font-bold text-ink truncate">
            {title}
          </h2>
        )}
        {subtitle && (
          <p className="text-[13px] text-muted mt-0.5">{subtitle}</p>
        )}
        {children}
      </div>
      {action && <div className="shrink-0 flex items-center gap-2">{action}</div>}
    </div>
  );
}

export function CardBody({ className = '', children, ...rest }) {
  return (
    <div className={`p-4 ${className}`.trim()} {...rest}>
      {children}
    </div>
  );
}

export default function Card({ as: Component = 'div', className = '', children, ...rest }) {
  return (
    <Component
      className={twMerge('bg-white dark:bg-gray-900 border border-line rounded-[14px]', className)}
      {...rest}
    >
      {children}
    </Component>
  );
}
