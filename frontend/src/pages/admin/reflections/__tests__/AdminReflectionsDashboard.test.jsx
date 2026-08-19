import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AdminReflectionsDashboard from '../AdminReflectionsDashboard';

const fetchMock = vi.fn();
const exportUrlMock = vi.fn();
vi.mock('../../../../api/adminReflections', () => ({
  fetchAdminReflectionsTeam: (...args) => fetchMock(...args),
  exportAdminReflectionsTeamUrl: (...args) => exportUrlMock(...args),
}));

const mockUseAuth = vi.fn();
vi.mock('../../../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// Pin tenant resolution to "unscoped host" so the single-org fixtures below
// resolve regardless of any local VITE_DEV_ORGANIZATION_SLUG.
vi.mock('../../../../utils/orgSlug', async (importOriginal) => ({
  ...(await importOriginal()),
  resolveOrganizationSlug: () => null,
}));

function adminIn(programTypes) {
  return {
    user: {
      organizations: [{
        slug: 'org',
        name: 'Org',
        capability: 'admin',
        roles: ['admin'],
        program_types: programTypes,
      }],
      membership_roles: ['admin'],
    },
    loading: false,
  };
}

const samplePayload = {
  header: {
    role: 'madrich',
    role_label: 'Madrich',
    program: { id: 1, name: 'TBE Religious School' },
    member_count: 2,
    date: '2026-08-03',
    period: { start: '2026-08-03', end: '2026-08-09', cadence: 'weekly' },
  },
  template: { id: 5, slug: 'tbe-madrich-3-2-1-weekly' },
  submission_status: { submitted: 1, day_off: 0, not_submitted: 1, total: 2 },
  members: [
    {
      membership_id: 11, person_id: 21, person_name: 'Maya A.', grade_level: 8,
      status: 'submitted', reflection_id: 100, submitted_at: '2026-08-03T10:00:00Z',
    },
    {
      membership_id: 12, person_id: 22, person_name: 'Ben B.', grade_level: 10,
      status: 'not_submitted', reflection_id: null, submitted_at: null,
    },
  ],
};

beforeEach(() => {
  fetchMock.mockReset();
  exportUrlMock.mockReset();
  exportUrlMock.mockReturnValue('/api/v1/admin/reflections/teams/madrich/export/');
  mockUseAuth.mockReset();
  mockUseAuth.mockReturnValue(adminIn(['religious_school']));
});

function renderAt(route = '/admin/reflections') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AdminReflectionsDashboard />
    </MemoryRouter>,
  );
}

describe('AdminReflectionsDashboard', () => {
  it('renders the weekly completion roster for a religious-school admin', async () => {
    fetchMock.mockResolvedValue(samplePayload);
    renderAt();

    await waitFor(() => expect(screen.getByText('Madrich completion')).toBeInTheDocument());
    expect(screen.getByTestId('admin-reflections-member-11')).toBeInTheDocument();
    expect(screen.getByTestId('admin-reflections-member-12')).toBeInTheDocument();
    expect(screen.getByTestId('admin-reflections-stat-submitted')).toHaveTextContent('Submitted');
    expect(screen.getByTestId('admin-reflections-stat-not_submitted')).toHaveTextContent('1');
    expect(screen.getByTestId('admin-reflections-completion')).toHaveTextContent('50%');
    expect(screen.getByTestId('admin-reflections-back')).toHaveAttribute('href', '/admin/home');
    expect(screen.getByTestId('admin-reflections-export')).toHaveAttribute(
      'href',
      '/api/v1/admin/reflections/teams/madrich/export/',
    );
  });

  it('renders an unavailable state for a camp organization', async () => {
    mockUseAuth.mockReturnValue(adminIn(['summer_camp']));
    renderAt();

    expect(screen.getByTestId('admin-reflections-unavailable')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('refetches with the selected grade levels when a grade pill is toggled', async () => {
    fetchMock.mockResolvedValue(samplePayload);
    renderAt();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByTestId('admin-reflections-grade-8'));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock).toHaveBeenLastCalledWith(
      'madrich',
      expect.objectContaining({ gradeLevels: [8] }),
    );
  });
});
