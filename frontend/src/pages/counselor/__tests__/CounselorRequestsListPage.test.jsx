import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import CounselorRequestsListPage from '../CounselorRequestsListPage';

const getMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

const samplePayload = {
  requests: [
    {
      type: 'maintenance',
      id: 'mt-1',
      status: 'new',
      status_label: 'New',
      location: 'Bunk Pine',
      category: 'leak',
      category_label: 'Leak',
      urgency: 'urgent',
      urgency_label: 'Urgent',
      description: 'under sink',
      photo_count: 2,
      submitter: { is_self: true, name: null },
      submitted_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    },
    {
      type: 'camper_care',
      id: 'order-1',
      status: 'in_progress',
      status_label: 'In progress',
      subject: { id: 100, name: 'Avi L' },
      item: 'Toothpaste',
      item_note: 'mint',
      submitter: { is_self: false, name: 'Casey Q' },
      submitted_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    },
    {
      type: 'camper_care',
      id: 'order-2',
      status: 'new',
      status_label: 'New',
      subject: null,
      item: 'Bug spray',
      item_note: '',
      submitter: { is_self: true, name: null },
      submitted_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    },
  ],
};

function renderPage(initialEntry = '/counselor/requests') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <CounselorRequestsListPage />
    </MemoryRouter>,
  );
}

describe('CounselorRequestsListPage', () => {
  beforeEach(() => {
    getMock.mockReset();
  });

  it('fetches with status=open by default', async () => {
    getMock.mockResolvedValue({ data: samplePayload });
    renderPage();
    await waitFor(() => expect(getMock).toHaveBeenCalled());
    expect(getMock.mock.calls[0]).toEqual([
      '/api/v1/counselor/requests/',
      { params: { status: 'open' } },
    ]);
  });

  it('renders each request with type, status, and submitter info', async () => {
    getMock.mockResolvedValue({ data: samplePayload });
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId('request-row-maintenance-mt-1')).toBeInTheDocument(),
    );

    const mt = screen.getByTestId('request-row-maintenance-mt-1');
    expect(mt).toHaveAttribute('data-status', 'new');
    expect(mt).toHaveAttribute('data-type', 'maintenance');
    expect(mt.querySelector('[data-testid="request-urgency-badge"]')).toBeTruthy();
    expect(mt).toHaveTextContent('Leak');
    expect(mt).toHaveTextContent('Sent by you');
    expect(mt).toHaveTextContent('2 photos');

    const cc1 = screen.getByTestId('request-row-camper_care-order-1');
    expect(cc1).toHaveTextContent('Toothpaste');
    expect(cc1).toHaveTextContent('For Avi L');
    expect(cc1).toHaveTextContent('Casey Q');
    expect(cc1.querySelector('[data-testid="request-status-badge"]')).toHaveAttribute(
      'data-status',
      'in_progress',
    );

    const cc2 = screen.getByTestId('request-row-camper_care-order-2');
    expect(cc2).toHaveTextContent('Bunk-wide request');
  });

  it('flips to status=all when the All filter is clicked', async () => {
    const user = userEvent.setup();
    getMock.mockResolvedValueOnce({ data: samplePayload });
    getMock.mockResolvedValueOnce({ data: { requests: [] } });
    renderPage();
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByTestId('requests-filter-all'));
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(2));
    expect(getMock.mock.calls[1][1].params.status).toBe('all');
  });

  it('seeds the filter from the URL ?status=all', async () => {
    getMock.mockResolvedValue({ data: samplePayload });
    renderPage('/counselor/requests?status=all');
    await waitFor(() => expect(getMock).toHaveBeenCalled());
    expect(getMock.mock.calls[0][1].params.status).toBe('all');
    expect(screen.getByTestId('requests-filter-all')).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('renders empty-state copy when no rows', async () => {
    getMock.mockResolvedValue({ data: { requests: [] } });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('requests-empty')).toBeInTheDocument());
    expect(screen.getByTestId('requests-empty')).toHaveTextContent(/No open requests/i);
  });

  it('renders an error banner when fetch fails', async () => {
    getMock.mockRejectedValue({ response: { status: 500, data: { detail: 'boom' } } });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('requests-error')).toBeInTheDocument());
    expect(screen.getByTestId('requests-error')).toHaveTextContent('boom');
  });

  it('always exposes both new-request CTAs', async () => {
    getMock.mockResolvedValue({ data: samplePayload });
    renderPage();
    await waitFor(() => expect(getMock).toHaveBeenCalled());
    expect(screen.getByTestId('requests-new-camper-care')).toHaveAttribute(
      'href',
      '/counselor/requests/camper-care/new',
    );
    expect(screen.getByTestId('requests-new-maintenance')).toHaveAttribute(
      'href',
      '/counselor/requests/maintenance/new',
    );
  });
});
