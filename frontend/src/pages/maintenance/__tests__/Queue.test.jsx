import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import MaintenanceQueue from '../Queue';

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
  },
}));

// useNavigate is used by Queue; stub it
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useNavigate: () => vi.fn() };
});

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

const sampleTickets = [
  {
    id: 'aaaa1111-aaaa-1111-aaaa-111111111111',
    status: 'new',
    urgency: 'urgent',
    location: 'Dining Hall',
    category: 'plumbing',
    description: 'Burst pipe',
    submitter_name: 'Alex Smith',
    age_seconds: 3600,
    has_photos: false,
    acknowledger: null,
    available_transitions: ['in_progress', 'unable_to_fulfill'],
    is_within_correction_window: false,
    created_at: '2026-07-10T08:00:00Z',
    updated_at: '2026-07-10T08:00:00Z',
  },
  {
    id: 'bbbb2222-bbbb-2222-bbbb-222222222222',
    status: 'in_progress',
    urgency: 'normal',
    location: 'Bunk 12',
    category: 'broken_light',
    description: 'Overhead light out',
    submitter_name: 'Jordan Lee',
    age_seconds: 7200,
    has_photos: true,
    acknowledger: { name: 'Mike T.', at: '2026-07-10T09:00:00Z' },
    available_transitions: ['fulfilled', 'unable_to_fulfill'],
    is_within_correction_window: true,
    created_at: '2026-07-10T07:00:00Z',
    updated_at: '2026-07-10T09:00:00Z',
  },
];

const emptyPayload = { tickets: [], counts: { new: 0, in_progress: 0, urgent_open: 0 } };
const samplePayload = { tickets: sampleTickets, counts: { new: 1, in_progress: 1, urgent_open: 1 } };

function renderQueue() {
  return render(
    <MemoryRouter>
      <MaintenanceQueue />
    </MemoryRouter>,
  );
}

describe('MaintenanceQueue', () => {
  it('renders tickets from the API', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    renderQueue();
    await waitFor(() => expect(screen.getByTestId('maint-queue-list')).toBeInTheDocument());
    expect(screen.getByTestId(`ticket-row-${sampleTickets[0].id}`)).toBeInTheDocument();
    expect(screen.getByTestId(`ticket-row-${sampleTickets[1].id}`)).toBeInTheDocument();
  });

  it('shows header counts', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    renderQueue();
    await waitFor(() => screen.getByTestId('maint-queue-counts'));
    expect(screen.getByTestId('maint-queue-counts').textContent).toMatch(/1 new/);
    expect(screen.getByTestId('maint-queue-counts').textContent).toMatch(/1 urgent/);
  });

  it('shows empty state when no tickets', async () => {
    getMock.mockResolvedValueOnce({ data: emptyPayload });
    renderQueue();
    await waitFor(() => screen.getByTestId('maint-queue-empty'));
    expect(screen.getByTestId('maint-queue-empty')).toBeInTheDocument();
  });

  it('status filters reload the queue', async () => {
    getMock.mockResolvedValue({ data: emptyPayload });
    renderQueue();
    await waitFor(() => screen.getByTestId('filter-closed'));
    await userEvent.click(screen.getByTestId('filter-closed'));
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(2));
    const secondCall = getMock.mock.calls[1][1];
    expect(secondCall?.params?.filter).toBe('closed');
  });

  it('bulk bar appears when in-progress tickets selected', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    renderQueue();
    await waitFor(() => screen.getByTestId(`ticket-select-${sampleTickets[1].id}`));
    await userEvent.click(screen.getByTestId(`ticket-select-${sampleTickets[1].id}`));
    expect(screen.getByTestId('maint-queue-bulk-bar')).toBeInTheDocument();
  });

  it('handles API error gracefully', async () => {
    getMock.mockRejectedValueOnce(new Error('Network error'));
    renderQueue();
    await waitFor(() => screen.getByTestId('maint-queue-error'));
    expect(screen.getByTestId('maint-queue-error').textContent).toMatch(/Network error/);
  });

  it('renders a read-only view of the full queue for viewer scope', async () => {
    const viewerTicket = {
      ...sampleTickets[0],
      available_transitions: [],
    };
    getMock.mockResolvedValueOnce({
      data: {
        tickets: [viewerTicket],
        counts: { new: 1, in_progress: 0, urgent_open: 1 },
        scope: 'viewer',
      },
    });
    renderQueue();
    await waitFor(() => screen.getByTestId('maint-queue-readonly-note'));
    // No transition actions and no select checkbox for read-only viewers.
    expect(screen.queryByTestId(`ticket-action-in_progress-${viewerTicket.id}`)).toBeNull();
    expect(screen.queryByTestId(`ticket-select-${viewerTicket.id}`)).toBeNull();
  });
});
