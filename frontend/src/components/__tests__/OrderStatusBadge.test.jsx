import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import OrderStatusBadge from '../OrderStatusBadge';

describe('OrderStatusBadge', () => {
  it('renders the canonical label for each known state', () => {
    const states = [
      ['new', 'New'],
      ['in_progress', 'In Progress'],
      ['fulfilled', 'Fulfilled'],
      ['unable_to_fulfill', 'Unable to Fulfill'],
    ];
    for (const [status, label] of states) {
      const { unmount } = render(<OrderStatusBadge status={status} />);
      expect(screen.getByTestId('order-status-badge')).toHaveTextContent(label);
      expect(screen.getByTestId('order-status-badge')).toHaveAttribute(
        'data-status',
        status,
      );
      unmount();
    }
  });

  it('falls back gracefully for unknown statuses', () => {
    render(<OrderStatusBadge status="" />);
    const el = screen.getByTestId('order-status-badge');
    expect(el).toHaveAttribute('data-status', 'unknown');
  });
});
