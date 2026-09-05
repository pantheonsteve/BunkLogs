import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';

const mockUseAuth = vi.fn();
vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// Pin tenant resolution to "unscoped host" so the single-org fixtures below
// resolve regardless of any local VITE_DEV_ORGANIZATION_SLUG.
vi.mock('../../../utils/orgSlug', async (importOriginal) => ({
  ...(await importOriginal()),
  resolveOrganizationSlug: () => null,
}));

const fetchAdminDashboard = vi.fn();
vi.mock('../../../api/admin', () => ({
  fetchAdminDashboard: (...args) => fetchAdminDashboard(...args),
  listAdminPrograms: vi.fn(() => Promise.resolve({ results: [] })),
}));

// DirectorHome fires seven independent requests of its own; this page's
// behaviour is what's under test.
vi.mock('../DirectorHome', () => ({
  default: () => <div data-testid="director-home" />,
}));

import AdminHome from '../AdminHome';

const DASHBOARD = {
  today: '2026-08-30',
  org_snapshot: {
    active_people: 42,
    memberships_by_role: [
      { role: 'camper', count: 20 },
      { role: 'counselor', count: 14 },
      { role: 'admin', count: 2 },
    ],
  },
  setup_attention: {
    groups_without_author: { count: 2, groups: [{ id: 1, name: 'Grade 3' }, { id: 2, name: 'Grade 5' }] },
    groups_without_subjects: { count: 0, groups: [] },
    people_never_invited: { count: 7 },
    people_invited_not_signed_in: { count: 3 },
    completed: {
      groups_created: 2,
      groups_total: 2,
      subjects_enrolled: 20,
      groups_with_forms: 2,
    },
  },
  logs_this_week: {
    window_start: '2026-08-24',
    window_end: '2026-08-30',
    submitted: 9,
    expected: 20,
    behind: [
      { id: 2, name: 'Grade 5', submitted: 1, expected: 8 },
      { id: 1, name: 'Grade 3', submitted: 8, expected: 12 },
    ],
  },
  recent_activity: [
    {
      id: 'a1',
      actor: 'Edie Cooper',
      summary: 'Reflection created',
      created_at: '2026-08-30T09:00:00Z',
      deep_link: '/admin/people/12',
    },
  ],
};

function adminIn(programTypes) {
  return {
    first_name: 'Edie',
    organizations: [{
      slug: 'org',
      name: 'Org',
      capability: 'admin',
      roles: ['admin'],
      program_types: programTypes,
    }],
    membership_roles: ['admin'],
  };
}

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname + location.search}</div>;
}

function renderHome(user = adminIn(['summer_camp'])) {
  mockUseAuth.mockReturnValue({ user });
  return render(
    <MemoryRouter initialEntries={['/admin/home']}>
      <Routes>
        <Route path="/admin/home" element={<AdminHome />} />
        <Route path="*" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mockUseAuth.mockReset();
  fetchAdminDashboard.mockReset();
  fetchAdminDashboard.mockResolvedValue(DASHBOARD);
});

describe('AdminHome dashboard', () => {
  it('leads with the setup problems rather than a grid of nav tiles', async () => {
    renderHome();

    expect(await screen.findByTestId('admin-home-setup')).toBeInTheDocument();
    expect(screen.getByTestId('attention-no-author')).toHaveTextContent(
      /2 groups have no counselors assigned/i,
    );
    expect(screen.getByTestId('attention-no-author')).toHaveTextContent('Grade 3 · Grade 5');
    expect(screen.getByTestId('attention-never-invited')).toHaveTextContent(
      /7 people have never been invited/i,
    );
  });

  it('ticks off a check that has no problems instead of hiding it', async () => {
    renderHome();
    const row = await screen.findByTestId('attention-no-subjects');
    expect(row).toHaveTextContent(/every group either has campers or is confirmed staff-only/i);
  });

  it('lists the groups behind on logs, most behind first', async () => {
    renderHome();

    const logs = await screen.findByTestId('admin-home-logs');
    expect(logs).toHaveTextContent('9 of 20 expected');
    const names = Array.from(logs.querySelectorAll('li a'))
      .map((a) => a.textContent)
      .filter((text) => text !== 'Open');
    expect(names).toEqual(['Grade 5', 'Grade 3']);
  });

  it('sends the never-invited row to People pre-filtered to that state', async () => {
    renderHome();

    await screen.findByTestId('attention-never-invited');
    await userEvent.click(screen.getByRole('button', { name: /send invitations/i }));

    await waitFor(() => {
      expect(screen.getByTestId('location')).toHaveTextContent(
        '/admin/people?invite_status=never',
      );
    });
  });

  it('opens with a greeting and the date rather than the word Dashboard', async () => {
    renderHome();

    const heading = await screen.findByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent(/^Good (morning|afternoon|evening), Edie$/);
    expect(await screen.findByText(/Sunday, August 30/)).toBeInTheDocument();
  });

  it('scores setup as a fraction, with the done steps ticked', async () => {
    renderHome();

    const setup = await screen.findByTestId('admin-home-setup');
    // Six steps; groups, subjects, forms and no-subjects are done.
    expect(setup).toHaveTextContent('4 of 6 steps complete');
    expect(screen.getByTestId('setup-progress')).toHaveAttribute('aria-valuenow', '4');
    expect(screen.getByTestId('setup-groups-created')).toHaveTextContent('2 groups created');
    expect(screen.getByTestId('setup-forms-assigned')).toHaveTextContent(
      /all 2 groups have a form assigned/i,
    );
    expect(screen.getByRole('link', { name: /continue setup/i })).toHaveAttribute(
      'href', '/admin/setup',
    );
  });

  it('says which week the logs card is reporting on', async () => {
    renderHome();
    expect(await screen.findByTestId('admin-home-logs')).toHaveTextContent(
      'Week of Aug 24 · 9 of 20 expected',
    );
  });

  it('gives each activity row a time and a link to what changed', async () => {
    renderHome();

    const activity = await screen.findByTestId('admin-home-activity');
    const link = activity.querySelector('a');
    expect(link).toHaveAttribute('href', '/admin/people/12');
    expect(link).toHaveTextContent(/ago|just now/);
  });

  it('counts staff from the non-camper memberships', async () => {
    renderHome();
    expect(await screen.findByTestId('stat-staff')).toHaveTextContent('16');
  });

  it('drops the nav tiles entirely — the sidebar owns navigation now', async () => {
    renderHome();

    await screen.findByTestId('admin-home-setup');
    expect(screen.queryByTestId('admin-home-links')).not.toBeInTheDocument();
  });

  it('still appends the reflections section at a religious school', async () => {
    renderHome(adminIn(['religious_school']));
    expect(await screen.findByTestId('director-home')).toBeInTheDocument();
  });

  it('surfaces a load failure instead of rendering an empty dashboard', async () => {
    fetchAdminDashboard.mockRejectedValue({
      response: { data: { detail: 'Nope.' } },
    });
    renderHome();

    expect(await screen.findByText('Nope.')).toBeInTheDocument();
  });
});
