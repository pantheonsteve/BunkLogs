import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import BunkDashboardPage from '../BunkDashboardPage';

const getMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
});

function payloadFor(role) {
  return {
    role_context: { role, can_edit: false },
    header: {
      bunk: { id: 11, name: 'Cabin Birch', slug: 'cabin-birch', unit_name: 'Senior Village' },
      date: '2026-07-04',
      today: '2026-07-04',
      counselor_names: ['Pat L.', 'Sam R.'],
    },
    help_requested: [],
    off_camp: [],
    bunk_concerns: [],
    score_grid: { columns: [], rows: [] },
    orders: { today: [], carried_over: [], counts: { open: 0, in_progress: 0, resolved: 0 } },
    specialist_reports: { today: [], recent: [], sensitive_counts_by_camper: {} },
  };
}

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/dashboards/bunk/:bunkId"
          element={<BunkDashboardPage />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('BunkDashboardPage', () => {
  it('hits the unified endpoint and renders the shared BunkDashboard', async () => {
    getMock.mockResolvedValueOnce({ data: payloadFor('camper_care') });
    renderAt('/dashboards/bunk/11');
    await waitFor(() => {
      expect(screen.getByTestId('bunk-dashboard')).toBeInTheDocument();
    });
    expect(screen.getByText('Cabin Birch')).toBeInTheDocument();
    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/dashboards/bunks/11/',
      expect.any(Object),
    );
  });

  it.each([
    ['camper_care', '/camper-care'],
    ['unit_head', '/unit-head'],
    ['counselor', '/counselor'],
    ['leadership_team', '/leadership-team'],
    ['admin', '/admin'],
  ])('routes the back link to %s home when role_context.role is %s', async (role, expectedHref) => {
    getMock.mockResolvedValueOnce({ data: payloadFor(role) });
    renderAt('/dashboards/bunk/11');
    const backLink = await screen.findByRole('link', { name: /back/i });
    expect(backLink).toHaveAttribute('href', expectedHref);
  });

  it('falls back to /dashboards when role_context is missing', async () => {
    const payload = payloadFor('camper_care');
    delete payload.role_context;
    getMock.mockResolvedValueOnce({ data: payload });
    renderAt('/dashboards/bunk/11');
    const backLink = await screen.findByRole('link', { name: /back/i });
    expect(backLink).toHaveAttribute('href', '/dashboards');
  });

  it('surfaces a permission error from the backend', async () => {
    getMock.mockRejectedValueOnce({
      response: { data: { detail: 'You do not have access to this bunk.' } },
    });
    renderAt('/dashboards/bunk/99');
    await waitFor(() => {
      expect(screen.getByTestId('bunk-dashboard-error')).toHaveTextContent(
        /do not have access/i,
      );
    });
  });
});
