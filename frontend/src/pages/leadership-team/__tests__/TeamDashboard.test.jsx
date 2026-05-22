import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import LeadershipTeamTeamDashboard from '../TeamDashboard';

const getMock = vi.fn();
vi.mock('../../../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'test-org', user: { id: 1 } }),
}));

const samplePayload = {
  header: {
    team_role: 'kitchen_staff',
    team_role_label: 'Kitchen Staff',
    program: { id: 1, name: 'Summer 2026' },
    member_count: 3,
    supervisors: [{ membership_id: 1, person_name: 'Lou LT', is_viewer: true }],
    period: { start: '2026-07-06', end: '2026-07-12', cadence: 'weekly' },
    date: '2026-07-10',
  },
  submission_status: { submitted: 1, day_off: 1, not_submitted: 1, total: 3 },
  flagged: [],
  members: [
    {
      membership_id: 11, person_id: 21, person_name: 'Asha Cook',
      language_preference: 'en', status: 'submitted', reflection_id: 100,
      submitted_at: '2026-07-10T08:00:00Z', language_of_authorship: 'en',
      preview: 'good day', attention_marker_count: 0,
    },
    {
      membership_id: 12, person_id: 22, person_name: 'Ben Cook',
      language_preference: 'en', status: 'not_submitted', reflection_id: null,
      submitted_at: null, language_of_authorship: null,
      preview: '', attention_marker_count: 0,
    },
    {
      membership_id: 13, person_id: 23, person_name: 'Cami Cook',
      language_preference: 'en', status: 'day_off', reflection_id: 102,
      submitted_at: '2026-07-10T07:00:00Z', language_of_authorship: 'en',
      preview: '', attention_marker_count: 2,
    },
  ],
};

beforeEach(() => { getMock.mockReset(); });

function renderAt(route) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/leadership-team/teams/:teamRole" element={<LeadershipTeamTeamDashboard />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LeadershipTeamTeamDashboard', () => {
  it('renders header, status, and member rows', async () => {
    getMock.mockResolvedValue({ data: samplePayload });
    renderAt('/leadership-team/teams/kitchen_staff');
    await waitFor(() => expect(screen.getByText('Kitchen Staff')).toBeInTheDocument());
    expect(screen.getByTestId('lt-member-row-11')).toBeInTheDocument();
    expect(screen.getByTestId('lt-marker-count-13')).toHaveTextContent('2 flags');
  });

  it('filters member rows by status when a filter chip is clicked', async () => {
    getMock.mockResolvedValue({ data: samplePayload });
    renderAt('/leadership-team/teams/kitchen_staff');
    await waitFor(() => screen.getByTestId('lt-team-members'));
    fireEvent.click(screen.getByTestId('lt-filter-not_submitted'));
    await waitFor(() => {
      expect(screen.getByTestId('lt-member-row-12')).toBeInTheDocument();
      expect(screen.queryByTestId('lt-member-row-11')).not.toBeInTheDocument();
    });
  });

  it('shows a permission error if the API returns 403', async () => {
    getMock.mockRejectedValue({ response: { status: 403 } });
    renderAt('/leadership-team/teams/kitchen_staff');
    await waitFor(() => expect(screen.getByTestId('lt-team-error')).toBeInTheDocument());
    expect(screen.getByText(/do not supervise/)).toBeInTheDocument();
  });
});
