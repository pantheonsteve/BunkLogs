import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import CamperCareOrders from '../Orders';

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

const samplePayload = {
  new: [
    {
      id: 'aaaa1111-aaaa-1111-aaaa-111111111111',
      status: 'new',
      available_transitions: ['in_progress', 'unable_to_fulfill'],
      is_within_correction_window: false,
      subject: { id: 1, first_name: 'Lila', last_name: 'Park', preferred_name: '' },
      bunk: { id: 11, name: 'Bunk Birch' },
      item: 'Sunscreen',
      item_note: 'SPF 50',
      description: 'For Tuesday hike.',
      submitter: { membership_id: 7, role: 'counselor', name: 'Pat L.' },
      created_at: '2026-07-04T09:00:00Z',
      updated_at: '2026-07-04T09:00:00Z',
      age_seconds: 600,
      last_event_note: '',
    },
  ],
  in_progress: [
    {
      id: 'bbbb2222-bbbb-2222-bbbb-222222222222',
      status: 'in_progress',
      available_transitions: ['fulfilled', 'unable_to_fulfill'],
      is_within_correction_window: true,
      subject: { id: 2, first_name: 'Jordan', last_name: 'Tate', preferred_name: 'Jo' },
      bunk: { id: 12, name: 'Bunk Pine' },
      item: 'Inhaler',
      item_note: '',
      description: '',
      submitter: { membership_id: 8, role: 'counselor', name: 'Sam R.' },
      created_at: '2026-07-04T08:00:00Z',
      updated_at: '2026-07-04T10:00:00Z',
      age_seconds: 7200,
      last_event_note: '',
    },
    {
      id: 'cccc3333-cccc-3333-cccc-333333333333',
      status: 'in_progress',
      available_transitions: ['fulfilled', 'unable_to_fulfill'],
      is_within_correction_window: false,
      subject: { id: 3, first_name: 'Avi', last_name: 'Klein', preferred_name: '' },
      bunk: { id: 11, name: 'Bunk Birch' },
      item: 'Sunscreen',
      item_note: '',
      description: '',
      submitter: { membership_id: 9, role: 'counselor', name: 'Mira C.' },
      created_at: '2026-07-04T08:30:00Z',
      updated_at: '2026-07-04T10:30:00Z',
      age_seconds: 7800,
      last_event_note: '',
    },
  ],
  resolved: [],
  counts: { new: 1, in_progress: 2, resolved: 0 },
  scope: 'team',
};

describe('CamperCareOrders', () => {
  it('renders the three workspace sections with counts', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(
      <MemoryRouter>
        <CamperCareOrders />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('cc-orders')).toBeInTheDocument();
    });
    expect(screen.getByTestId('cc-orders-new-count')).toHaveTextContent('1');
    expect(screen.getByTestId('order-row-aaaa1111-aaaa-1111-aaaa-111111111111')).toBeInTheDocument();
    expect(screen.getByTestId('order-row-bbbb2222-bbbb-2222-bbbb-222222222222')).toBeInTheDocument();
    expect(screen.getByTestId('order-row-cccc3333-cccc-3333-cccc-333333333333')).toBeInTheDocument();
  });

  it('shows bunk prominently with submitter name secondary', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(
      <MemoryRouter>
        <CamperCareOrders />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('order-bunk-aaaa1111-aaaa-1111-aaaa-111111111111')).toBeInTheDocument();
    });
    const row = screen.getByTestId('order-row-aaaa1111-aaaa-1111-aaaa-111111111111');
    expect(row).toHaveTextContent('Bunk Birch');
    expect(row).toHaveTextContent('For Lila Park');
    expect(row).toHaveTextContent('from Pat L.');
  });

  it('bulk-fulfills selected In Progress orders', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    postMock.mockResolvedValueOnce({
      data: { transitioned: [], activity_by_id: {}, failed: [], missing: [] },
    });
    getMock.mockResolvedValueOnce({
      data: { ...samplePayload, in_progress: [], counts: { new: 1, in_progress: 0, resolved: 2 } },
    });

    render(
      <MemoryRouter>
        <CamperCareOrders />
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByTestId('cc-orders-in-progress')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('order-select-bbbb2222-bbbb-2222-bbbb-222222222222'));
    await user.click(screen.getByTestId('order-select-cccc3333-cccc-3333-cccc-333333333333'));
    expect(screen.getByTestId('cc-orders-bulk-bar')).toHaveTextContent('2 selected');

    await user.type(screen.getByTestId('cc-orders-bulk-note'), 'Distributed at line-up.');
    await user.click(screen.getByTestId('cc-orders-bulk-submit'));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalled();
    });
    const [url, payload] = postMock.mock.calls[0];
    expect(url).toBe('/api/v1/camper-care/orders/bulk-transition/');
    expect(payload.to_state).toBe('fulfilled');
    expect(payload.ids).toEqual([
      'bbbb2222-bbbb-2222-bbbb-222222222222',
      'cccc3333-cccc-3333-cccc-333333333333',
    ]);
    expect(payload.note).toBe('Distributed at line-up.');
  });

  it('switches filter and refetches with my_caseload', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    getMock.mockResolvedValueOnce({ data: { ...samplePayload, new: [], counts: { new: 0, in_progress: 2, resolved: 0 } } });

    render(
      <MemoryRouter>
        <CamperCareOrders />
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByTestId('cc-orders-filter')).toBeInTheDocument();
    });
    await user.selectOptions(screen.getByTestId('cc-orders-filter-select'), 'my_caseload');
    await waitFor(() => {
      const calls = getMock.mock.calls;
      const last = calls[calls.length - 1];
      expect(last[0]).toBe('/api/v1/camper-care/orders/');
      expect(last[1]?.params?.filter).toBe('my_caseload');
    });
  });
});
