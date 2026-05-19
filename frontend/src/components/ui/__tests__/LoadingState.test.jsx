import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import LoadingState from '../LoadingState';

describe('LoadingState (3.31)', () => {
  it('renders children text inside a paragraph with status role', () => {
    render(<LoadingState>Loading templates…</LoadingState>);
    const node = screen.getByText('Loading templates…');
    expect(node.tagName).toBe('P');
    expect(node).toHaveAttribute('role', 'status');
    expect(node).toHaveAttribute('aria-live', 'polite');
  });

  it('applies the standard muted-gray + text-sm classes by default', () => {
    render(<LoadingState>Working</LoadingState>);
    const node = screen.getByText('Working');
    expect(node.className).toContain('text-sm');
    expect(node.className).toContain('text-gray-500');
    expect(node.className).toContain('dark:text-gray-400');
  });

  it('drops text-sm when inline is true', () => {
    render(<LoadingState inline>Working</LoadingState>);
    const node = screen.getByText('Working');
    expect(node.className).not.toContain('text-sm');
    expect(node.className).toContain('text-gray-500');
  });

  it('forwards data-testid', () => {
    render(<LoadingState data-testid="ld">x</LoadingState>);
    expect(screen.getByTestId('ld')).toBeInTheDocument();
  });
});
