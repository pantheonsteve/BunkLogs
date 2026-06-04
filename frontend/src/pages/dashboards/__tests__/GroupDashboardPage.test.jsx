import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import GroupDashboardPage from '../GroupDashboardPage';

const getMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
});

function bunkPayload(role = 'camper_care') {
  return {
    role_context: { role, group_type: 'bunk', can_edit: false },
    header: {
      bunk: { id: 11, name: 'Cabin Birch', slug: 'cabin-birch', unit_name: 'Senior Village' },
      program_name: 'Summer 2025 — Session 1',
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

function unitPayload(role = 'unit_head') {
  return {
    role_context: { role, group_type: 'unit', can_edit: false },
    header: {
      group: { id: 21, name: 'Senior Village', slug: 'senior-village', group_type: 'unit', parent: null },
      date: '2026-07-04',
      today: '2026-07-04',
    },
    bunks: [],
    summary: {
      submitted: 0, expected: 0, off_camp: 0,
      help_requested_count: 0, attention_bunk_count: 0, bunk_count: 0,
    },
    help_requested: [],
    off_camp: [],
    bunk_concerns: [],
  };
}

function divisionPayload(role = 'leadership_team') {
  return {
    role_context: { role, group_type: 'division', can_edit: false },
    header: {
      group: { id: 31, name: 'Division Aleph', slug: 'division-aleph', group_type: 'division', parent: null },
      date: '2026-07-04',
      today: '2026-07-04',
    },
    units: [],
    summary: {
      submitted: 0, expected: 0, off_camp: 0,
      bunk_count: 0, unit_count: 0, attention_bunk_count: 0,
    },
  };
}

function classroomPayload(role = 'classroom_author') {
  return {
    role_context: { role, group_type: 'classroom', can_edit: false },
    header: {
      group: { id: 41, name: 'Hebrew 101', slug: 'hebrew-101', group_type: 'classroom', parent: null },
      date: '2026-07-04',
      today: '2026-07-04',
    },
    subjects: [],
    authors: [],
    summary: { subject_count: 0, author_count: 0 },
  };
}

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/dashboards/group/:groupId"
          element={<GroupDashboardPage />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('GroupDashboardPage', () => {
  it('hits the unified group endpoint and renders the bunk dashboard', async () => {
    getMock.mockResolvedValueOnce({ data: bunkPayload('camper_care') });
    renderAt('/dashboards/group/11');
    await waitFor(() => {
      expect(screen.getByTestId('group-dashboard-bunk')).toBeInTheDocument();
    });
    expect(screen.getByText('Cabin Birch')).toBeInTheDocument();
    expect(screen.getByText(/Summer 2025 — Session 1/)).toBeInTheDocument();
    expect(screen.queryByTestId('section-score-grid')).not.toBeInTheDocument();
    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/dashboards/group/11/',
      expect.any(Object),
    );
  });

  it.each([
    ['bunk', bunkPayload, 'group-dashboard-bunk'],
    ['unit', unitPayload, 'group-dashboard-unit'],
    ['division', divisionPayload, 'group-dashboard-division'],
    ['classroom', classroomPayload, 'group-dashboard-classroom'],
  ])(
    'dispatches to the right sub-component for group_type=%s',
    async (_type, build, testid) => {
      getMock.mockResolvedValueOnce({ data: build() });
      renderAt('/dashboards/group/11');
      await waitFor(() => {
        expect(screen.getByTestId(testid)).toBeInTheDocument();
      });
    },
  );

  it.each([
    ['camper_care', '/camper-care'],
    ['unit_head', '/unit-head'],
    ['counselor', '/counselor'],
    ['leadership_team', '/leadership-team'],
    ['admin', '/groups/performance?date=2026-07-04'],
  ])('routes the back link to %s home when role_context.role is %s', async (role, expectedHref) => {
    getMock.mockResolvedValueOnce({ data: bunkPayload(role) });
    renderAt('/dashboards/group/11');
    const backLink = await screen.findByRole('link', { name: /back/i });
    expect(backLink).toHaveAttribute('href', expectedHref);
  });

  it('routes admin back link to performance dashboard preserving date', async () => {
    getMock.mockResolvedValueOnce({ data: bunkPayload('admin') });
    renderAt('/dashboards/group/11?date=2026-06-03');
    const backLink = await screen.findByRole('link', { name: /back/i });
    expect(backLink).toHaveAttribute('href', '/groups/performance?date=2026-06-03');
  });

  it('falls back to /dashboards when role_context is missing', async () => {
    const payload = bunkPayload('camper_care');
    delete payload.role_context;
    getMock.mockResolvedValueOnce({ data: payload });
    renderAt('/dashboards/group/11');
    // No role_context → no recognized group_type → unsupported component.
    await waitFor(() => {
      expect(screen.getByTestId('group-dashboard-unsupported')).toBeInTheDocument();
    });
    const backLink = await screen.findByRole('link', { name: /back/i });
    expect(backLink).toHaveAttribute('href', '/dashboards');
  });

  it('renders the unsupported empty-state on a 400 from the backend', async () => {
    getMock.mockRejectedValueOnce({
      response: {
        status: 400,
        data: ["Dashboard not yet supported for group_type 'cohort'."],
      },
    });
    renderAt('/dashboards/group/99');
    await waitFor(() => {
      expect(screen.getByTestId('group-dashboard-unsupported')).toBeInTheDocument();
    });
    expect(screen.getByRole('alert')).toHaveTextContent(/cohort/);
  });

  it('surfaces a permission error from the backend', async () => {
    getMock.mockRejectedValueOnce({
      response: {
        status: 403,
        data: { detail: 'You do not have access to this group.' },
      },
    });
    renderAt('/dashboards/group/99');
    await waitFor(() => {
      expect(screen.getByTestId('group-dashboard-error')).toHaveTextContent(
        /do not have access/i,
      );
    });
  });
});
