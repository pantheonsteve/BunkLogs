import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import OrderActivityList from '../OrderActivityList';

const baseEvent = {
  id: 'e1',
  event_type: 'state_change',
  from_state: 'new',
  to_state: 'in_progress',
  note: '',
  reason: '',
  actor_name: 'Riley R.',
  correction_of: null,
  created_at: '2026-06-01T12:00:00Z',
};

describe('OrderActivityList', () => {
  it('renders empty placeholder when no events', () => {
    render(<OrderActivityList events={[]} />);
    expect(screen.getByTestId('order-activity-empty')).toBeInTheDocument();
  });

  it('renders a state change event with arrow notation', () => {
    render(<OrderActivityList events={[baseEvent]} />);
    const item = screen.getByTestId('order-activity-event');
    expect(item).toHaveTextContent('New → In Progress');
    expect(item).toHaveTextContent('Riley R.');
  });

  it('renders correction events distinctly', () => {
    render(
      <OrderActivityList
        events={[
          {
            ...baseEvent,
            id: 'e2',
            event_type: 'correction',
            from_state: 'in_progress',
            to_state: 'new',
          },
        ]}
      />,
    );
    const item = screen.getByTestId('order-activity-event');
    expect(item).toHaveAttribute('data-event-type', 'correction');
    expect(item).toHaveTextContent('Correction: In Progress → New');
  });

  it('shows reason and note bodies when present', () => {
    render(
      <OrderActivityList
        events={[
          {
            ...baseEvent,
            id: 'e3',
            from_state: 'in_progress',
            to_state: 'unable_to_fulfill',
            reason: 'Item is out of stock through end of session.',
            note: 'Counselor notified.',
          },
        ]}
      />,
    );
    expect(
      screen.getByText(/Item is out of stock through end of session\./),
    ).toBeInTheDocument();
    expect(screen.getByText(/Counselor notified\./)).toBeInTheDocument();
  });
});
