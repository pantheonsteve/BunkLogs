import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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
  it('renders the shared CamperDashboard and offers an in-context Add Camper Care note CTA (Story 21)', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    renderAt('/camper-care/campers/7');
    await waitFor(() => {
      expect(screen.getByTestId('camper-dashboard')).toBeInTheDocument();
    });
    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/camper-care/campers/7/',
      expect.any(Object),
    );
    const cta = screen.getByTestId('cc-camper-add-note');
    expect(cta).toHaveTextContent(/add camper care note/i);
    expect(cta).toHaveAttribute('href', '/camper-care/notes/new?camperId=7');
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
