import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import PerformanceDashboard from '../PerformanceDashboard';

vi.mock('../../../api', () => ({
  default: { get: vi.fn() },
}));

import api from '../../../api';

const currentProgram = {
  id: 1,
  name: 'Summer 2026',
  start_date: '2026-06-01',
  end_date: '2026-08-31',
  is_active: true,
};

const pastProgram = {
  id: 2,
  name: 'Summer 2025',
  start_date: '2025-06-01',
  end_date: '2025-08-31',
  is_active: false,
};

const groups = [
  {
    id: 5,
    name: 'Bunk Maple',
    group_type: 'bunk',
    program_id: 1,
    program_name: 'Summer 2026',
    parent_name: 'Unit Aleph',
    author_names: ['Sam Counselor'],
    roster: [
      { person_id: 10, name: 'Sam Counselor', role_in_group: 'author', membership_role: 'counselor' },
    ],
    completion: { submitted: 2, expected: 3, percent: 67, is_complete: false },
    scores: { scale_max: 5, distribution: { '4': 2, '5': 1 }, total_ratings: 3 },
  },
  {
    id: 6,
    name: 'Bunk Oak',
    group_type: 'bunk',
    program_id: 1,
    program_name: 'Summer 2026',
    parent_name: 'Unit Aleph',
    author_names: ['Alex Counselor'],
    completion: { submitted: 4, expected: 4, percent: 100, is_complete: true },
    scores: { scale_max: 5, distribution: { '5': 4 }, total_ratings: 4 },
  },
];

const payloadWithCurrent = {
  date: '2026-07-10',
  today: '2026-07-10',
  current_program: currentProgram,
  program: currentProgram,
  programs: [currentProgram, pastProgram],
  groups,
};

function renderDashboard(initialEntry = '/groups/performance?date=2026-07-10&group_type=bunk&program=1') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/groups/performance" element={<PerformanceDashboard />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('PerformanceDashboard', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue({ data: payloadWithCurrent });
  });

  it('renders current tab with program name, dates, filters, and group cards', async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Bunk Maple')).toBeInTheDocument();
    });

    expect(screen.getByTestId('performance-program-name')).toHaveTextContent('Summer 2026');
    expect(screen.getByTestId('performance-program-dates')).toHaveTextContent('June 1, 2026');
    expect(screen.getByTestId('performance-tab-current')).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('Sam Counselor')).toBeInTheDocument();
    expect(screen.getAllByText(/Summer 2026/).length).toBeGreaterThan(0);

    const mapleCard = screen.getByTestId('performance-group-5');
    expect(mapleCard.querySelector('a')).toHaveAttribute(
      'href',
      '/dashboards/group/5?date=2026-07-10&program=1',
    );

    expect(api.get).toHaveBeenCalledWith(
      '/api/v1/dashboards/groups/performance/',
      expect.objectContaining({
        params: expect.objectContaining({
          group_type: 'bunk',
          date: '2026-07-10',
          program: '1',
        }),
      }),
    );

    expect(screen.getByTestId('performance-date-picker')).toHaveValue('2026-07-10');
  });

  it('shows past program tiles and drills into a selected program', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockImplementation(async (_url, config) => {
      const programId = config?.params?.program;
      if (String(programId) === '2') {
        return {
          data: {
            ...payloadWithCurrent,
            date: '2025-08-31',
            program: pastProgram,
            groups,
          },
        };
      }
      return { data: payloadWithCurrent };
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Bunk Maple')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('performance-tab-past'));

    expect(screen.getByTestId('past-program-tile-2')).toBeInTheDocument();
    expect(screen.queryByTestId('performance-groups')).not.toBeInTheDocument();

    await user.click(screen.getByTestId('past-program-tile-2'));

    await waitFor(() => {
      expect(screen.getByTestId('performance-program-name')).toHaveTextContent('Summer 2025');
    });
    expect(screen.getByTestId('past-programs-back')).toBeInTheDocument();
    expect(screen.getByTestId('performance-group-5').querySelector('a')).toHaveAttribute(
      'href',
      '/dashboards/group/5?date=2025-08-31&program=2&tab=past',
    );
  });

  it('expands roster panel on tile toggle', async () => {
    const user = userEvent.setup();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText('Bunk Maple')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('performance-roster-panel-5')).not.toBeInTheDocument();
    await user.click(screen.getByTestId('performance-roster-toggle-5'));
    const panel = screen.getByTestId('performance-roster-panel-5');
    expect(panel).toBeInTheDocument();
    expect(panel).toHaveTextContent('Sam Counselor');
  });

  it('shows empty state when no current program is active', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        date: '2026-01-15',
        today: '2026-01-15',
        current_program: null,
        program: null,
        programs: [pastProgram],
        groups: [],
      },
    });

    renderDashboard('/groups/performance?date=2026-01-15&group_type=bunk');

    await waitFor(() => {
      expect(screen.getByTestId('performance-no-current-program')).toBeInTheDocument();
    });
    expect(screen.getByText(/No program is active today/i)).toBeInTheDocument();
  });

  it('hides the standalone page title when embedded', async () => {
    render(
      <MemoryRouter initialEntries={['/unit-head?date=2026-07-10&group_type=bunk&program=1']}>
        <Routes>
          <Route path="/unit-head" element={<PerformanceDashboard embedded />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('performance-dashboard-embedded')).toBeInTheDocument();
    });
    expect(screen.queryByText('Group Performance')).not.toBeInTheDocument();
    expect(screen.getByText('Bunk Maple')).toBeInTheDocument();
  });
});
