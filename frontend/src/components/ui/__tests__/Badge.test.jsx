import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import Badge from '../Badge';

describe('Badge', () => {
  it('renders its children', () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('defaults to the neutral tone and the sm size', () => {
    render(<Badge data-testid="b">3</Badge>);
    const node = screen.getByTestId('b');
    expect(node.className).toContain('bg-gray-100');
    expect(node.className).toContain('text-xs');
    expect(node.className).toContain('px-2');
  });

  it('maps tone to a colour treatment', () => {
    render(<Badge tone="danger" data-testid="b">Urgent</Badge>);
    expect(screen.getByTestId('b').className).toContain('bg-red-100');
  });

  it('lets colors replace the tone classes outright', () => {
    render(
      <Badge tone="danger" colors="bg-purple-100 text-purple-800" data-testid="b">
        Care
      </Badge>,
    );
    const { className } = screen.getByTestId('b');
    expect(className).toContain('bg-purple-100');
    expect(className).not.toContain('bg-red-100');
  });

  // The gap between a pill and the word before it is the whole reason this
  // component owns spacing; a call site setting its own margin is the bug.
  it('adds left margin only when inline is set', () => {
    const { rerender } = render(<Badge data-testid="b">3</Badge>);
    expect(screen.getByTestId('b').className).not.toContain('ml-');

    rerender(<Badge inline data-testid="b">3</Badge>);
    expect(screen.getByTestId('b').className).toContain('ml-2.5');
  });

  it('renders a dot when asked', () => {
    const { container } = render(<Badge dot>Active</Badge>);
    expect(container.querySelector('span span')).toHaveClass('rounded-full');
  });

  it('appends className without dropping the base classes', () => {
    render(<Badge className="font-semibold" data-testid="b">9</Badge>);
    const { className } = screen.getByTestId('b');
    expect(className).toContain('font-semibold');
    expect(className).toContain('rounded-full');
  });

  // Call sites override weight and padding; those must win outright rather
  // than depending on which class Tailwind happens to emit last.
  it('lets className replace conflicting base utilities', () => {
    render(<Badge className="font-semibold py-1" data-testid="b">9</Badge>);
    const { className } = screen.getByTestId('b');
    expect(className).not.toContain('font-medium');
    expect(className).not.toContain('py-0.5');
  });
});
