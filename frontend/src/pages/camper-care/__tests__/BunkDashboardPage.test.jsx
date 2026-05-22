import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import CamperCareBunkDashboardPage from '../BunkDashboardPage';

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
    bunk: { id: 11, name: 'Cabin Birch', slug: 'cabin-birch', unit_name: 'Senior Village' },
    date: '2026-07-04',
    today: '2026-07-04',
    counselor_names: ['Pat L.', 'Sam R.'],
  },
  help_requested: [
    { id: 901, first_name: 'Sarah', preferred_name: '', last_name: 'L' },
  ],
  off_camp: [],
  bunk_concerns: [],
  score_grid: { columns: [], rows: [] },
  orders: [],
  specialist_reports: { today: [], recent: [] },
};

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/camper-care/bunks/:bunkId"
          element={<CamperCareBunkDashboardPage />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('CamperCareBunkDashboardPage', () => {
  it('renders the shared BunkDashboard payload for a bunk on the caseload', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    renderAt('/camper-care/bunks/11');
    await waitFor(() => {
      expect(screen.getByTestId('bunk-dashboard')).toBeInTheDocument();
    });
    expect(screen.getByText('Cabin Birch')).toBeInTheDocument();
    expect(screen.getByText('Senior Village')).toBeInTheDocument();
    // Hits the CC-scoped endpoint (not the UH one).
    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/camper-care/bunks/11/',
      expect.any(Object),
    );
  });

  it('shows an error banner when the fetch fails with a permission error', async () => {
    getMock.mockRejectedValueOnce({
      response: { data: { detail: 'This bunk is not on your caseload.' } },
    });
    renderAt('/camper-care/bunks/99');
    await waitFor(() => {
      expect(screen.getByTestId('cc-bunk-dashboard-error')).toHaveTextContent(
        /not on your caseload/i,
      );
    });
  });
});
