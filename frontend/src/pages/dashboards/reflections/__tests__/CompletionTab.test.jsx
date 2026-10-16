import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CompletionTab from '../CompletionTab';

const fetchMock = vi.fn();
const exportUrlMock = vi.fn();
vi.mock('../../../../api/adminReflections', () => ({
  fetchAdminReflectionsTeam: (...args) => fetchMock(...args),
  exportAdminReflectionsTeamUrl: (...args) => exportUrlMock(...args),
}));

const settingsMock = vi.fn();
vi.mock('../../../../api/admin', () => ({
  getAdminSettings: () => settingsMock(),
}));

const templatesMock = vi.fn();
vi.mock('../../../../api/leadershipTeam', () => ({
  listTemplates: () => templatesMock(),
}));

const mockUseAuth = vi.fn();
vi.mock('../../../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

const samplePayload = {
  header: {
    role: 'madrich',
    role_label: 'Madrich',
    program: { id: 1, name: 'Religious School' },
    member_count: 2,
    date: '2026-08-03',
    period: { start: '2026-08-03', end: '2026-08-09', cadence: 'weekly' },
  },
  template: { id: 5, slug: 'weekly' },
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
  exportUrlMock.mockImplementation(
    (role) => `/api/v1/admin/reflections/teams/${role}/export/`,
  );
  settingsMock.mockReset();
  settingsMock.mockResolvedValue({ enabled_roles: ['counselor', 'madrich'] });
  templatesMock.mockReset();
  templatesMock.mockResolvedValue({
    templates: [
      { role: 'madrich', subject_mode: 'self' },
      { role: 'counselor', subject_mode: 'self' },
      { role: 'faculty', subject_mode: 'single_subject' },
    ],
  });
  mockUseAuth.mockReset();
  mockUseAuth.mockReturnValue({ orgSlug: 'org', user: { organizations: [] } });
  fetchMock.mockResolvedValue(samplePayload);
});

function renderTab() {
  return render(
    <MemoryRouter initialEntries={['/dashboards/reflections?tab=completion']}>
      <CompletionTab />
    </MemoryRouter>,
  );
}

describe('CompletionTab', () => {
  it('defaults to the first role that has a self-reflection template', async () => {
    renderTab();
    await waitFor(() => expect(screen.getByText('Counselor completion')).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith('counselor', expect.any(Object));
    expect(screen.getByTestId('admin-reflections-role')).toHaveValue('counselor');
    expect(screen.getByTestId('admin-reflections-export')).toHaveAttribute(
      'href',
      '/api/v1/admin/reflections/teams/counselor/export/',
    );
  });

  it('shows the grade filter when roster rows carry grades', async () => {
    renderTab();
    const gradeEight = await screen.findByTestId('admin-reflections-grade-8');
    expect(screen.getByTestId('admin-reflections-grade-10')).toBeInTheDocument();
    fireEvent.click(gradeEight);
    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith(
      'counselor',
      expect.objectContaining({ gradeLevels: [8] }),
    ));
  });

  it('hides the grade filter when no row has a grade', async () => {
    fetchMock.mockResolvedValue({
      ...samplePayload,
      members: samplePayload.members.map((member) => ({ ...member, grade_level: null })),
    });
    renderTab();
    await screen.findByText('Counselor completion');
    expect(screen.queryByTestId('admin-reflections-grade-8')).not.toBeInTheDocument();
  });
});
