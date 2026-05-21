import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import CounselorSelfReflectionHistoryPage from '../CounselorSelfReflectionHistoryPage';

const getMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

function payload(overrides = {}) {
  return {
    count: 60,
    page: 1,
    page_size: 14,
    next: 2,
    previous: null,
    results: [
      {
        date: '2026-07-04',
        submitted: true,
        is_day_off: false,
        reflection_id: 700,
        submitted_at: '2026-07-04T20:00:00Z',
        preview: 'A productive day with the bunk.',
        editable: true,
      },
      {
        date: '2026-07-03',
        submitted: true,
        is_day_off: true,
        reflection_id: 699,
        submitted_at: '2026-07-03T10:00:00Z',
        preview: '',
        editable: false,
      },
      {
        date: '2026-07-02',
        submitted: false,
        is_day_off: false,
        reflection_id: null,
        submitted_at: null,
        preview: '',
        editable: false,
      },
    ],
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/counselor/self-reflection/history']}>
      <CounselorSelfReflectionHistoryPage />
    </MemoryRouter>,
  );
}

describe('CounselorSelfReflectionHistoryPage', () => {
  beforeEach(() => {
    getMock.mockReset();
  });

  it('renders submitted, day-off, and missing rows distinctly', async () => {
    getMock.mockResolvedValue({ data: payload() });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('history-row-2026-07-04')).toBeInTheDocument());

    const submitted = screen.getByTestId('history-row-2026-07-04');
    expect(submitted).toHaveAttribute('data-submitted', 'true');
    expect(submitted).toHaveAttribute('data-day-off', 'false');
    expect(screen.getByTestId('history-row-2026-07-04-preview')).toHaveTextContent(
      'A productive day',
    );

    const dayOff = screen.getByTestId('history-row-2026-07-03');
    expect(dayOff).toHaveAttribute('data-day-off', 'true');
    expect(dayOff.querySelector('[data-testid="row-badge-day-off"]')).toBeTruthy();

    const missing = screen.getByTestId('history-row-2026-07-02');
    expect(missing).toHaveAttribute('data-submitted', 'false');
    expect(missing.querySelector('[data-testid="row-badge-missing"]')).toBeTruthy();
  });

  it('points today (editable) at the edit URL and past rows at the read-only viewer', async () => {
    getMock.mockResolvedValue({ data: payload() });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('history-row-2026-07-04-link')).toBeInTheDocument());

    expect(screen.getByTestId('history-row-2026-07-04-link')).toHaveAttribute(
      'href',
      '/counselor/self-reflection/700/edit',
    );
    expect(screen.getByTestId('history-row-2026-07-04-link')).toHaveTextContent('Edit');

    expect(screen.getByTestId('history-row-2026-07-03-link')).toHaveAttribute(
      'href',
      '/reflections/699',
    );
    expect(screen.getByTestId('history-row-2026-07-03-link')).toHaveTextContent('View');

    // Missing rows shouldn't render any link.
    expect(screen.queryByTestId('history-row-2026-07-02-link')).toBeNull();
  });

  it('paginates forward and backward via the API', async () => {
    const user = userEvent.setup();
    getMock.mockResolvedValueOnce({ data: payload() });
    getMock.mockResolvedValueOnce({
      data: payload({ page: 2, previous: 1, next: 3, results: [] }),
    });
    getMock.mockResolvedValueOnce({ data: payload() });
    renderPage();
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByTestId('history-next'));
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(2));
    expect(getMock.mock.calls[1][1].params).toEqual({ page: 2 });

    await user.click(screen.getByTestId('history-prev'));
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(3));
    expect(getMock.mock.calls[2][1].params).toEqual({ page: 1 });
  });

  it('disables prev on page 1 and next on the last page', async () => {
    getMock.mockResolvedValue({
      data: payload({ next: null, previous: null }),
    });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('history-prev')).toBeInTheDocument());
    expect(screen.getByTestId('history-prev')).toBeDisabled();
    expect(screen.getByTestId('history-next')).toBeDisabled();
  });

  it('renders the empty state when results are empty', async () => {
    getMock.mockResolvedValue({
      data: { count: 0, page: 1, page_size: 14, next: null, previous: null, results: [] },
    });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('history-empty')).toBeInTheDocument());
  });

  it('shows an error banner on API failure', async () => {
    getMock.mockRejectedValue({ response: { status: 500, data: { detail: 'boom' } } });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('history-error')).toBeInTheDocument());
    expect(screen.getByTestId('history-error')).toHaveTextContent('boom');
  });
});
