import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import CamperCareCamperDashboardPage from '../CamperDashboardPage';

const getMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
});

const samplePayload = {
  header: {
    camper: { id: 7, first_name: 'Sarah', preferred_name: '', last_name: 'Levin' },
    bunk: { id: 11, name: 'Cabin Birch' },
    unit: { id: 100, name: 'Senior Village' },
    today: '2026-07-04',
    date: '2026-07-04',
    range: { key: 'last_4_weeks', date_start: '2026-06-06', date_end: '2026-07-04' },
  },
  trend: { series: [], points: [] },
  today_reflection: null,
  today_scores: [],
  today_flags: [],
  specialist_reports: [],
  camper_care_notes: [],
};

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/camper-care/campers/:camperId"
          element={<CamperCareCamperDashboardPage />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('CamperCareCamperDashboardPage', () => {
  it('renders the shared CamperDashboard (legacy note CTA removed in 7_24)', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    renderAt('/camper-care/campers/7');
    await waitFor(() => {
      expect(screen.getByTestId('camper-dashboard')).toBeInTheDocument();
    });
    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/camper-care/campers/7/',
      expect.any(Object),
    );
    expect(screen.queryByTestId('cc-camper-add-note')).not.toBeInTheDocument();
  });

  it('renders the flag history section newest-first and highlights the anchored row from ?flagId=', async () => {
    const flagId = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
    const olderId = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';
    getMock.mockResolvedValueOnce({
      data: {
        ...samplePayload,
        flag_history: [
          {
            id: flagId,
            status: 'active',
            created_at: '2026-07-04T12:00:00Z',
            raised_by: { name: 'Rivka G.', role: 'specialist' },
            trigger_content_type: 'specialist_note',
            trigger_preview: 'Crying after lights-out, asking for parent contact.',
          },
          {
            id: olderId,
            status: 'resolved',
            created_at: '2026-06-15T12:00:00Z',
            raised_by: { name: 'Maya R.', role: 'unit_head' },
            trigger_content_type: '',
            trigger_preview: '',
          },
        ],
      },
    });
    renderAt(`/camper-care/campers/7?flagId=${encodeURIComponent(flagId)}#flag-${flagId}`);
    await waitFor(() => {
      expect(screen.getByTestId('cc-camper-flag-history')).toBeInTheDocument();
    });
    const anchored = screen.getByTestId(`cc-camper-flag-${flagId}`);
    expect(anchored).toHaveAttribute('data-anchored', 'true');
    expect(anchored).toHaveTextContent(/Active/);
    expect(anchored).toHaveTextContent(/Crying after lights-out/);
    const older = screen.getByTestId(`cc-camper-flag-${olderId}`);
    expect(older).toHaveAttribute('data-anchored', 'false');
    expect(older).toHaveTextContent(/Resolved/);
  });

  it('renders the empty-state for the flag history when there are none', async () => {
    getMock.mockResolvedValueOnce({ data: { ...samplePayload, flag_history: [] } });
    renderAt('/camper-care/campers/7');
    await waitFor(() => {
      expect(screen.getByTestId('cc-camper-flag-history-empty')).toBeInTheDocument();
    });
  });

  it('updates URL params and re-fetches with notes_from / notes_to when the date filter is applied', async () => {
    getMock.mockResolvedValue({ data: samplePayload });
    renderAt('/camper-care/campers/7');
    await waitFor(() => {
      expect(screen.getByTestId('cc-camper-notes-filter')).toBeInTheDocument();
    });
    fireEvent.change(screen.getByTestId('cc-notes-from'), { target: { value: '2026-06-01' } });
    fireEvent.change(screen.getByTestId('cc-notes-to'), { target: { value: '2026-07-04' } });
    fireEvent.click(screen.getByTestId('cc-notes-filter-apply'));
    await waitFor(() => {
      const calls = getMock.mock.calls;
      const params = calls[calls.length - 1]?.[1]?.params || {};
      expect(params).toMatchObject({
        notes_from: '2026-06-01',
        notes_to: '2026-07-04',
      });
    }, { timeout: 2000 });
    expect(screen.getByTestId('cc-notes-filter-active')).toHaveTextContent(/2026-06-01/);
  });

  it('surfaces an error when the camper is off-caseload', async () => {
    getMock.mockRejectedValueOnce({
      response: { data: { detail: 'This camper is not on your caseload.' } },
    });
    renderAt('/camper-care/campers/9999');
    await waitFor(() => {
      expect(screen.getByTestId('cc-camper-dashboard-error')).toHaveTextContent(
        /not on your caseload/i,
      );
    });
  });
});
