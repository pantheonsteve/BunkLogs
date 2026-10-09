import React, { forwardRef } from 'react';
import { twMerge } from 'tailwind-merge';

/**
 * Canonical button primitive.
 *
 *   variant: 'primary'   — filled brand violet (the "New X" / "Save" CTA)
 *            'secondary' — white with a line border (Cancel, back-out)
 *            'danger'    — red text on hover (Delete actions)
 *
 *   size:    'sm' — table-row and toolbar usage
 *            'md' — page-level actions, 40px tall
 *            'lg' — 52px phone CTA
 *
 * Dark brand is violet-400, which fails 4.5:1 under white text, so the
 * primary label flips to near-black in dark mode.
 */

const VARIANT_CLASSES = {
  primary:
    'bg-brand text-white dark:text-gray-950 font-semibold rounded-lg hover:bg-brand-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors',
  secondary:
    'bg-white dark:bg-gray-900 border border-line text-ink font-semibold rounded-lg hover:bg-line-soft disabled:opacity-50 disabled:cursor-not-allowed transition-colors',
  danger:
    'text-red-600 dark:text-red-400 font-medium rounded-lg hover:bg-red-50 dark:hover:bg-red-950/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors',
};

const SIZE_CLASSES = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'min-h-10 px-4 py-2 text-sm',
  lg: 'min-h-[52px] px-5 py-3 text-base rounded-xl',
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
      className={twMerge('inline-flex items-center justify-center gap-2', variantCls, sizeCls, className)}
      {...rest}
    >
      {children}
    </button>
  );
});

export default Button;
