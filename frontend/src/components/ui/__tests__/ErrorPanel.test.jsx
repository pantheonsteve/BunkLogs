import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import ErrorPanel from '../ErrorPanel';

describe('ErrorPanel (3.31)', () => {
  it('renders children with role="alert"', () => {
    render(<ErrorPanel>Something went wrong.</ErrorPanel>);
    const node = screen.getByRole('alert');
    expect(node).toHaveTextContent('Something went wrong.');
  });

  it('renders the optional title above the body', () => {
    render(
      <ErrorPanel title="Access restricted">
        You do not have permission.
      </ErrorPanel>,
    );
    expect(screen.getByText('Access restricted')).toBeInTheDocument();
    expect(screen.getByText(/you do not have permission/i)).toBeInTheDocument();
  });

  it('applies the standard red-50 / red-200 panel classes', () => {
    render(<ErrorPanel data-testid="ep">err</ErrorPanel>);
    const node = screen.getByTestId('ep');
    expect(node.className).toContain('bg-red-50');
    expect(node.className).toContain('border-red-200');
    expect(node.className).toContain('text-red-700');
  });
});
