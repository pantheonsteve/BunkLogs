import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import Button from '../Button';

describe('Button (3.31)', () => {
  it('renders children inside a <button>', () => {
    render(<Button>Click me</Button>);
    const btn = screen.getByRole('button', { name: /click me/i });
    expect(btn).toBeInTheDocument();
    expect(btn.tagName).toBe('BUTTON');
  });

  it('defaults to type="button" so it does not submit ambient forms', () => {
    render(<Button>Safe</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button');
  });

  it('renders the primary variant by default with the standard blue class', () => {
    render(<Button>Primary</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('bg-blue-600');
    expect(btn.className).toContain('text-white');
    expect(btn.className).toContain('hover:bg-blue-700');
  });

  it('renders the secondary variant with the gray outline', () => {
    render(<Button variant="secondary">Cancel</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('border-gray-300');
    expect(btn.className).toContain('bg-white');
  });

  it('renders the danger variant with red text', () => {
    render(<Button variant="danger">Delete</Button>);
    const btn = screen.getByRole('button');
    expect(btn.className).toContain('text-red-600');
  });

  it('applies the small size when size="sm"', () => {
    render(<Button size="sm">Sm</Button>);
    expect(screen.getByRole('button').className).toContain('px-3');
    expect(screen.getByRole('button').className).toContain('py-1.5');
  });

  it('forwards onClick, but does not fire when disabled', async () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Disabled
      </Button>,
    );
    await userEvent.click(screen.getByRole('button'));
    expect(onClick).not.toHaveBeenCalled();
  });

  it('forwards data-testid and other html attributes', () => {
    render(<Button data-testid="my-btn">X</Button>);
    expect(screen.getByTestId('my-btn')).toBeInTheDocument();
  });
});
