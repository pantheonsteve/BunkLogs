import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MyReflectionsPage from './MyReflectionsPage';

const getMock = vi.fn();

vi.mock('../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

vi.mock('../partials/Header', () => ({ default: () => null }));
vi.mock('../partials/Sidebar', () => ({ default: () => null }));

function renderPage() {
  return render(
    <MemoryRouter>
      <MyReflectionsPage />
    </MemoryRouter>,
  );
}

const SUMMARY = {
  template: { name: 'Counselor weekly', cadence: 'weekly' },
  streak: 2,
  total_completed: 5,
  current_period: null,
  history: [
    {
      period_start: '2026-06-08',
      period_end: '2026-06-14',
      submitted: true,
      submitted_at: '2026-06-12T10:00:00Z',
      reflection_id: 91,
      team_visibility: 'supervisors_only',
    },
    {
      period_start: '2026-06-01',
      period_end: '2026-06-07',
      submitted: true,
      submitted_at: '2026-06-05T10:00:00Z',
      reflection_id: 92,
      team_visibility: 'team',
    },
    {
      period_start: '2026-05-25',
      period_end: '2026-05-31',
      submitted: false,
      submitted_at: null,
      reflection_id: null,
      team_visibility: null,
    },
  ],
};

describe('MyReflectionsPage', () => {
  beforeEach(() => {
    getMock.mockReset();
    getMock.mockResolvedValue({ data: SUMMARY });
  });

  it('shows the privacy chip only on history rows filed privately', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Counselor weekly · weekly')).toBeInTheDocument());

    const items = screen.getAllByRole('listitem');
    // First item (Jun 8) is private; second (Jun 1) is team; third is unsubmitted.
    expect(within(items[0]).getByTestId('privacy-chip')).toBeInTheDocument();
    expect(within(items[1]).queryByTestId('privacy-chip')).toBeNull();
    expect(within(items[2]).queryByTestId('privacy-chip')).toBeNull();
  });
});
