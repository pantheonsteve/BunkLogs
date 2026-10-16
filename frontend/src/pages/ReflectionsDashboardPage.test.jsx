import { describe, it, expect, vi, beforeEach } from 'vitest';
import { cleanup, render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ReflectionsDashboardPage from './ReflectionsDashboardPage';

const getMock = vi.fn();

vi.mock('../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

const mockUseAuth = vi.fn(() => ({ user: null }));
vi.mock('../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('../utils/orgSlug', async (importOriginal) => ({
  ...(await importOriginal()),
  resolveOrganizationSlug: () => 'tbe',
}));

vi.mock('../partials/Sidebar', () => ({ default: () => <div /> }));
vi.mock('../partials/Header', () => ({ default: () => <div /> }));

const adminUser = {
  organizations: [{ slug: 'tbe', name: 'TBE', capability: 'admin', roles: ['admin'] }],
  membership_roles: ['admin'],
};

const programLeadUser = {
  organizations: [{
    slug: 'tbe', name: 'TBE', capability: 'program_lead', roles: ['leadership_team'],
  }],
  membership_roles: ['leadership_team'],
};

const supervisorUser = {
  organizations: [{ slug: 'tbe', name: 'TBE', capability: 'supervisor', roles: ['faculty'] }],
  membership_roles: ['faculty'],
};

function userWithCompletion(extra = {}) {
  return {
    organizations: [{
      slug: 'tbe',
      name: 'TBE',
      capability: 'admin',
      roles: ['admin'],
      reflection_completion: true,
      ...extra,
    }],
    membership_roles: ['admin'],
  };
}

const templates = [
  {
    template_id: 10,
    template_name: 'Counselor Daily',
    display_title: 'Counselor Daily',
    cadence: 'daily',
    audience_types: ['bunk'],
    group_count: 3,
    groups: [
      { assignment_id: 101, label: 'Mountainview East', audience_type: 'bunk', program_id: 1, program_label: 'Summer 2026' },
      { assignment_id: 102, label: 'Mountainview West', audience_type: 'bunk', program_id: 1, program_label: 'Summer 2026' },
      { assignment_id: 103, label: 'Lakeside', audience_type: 'bunk', program_id: 2, program_label: 'Winter 2026' },
    ],
  },
  {
    template_id: 20,
    template_name: 'Kitchen Daily',
    display_title: 'Kitchen Daily',
    cadence: 'daily',
    audience_types: ['team'],
    group_count: 1,
    groups: [{ assignment_id: 201, label: 'Kitchen Staff', audience_type: 'team', program_id: 1, program_label: 'Summer 2026' }],
  },
];

function routeGet(url) {
  if (url === '/api/v1/dashboards/assignment-templates/') {
    return Promise.resolve({ data: { templates } });
  }
  return Promise.resolve({ data: {} });
}

function renderPage(entry = '/dashboards/reflections') {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <ReflectionsDashboardPage />
    </MemoryRouter>,
  );
}

describe('ReflectionsDashboardPage', () => {
  beforeEach(() => {
    getMock.mockReset();
    getMock.mockImplementation(routeGet);
    mockUseAuth.mockReturnValue({ user: programLeadUser });
  });

  it('offers admins a way back to Admin Home', async () => {
    mockUseAuth.mockReturnValue({ user: adminUser });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('reflections-back')).toBeInTheDocument());
    expect(screen.getByTestId('reflections-back')).toHaveAttribute('href', '/admin/home');
  });

  it('hides the Admin Home link from program leads, who cannot open it', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('reflections-form-tiles')).toBeInTheDocument());
    expect(screen.queryByTestId('reflections-back')).toBeNull();
  });

  it('does not show form tiles to someone who cannot open responses', async () => {
    mockUseAuth.mockReturnValue({ user: supervisorUser });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('reflections-responses-restricted')).toBeInTheDocument());
    expect(screen.queryByTestId('reflections-form-tiles')).not.toBeInTheDocument();
  });

  it('hides the Completion tab unless an admin has the setting on', async () => {
    renderPage('/dashboards/reflections?tab=completion');
    await waitFor(() => expect(screen.getByTestId('reflections-form-tiles')).toBeInTheDocument());
    expect(screen.queryByTestId('reflections-tab-completion')).not.toBeInTheDocument();

    cleanup();
    mockUseAuth.mockReturnValue({ user: adminUser });
    renderPage('/dashboards/reflections?tab=completion');
    await waitFor(() => expect(screen.getByTestId('reflections-form-tiles')).toBeInTheDocument());
    expect(screen.queryByTestId('reflections-tab-completion')).not.toBeInTheDocument();
  });

  it('opens the Completion tab from the URL for an admin with the setting on', async () => {
    mockUseAuth.mockReturnValue({ user: userWithCompletion() });
    getMock.mockImplementation((url) => {
      if (url === '/api/v1/admin/settings/') {
        return Promise.resolve({ data: { enabled_roles: ['madrich'] } });
      }
      if (url === '/api/v1/leadership-team/templates/') {
        return Promise.resolve({
          data: { templates: [{ role: 'madrich', subject_mode: 'self' }] },
        });
      }
      if (String(url).includes('/api/v1/admin/reflections/teams/')) {
        return Promise.resolve({
          data: {
            header: {
              role: 'madrich',
              program: { name: 'School' },
              member_count: 0,
              date: '2026-08-03',
              period: { start: '2026-08-03', end: '2026-08-09', cadence: 'weekly' },
            },
            template: { id: 5 },
            submission_status: { submitted: 0, day_off: 0, not_submitted: 0, total: 0 },
            members: [],
          },
        });
      }
      return routeGet(url);
    });
    renderPage('/dashboards/reflections?tab=completion');
    expect(await screen.findByTestId('reflections-tab-completion')).toBeInTheDocument();
    expect(await screen.findByTestId('reflections-completion')).toBeInTheDocument();
    expect(screen.queryByTestId('reflections-form-tiles')).not.toBeInTheDocument();
  });

  it('renders form tiles linking to the reflections dashboard', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('reflections-form-tiles')).toBeInTheDocument());
    expect(screen.getByTestId('reflections-form-tile-10')).toHaveAttribute(
      'href',
      expect.stringMatching(
        /^\/dashboards\/reflections\/10\?date=\d{4}-\d{2}-\d{2}$/,
      ),
    );
    expect(screen.getByTestId('reflections-form-tile-20')).toBeInTheDocument();
    expect(screen.queryByLabelText('Select form')).not.toBeInTheDocument();
    expect(getMock).not.toHaveBeenCalledWith(
      expect.stringMatching(/\/assignment-template\//),
      expect.anything(),
    );
  });

  it('narrows tiles when audience filter changes', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('reflections-form-tile-10')).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText('Filter by audience'), { target: { value: 'bunk' } });
    expect(screen.getByTestId('reflections-form-tile-10')).toBeInTheDocument();
    expect(screen.queryByTestId('reflections-form-tile-20')).not.toBeInTheDocument();
  });

  it('filters tiles by program', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('reflections-form-tiles')).toBeInTheDocument());
    expect(screen.getByLabelText('Filter by program')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Filter by program'), { target: { value: '2' } });
    await waitFor(() => {
      expect(screen.getByTestId('reflections-form-tile-10')).toBeInTheDocument();
      expect(screen.queryByTestId('reflections-form-tile-20')).not.toBeInTheDocument();
    });
  });

  it('filters tiles by group', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('reflections-form-tiles')).toBeInTheDocument());
    expect(screen.getByLabelText('Filter by group')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Filter by group'), { target: { value: '201' } });
    await waitFor(() => {
      expect(screen.getByTestId('reflections-form-tile-20')).toBeInTheDocument();
      expect(screen.queryByTestId('reflections-form-tile-10')).not.toBeInTheDocument();
    });
  });

  it('requests the selector with the active status by default', async () => {
    renderPage();
    await waitFor(() => expect(getMock).toHaveBeenCalledWith(
      '/api/v1/dashboards/assignment-templates/',
      expect.objectContaining({
        params: expect.objectContaining({ status: 'active', scope: 'reflections' }),
      }),
    ));
  });

  it('switches to the ended tab', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByTestId('reflections-form-tiles')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: 'Ended' }));
    await waitFor(() => expect(getMock).toHaveBeenCalledWith(
      '/api/v1/dashboards/assignment-templates/',
      expect.objectContaining({
        params: expect.objectContaining({ status: 'ended', scope: 'reflections' }),
      }),
    ));
  });

  it('shows access restricted on 403', async () => {
    getMock.mockReset();
    getMock.mockRejectedValue({ response: { status: 403 } });
    renderPage();
    await waitFor(() => expect(screen.getByText(/access restricted/i)).toBeInTheDocument());
  });

  it('shows empty state when no forms are visible', async () => {
    getMock.mockReset();
    getMock.mockImplementation((url) => {
      if (url === '/api/v1/dashboards/assignment-templates/') {
        return Promise.resolve({ data: { templates: [] } });
      }
      return Promise.resolve({ data: {} });
    });
    renderPage();
    await waitFor(() =>
      expect(screen.getByText(/no active reflections are visible/i)).toBeInTheDocument(),
    );
  });

  it('shows no-match message when filters exclude all forms', async () => {
    getMock.mockImplementation((url) => {
      if (url === '/api/v1/dashboards/assignment-templates/') {
        return Promise.resolve({
          data: {
            templates: [{
              template_id: 20,
              display_title: 'Kitchen Daily',
              cadence: 'daily',
              audience_types: ['team'],
              group_count: 1,
              groups: [{
                assignment_id: 201,
                label: 'Kitchen Staff',
                program_id: 1,
                program_label: 'Summer 2026',
              }],
            }],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('reflections-form-tile-20')).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText('Filter by audience'), { target: { value: 'bunk' } });
    await waitFor(() =>
      expect(screen.getByText(/no forms match these filters/i)).toBeInTheDocument(),
    );
  });
});
