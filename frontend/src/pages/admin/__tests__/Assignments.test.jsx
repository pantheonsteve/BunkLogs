import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';

vi.mock('../../../api', () => ({
  default: {
    get: vi.fn(),
  },
}));

vi.mock('../../../api/admin', () => ({
  listAdminAssignments: vi.fn(),
  listAdminPrograms: vi.fn(),
  createAdminAssignment: vi.fn(),
  patchAdminAssignment: vi.fn(),
  getAdminAssignmentFacets: vi.fn(),
}));

vi.mock('../../../api/organization', () => ({
  fetchOrganizationBranding: vi.fn(),
}));

import api from '../../../api';
import { fetchOrganizationBranding } from '../../../api/organization';
import { OrgBrandingProvider } from '../../../context/OrgBrandingContext';
import {
  listAdminAssignments,
  listAdminPrograms,
  createAdminAssignment,
  getAdminAssignmentFacets,
} from '../../../api/admin';
import AdminAssignments from '../Assignments';

const program = { id: 1, name: 'Summer 2026', slug: 'summer-2026', is_active: true };
const endedProgram = { id: 2, name: 'Summer 2025', slug: 'summer-2025', is_active: false };

beforeEach(() => {
  vi.clearAllMocks();
  listAdminPrograms.mockResolvedValue({ results: [program, endedProgram] });
  listAdminAssignments.mockResolvedValue({ results: [] });
  // Null facets means "don't filter", so the other tests see all sub-tabs.
  getAdminAssignmentFacets.mockResolvedValue(null);
  fetchOrganizationBranding.mockResolvedValue({ slug: 'clc', name: 'Crane Lake' });
  api.get.mockImplementation(async (url, config) => {
    if (url.includes('/assignment-groups/')) {
      // A group has exactly one type, so only the matching query returns it.
      const results = config?.params?.group_type === 'bunk'
        ? [{
          id: 10,
          name: 'Bunk Maple',
          parent_name: 'Unit A',
          program_name: 'Summer 2026',
        }]
        : [];
      return { data: { results } };
    }
    if (url.includes('/memberships/')) {
      return {
        data: [{
          id: 50,
          role: 'counselor',
          person: 5,
          person_name: 'Sam Lee',
        }],
      };
    }
    return { data: { results: [] } };
  });
});

describe('AdminAssignments', () => {
  it('renders pill sub-tabs and switches between them', async () => {
    render(<AdminAssignments />);
    expect(await screen.findByTestId('assignment-sub-tab-counselor_bunk')).toBeInTheDocument();
    expect(screen.getByTestId('assignment-sub-tab-staff_team')).toBeInTheDocument();
    expect(screen.getByTestId('assignment-sub-tab-uh_unit')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('assignment-sub-tab-uh_unit'));
    await waitFor(() => {
      expect(listAdminAssignments).toHaveBeenCalledWith(
        expect.objectContaining({ sub_tab: 'uh_unit' }),
      );
    });
  });

  it('lists programs in the dropdown with active and ended labels', async () => {
    render(<AdminAssignments />);
    const select = await screen.findByTestId('assignment-program-select');
    await waitFor(() => {
      expect(select).toHaveTextContent('Summer 2026 (Active)');
      expect(select).toHaveTextContent('Summer 2025 (Ended)');
    });
  });

  it('passes filter params when listing assignments', async () => {
    render(<AdminAssignments />);
    const select = await screen.findByTestId('assignment-program-select');
    await waitFor(() => {
      expect(select).toHaveTextContent('Summer 2026 (Active)');
    });

    fireEvent.change(select, { target: { value: '1' } });

    await waitFor(() => {
      expect(listAdminAssignments).toHaveBeenCalledWith(
        expect.objectContaining({ program: '1' }),
      );
      expect(api.get).toHaveBeenCalledWith(
        '/api/v1/assignment-groups/',
        expect.objectContaining({
          params: expect.objectContaining({ program: 'summer-2026' }),
        }),
      );
    }, { timeout: 5000 });
  });

  it('shows assignments empty pane until a group is selected', async () => {
    render(<AdminAssignments />);
    await screen.findByTestId('assignment-group-list');

    expect(screen.getByTestId('assignments-empty-pane')).toBeInTheDocument();
    expect(screen.queryByTestId('assignment-group-tile')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Bunk Maple'));

    expect(screen.queryByTestId('assignments-empty-pane')).not.toBeInTheDocument();
    expect(screen.getByTestId('assignment-group-tile')).toBeInTheDocument();
  });

  it('keeps the selected program while browsing groups', async () => {
    render(<AdminAssignments />);
    const select = await screen.findByTestId('assignment-program-select');
    await waitFor(() => {
      expect(select).toHaveTextContent('Summer 2026 (Active)');
    });
    await screen.findByTestId('assignment-group-list');

    fireEvent.change(select, { target: { value: '1' } });
    await waitFor(() => expect(select).toHaveValue('1'), { timeout: 5000 });

    await screen.findByText('Bunk Maple', undefined, { timeout: 5000 });
    fireEvent.click(screen.getByText('Bunk Maple'));

    expect(select).toHaveValue('1');
  });

  it('hides sub-tabs for relationship shapes the org does not have', async () => {
    // Temple Beth-El's real shape: faculty author for a classroom, madrichim
    // are the subjects in it. Neither role appears in the camp-only tabs.
    getAdminAssignmentFacets.mockResolvedValue({
      roles: ['admin', 'faculty', 'madrich'],
      group_types: ['classroom'],
    });
    api.get.mockImplementation(async (url, config) => {
      if (url.includes('/assignment-groups/')) {
        const results = config?.params?.group_type === 'classroom'
          ? [{ id: 20, name: 'Kitah Alef', program_name: 'Summer 2026' }]
          : [];
        return { data: { results } };
      }
      return { data: { results: [] } };
    });
    render(<AdminAssignments />);

    // The two classroom relationships survive; the camp-only ones do not.
    expect(await screen.findByTestId('assignment-sub-tab-camper_bunk')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByTestId('assignment-sub-tab-uh_unit')).not.toBeInTheDocument();
    });
    expect(screen.getByTestId('assignment-sub-tab-counselor_bunk')).toBeInTheDocument();
    expect(screen.queryByTestId('assignment-sub-tab-staff_team')).not.toBeInTheDocument();
    expect(screen.queryByTestId('assignment-sub-tab-cc_caseload')).not.toBeInTheDocument();
    expect(screen.queryByTestId('assignment-sub-tab-lt_team')).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('assignment-tabs-toggle'));
    expect(screen.getByTestId('assignment-sub-tab-uh_unit')).toBeInTheDocument();
  });

  it("labels sub-tabs with the tenant's own vocabulary", async () => {
    getAdminAssignmentFacets.mockResolvedValue({
      roles: ['admin', 'faculty', 'madrich'],
      group_types: ['classroom'],
    });
    fetchOrganizationBranding.mockResolvedValue({
      slug: 'tbe',
      name: 'Temple Beth-El',
      branding: { display_name: 'Temple Beth-El' },
      terminology: {
        camper: { one: 'student', other: 'students' },
        bunk: { one: 'class', other: 'classes' },
        counselor: { one: 'faculty', other: 'faculty' },
      },
    });
    render(
      <OrgBrandingProvider>
        <AdminAssignments />
      </OrgBrandingProvider>,
    );

    const subjectTab = await screen.findByTestId('assignment-sub-tab-camper_bunk');
    await waitFor(() => expect(subjectTab).toHaveTextContent('Student → Class'));
    expect(subjectTab).toHaveTextContent('Students placed in classes');
    expect(screen.getByTestId('assignment-sub-tab-counselor_bunk'))
      .toHaveTextContent('Faculty → Class');

    // The slug stays canonical even though the noun changed.
    await waitFor(() => {
      expect(listAdminAssignments).toHaveBeenCalledWith(
        expect.objectContaining({ sub_tab: 'counselor_bunk' }),
      );
    });
  });

  it('bulk assign posts once per selected person', async () => {
    createAdminAssignment.mockResolvedValue({ id: 1 });
    render(<AdminAssignments />);
    const select = await screen.findByTestId('assignment-program-select');
    await waitFor(() => {
      expect(select).toHaveTextContent('Summer 2026 (Active)');
    });
    await screen.findByTestId('assignment-group-list');

    fireEvent.change(select, { target: { value: '1' } });
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    fireEvent.click(screen.getByText('Bunk Maple'));
    fireEvent.click(screen.getByTestId('assign-person-5'));
    fireEvent.click(screen.getByTestId('bulk-assign-submit'));

    await waitFor(() => {
      expect(createAdminAssignment).toHaveBeenCalledWith(
        expect.objectContaining({
          sub_tab: 'counselor_bunk',
          group_id: 10,
          person_id: 5,
        }),
      );
    });
  });
});
