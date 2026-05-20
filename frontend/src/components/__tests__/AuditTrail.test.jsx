import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

vi.mock('../../api', () => ({
  default: { get: vi.fn() },
}));

import api from '../../api';
import AuditTrail from '../AuditTrail';

beforeEach(() => {
  api.get.mockReset();
});

const SAMPLE = [
  {
    id: 'evt-1',
    event_type: 'created',
    created_at: '2026-05-19T12:00:00Z',
    content_type: 'order',
    content_id: 'order-1',
    before_state: {},
    after_state: { status: 'new' },
    reason_note: '',
    is_admin_override: false,
    metadata: {},
  },
  {
    id: 'evt-2',
    event_type: 'state_changed',
    created_at: '2026-05-19T12:05:00Z',
    content_type: 'order',
    content_id: 'order-1',
    before_state: { status: 'new' },
    after_state: { status: 'in_progress' },
    reason_note: 'kickoff',
    is_admin_override: false,
    metadata: {},
  },
];

describe('AuditTrail', () => {
  it('renders nothing for non-admin viewers', () => {
    const { container } = render(
      <AuditTrail
        user={{ is_staff: false, is_superuser: false }}
        isAdmin={false}
        contentType="order"
        contentId="order-1"
      />,
    );
    expect(container.firstChild).toBeNull();
    expect(api.get).not.toHaveBeenCalled();
  });

  it('fetches and renders events for an org admin', async () => {
    api.get.mockResolvedValue({ data: SAMPLE });
    render(
      <AuditTrail
        user={{ is_staff: false, is_superuser: false }}
        isAdmin
        contentType="order"
        contentId="order-1"
      />,
    );
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    const list = await screen.findByTestId('audit-trail');
    expect(list).toHaveAttribute('data-content-type', 'order');
    expect(list).toHaveAttribute('data-content-id', 'order-1');
    const items = screen.getAllByTestId('audit-event');
    expect(items).toHaveLength(2);
    expect(items[1]).toHaveAttribute('data-event-type', 'state_changed');
    expect(items[1]).toHaveTextContent('new → in_progress');
  });

  it('renders for Super Admin users without an isAdmin prop', async () => {
    api.get.mockResolvedValue({ data: [] });
    render(
      <AuditTrail
        user={{ is_staff: false, is_superuser: true }}
        contentType="order"
        contentId="order-1"
      />,
    );
    expect(await screen.findByTestId('audit-trail-empty')).toBeInTheDocument();
  });

  it('renders an empty-state message when no events come back', async () => {
    api.get.mockResolvedValue({ data: [] });
    render(
      <AuditTrail isAdmin contentType="order" contentId="order-1" />,
    );
    expect(await screen.findByTestId('audit-trail-empty')).toBeInTheDocument();
  });

  it('renders an error message if the fetch fails', async () => {
    api.get.mockRejectedValue(new Error('boom'));
    render(
      <AuditTrail isAdmin contentType="order" contentId="order-1" />,
    );
    expect(await screen.findByTestId('audit-trail-error')).toBeInTheDocument();
  });
});
