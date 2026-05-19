import React, { forwardRef } from 'react';

/**
 * Canonical button primitive for admin surfaces.
 *
 * Variants codify the most common tailwind blobs we were repeating
 * across the new admin pages -- they don't introduce new visuals.
 *
 *   variant: 'primary'   — filled blue (the "New X" / "Save" CTA)
 *            'secondary' — gray outline / ghost (Cancel, back-out)
 *            'danger'    — red text on hover (Delete actions)
 *
 *   size:    'sm' — px-3 py-1.5 text-xs/sm (table-row and toolbar usage)
 *            'md' — px-4 py-2 text-sm (page-level actions)
 *
 * Renders a regular <button> with className composed from variant +
 * size + caller-provided className.
 */

const VARIANT_CLASSES = {
  primary:
    'bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors',
  secondary:
    'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors',
  danger:
    'text-red-600 dark:text-red-400 font-medium rounded-lg hover:bg-red-50 dark:hover:bg-red-950/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors',
};

const SIZE_CLASSES = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
};

const Button = forwardRef(function Button(
  {
    variant = 'primary',
    size = 'md',
    type = 'button',
    className = '',
    children,
    ...rest
  },
  ref,
) {
  const variantCls = VARIANT_CLASSES[variant] || VARIANT_CLASSES.primary;
  const sizeCls = SIZE_CLASSES[size] || SIZE_CLASSES.md;
  return (
    <button
      ref={ref}
      type={type}
      className={`inline-flex items-center justify-center gap-2 ${variantCls} ${sizeCls} ${className}`.trim()}
      {...rest}
    >
      {children}
    </button>
  );
});

export default Button;
