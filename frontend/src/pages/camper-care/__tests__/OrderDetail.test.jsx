import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import CamperCareOrderDetail from '../OrderDetail';

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
  },
}));

const detailPayload = {
  order: {
    id: 'aaaa1111-aaaa-1111-aaaa-111111111111',
    status: 'new',
    status_label: 'New',
    available_transitions: ['in_progress', 'unable_to_fulfill'],
    is_within_correction_window: false,
    subject: { id: 1, first_name: 'Lila', last_name: 'Park', preferred_name: '' },
    bunk: { id: 11, name: 'Bunk Birch' },
    item: 'Sunscreen',
    item_note: 'SPF 50',
    line_items: [
      {
        id: 'line-1',
        item_id: null,
        item_label: 'Sunscreen',
        quantity: 2,
        note: 'SPF 50',
      },
      {
        id: 'line-2',
        item_id: null,
        item_label: 'Bug spray',
        quantity: 1,
        note: 'Travel size',
      },
    ],
    description: 'For Tuesday hike.',
    submitter: { membership_id: 7, role: 'counselor', name: 'Pat L.' },
    created_at: '2026-07-04T09:00:00Z',
    updated_at: '2026-07-04T09:00:00Z',
    last_transition_at: null,
  },
  activity: [
    {
      id: 'evt-1',
      event_type: 'state_change',
      from_state: null,
      to_state: 'new',
      note: '',
      reason: '',
      actor_name: 'Pat L.',
      created_at: '2026-07-04T09:00:00Z',
    },
  ],
  scope: 'team',
};

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={['/camper-care/orders/aaaa1111-aaaa-1111-aaaa-111111111111']}>
      <Routes>
        <Route path="/camper-care/orders/:orderId" element={<CamperCareOrderDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

describe('CamperCareOrderDetail', () => {
  it('renders order header, description, and activity', async () => {
    getMock.mockResolvedValueOnce({ data: detailPayload });
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId('cc-order-detail')).toBeInTheDocument();
    });
    expect(screen.getByText('2 requested items')).toBeInTheDocument();
    expect(screen.getByTestId('cc-order-line-line-1')).toHaveTextContent('Sunscreen');
    expect(screen.getByTestId('cc-order-line-line-1')).toHaveTextContent('×2');
    expect(screen.getByTestId('cc-order-line-line-2')).toHaveTextContent('Bug spray');
    expect(screen.getByTestId('cc-order-line-line-2')).toHaveTextContent('Travel size');
    expect(screen.getByText('For Tuesday hike.')).toBeInTheDocument();
    expect(screen.getByTestId('activity-evt-1')).toBeInTheDocument();
    expect(screen.getByTestId('cc-order-detail-camper-link')).toHaveAttribute(
      'href',
      '/camper-care/campers/1',
    );
    expect(screen.getByTestId('cc-order-action-in_progress')).toBeInTheDocument();
  });

  it('shows an error when the detail fetch fails', async () => {
    getMock.mockRejectedValueOnce({ response: { data: { detail: 'Order not found.' } } });
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId('cc-order-detail-error')).toHaveTextContent('Order not found.');
    });
  });
});
