/**
 * Group detail — Members / Staff / Supervision / Settings.
 *
 * Covers the three things the merge changed: the roster is split into
 * two tabs by role, removing people is guarded and reversible, and the
 * Supervision tab only exists for orgs that actually supervise.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

vi.mock('../../../../api', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));
vi.mock('../../../../api/admin', () => ({
  getAdminAssignmentFacets: vi.fn(),
  listAdminAssignments: vi.fn(),
  createAdminAssignment: vi.fn(),
  patchAdminAssignment: vi.fn(),
  listAdminPeople: vi.fn(),
  listAdminPrograms: vi.fn(),
}));

import api from '../../../../api';
import {
  getAdminAssignmentFacets,
  listAdminAssignments,
  listAdminPeople,
  listAdminPrograms,
} from '../../../../api/admin';
import GroupDetailPage from '../GroupDetailPage';

const GROUP = {
  id: 7,
  name: 'Bunk Aleph',
  slug: 'bunk-aleph',
  group_type: 'bunk',
  program: 1,
  program_name: 'Crane Lake 2026',
  parent_id: 3,
  parent_name: 'Unit A',
  display_order: 0,
  is_active: true,
  memberships: [
    {
      id: 11,
      person: { id: 101, first_name: 'Ada', last_name: 'Byron', preferred_name: '' },
      role_in_group: 'subject',
      is_active: true,
      start_date: '2026-06-20',
    },
    {
      id: 12,
      person: { id: 102, first_name: 'Grace', last_name: 'Hopper', preferred_name: '' },
      role_in_group: 'author',
      is_active: true,
      start_date: '2026-06-20',
    },
    {
      id: 13,
      person: { id: 103, first_name: 'Old', last_name: 'Camper', preferred_name: '' },
      role_in_group: 'subject',
      is_active: false,
      start_date: '2025-06-20',
    },
  ],
};

function mockGroup(overrides = {}) {
  api.get.mockImplementation((url) => {
    if (String(url).includes('/assignment-groups/7/')) {
      return Promise.resolve({ data: { ...GROUP, ...overrides } });
    }
    return Promise.resolve({ data: { results: [] } });
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  mockGroup();
  api.post.mockResolvedValue({ data: {} });
  api.patch.mockResolvedValue({ data: {} });
  api.delete.mockResolvedValue({ data: {} });
  getAdminAssignmentFacets.mockResolvedValue({ roles: ['camper_care', 'unit_head'] });
  listAdminAssignments.mockResolvedValue({ results: [] });
  listAdminPeople.mockResolvedValue({ results: [] });
  listAdminPrograms.mockResolvedValue({ results: [] });
});

function renderDetail(entry = '/admin/groups/7') {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/admin/groups/:id" element={<GroupDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('GroupDetailPage', () => {
  it('splits the roster by role and hides ended memberships', async () => {
    renderDetail();
    await screen.findByTestId('group-roster-subject');

    expect(screen.getByText('Ada Byron')).toBeInTheDocument();
    expect(screen.queryByText('Grace Hopper')).toBeNull();
    expect(screen.queryByText('Old Camper')).toBeNull();

    fireEvent.click(screen.getByTestId('group-tab-staff'));
    expect(await screen.findByText('Grace Hopper')).toBeInTheDocument();
    expect(screen.queryByText('Ada Byron')).toBeNull();
  });

  it('names the group and where it sits without exposing the slug', async () => {
    renderDetail();
    await screen.findByTestId('group-roster-subject');

    expect(screen.getByRole('heading', { name: 'Bunk Aleph' })).toBeInTheDocument();
    expect(screen.getByText(/part of Unit A/)).toBeInTheDocument();
    expect(screen.queryByText('bunk-aleph')).toBeNull();
  });

  it('confirms a removal by name and count before ending the membership', async () => {
    renderDetail();
    await screen.findByTestId('group-roster-subject');

    fireEvent.click(screen.getByLabelText('Select row 11'));
    fireEvent.click(screen.getByTestId('group-subject-overflow'));
    fireEvent.click(screen.getByTestId('group-subject-remove'));

    expect(await screen.findByText(/Remove 1 camper from Bunk Aleph\?/)).toBeInTheDocument();
    expect(screen.getByText(/Logs already written stay exactly where they are/)).toBeInTheDocument();
    expect(api.delete).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('confirm-dialog-confirm'));
    await waitFor(() => expect(api.delete).toHaveBeenCalledTimes(1));
    expect(api.delete.mock.calls[0][0]).toContain('/assignment-groups/7/memberships/11/');
  });

  it('offers Supervision for a bunk when the org has camper care', async () => {
    renderDetail();
    await screen.findByTestId('group-roster-subject');
    await waitFor(() => expect(screen.getByTestId('group-tab-supervision')).toBeInTheDocument());
  });

  it('omits Supervision when the org has no camper care role', async () => {
    getAdminAssignmentFacets.mockResolvedValue({ roles: ['teacher', 'admin'] });
    renderDetail();
    await screen.findByTestId('group-roster-subject');

    await waitFor(() => {
      expect(screen.getByTestId('group-tab-settings')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('group-tab-supervision')).toBeNull();
  });

  it('keeps archiving in the Settings danger zone behind a confirmation', async () => {
    renderDetail('/admin/groups/7?tab=settings');
    await screen.findByTestId('group-settings-tab');

    fireEvent.click(screen.getByTestId('group-archive'));
    expect(await screen.findByText('Archive Bunk Aleph?')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('confirm-dialog-confirm'));
    await waitFor(() => {
      const archiveCall = api.patch.mock.calls.find(
        ([url, body]) => String(url).includes('/assignment-groups/7/') && body.is_active === false,
      );
      expect(archiveCall).toBeTruthy();
    });
  });

  it('saves "Part of" and sort position from Settings', async () => {
    api.get.mockImplementation((url) => {
      if (String(url).includes('/assignment-groups/7/')) return Promise.resolve({ data: GROUP });
      if (String(url).includes('/assignment-groups/')) {
        return Promise.resolve({ data: { results: [{ id: 3, name: 'Unit A', group_type: 'unit' }] } });
      }
      return Promise.resolve({ data: { results: [] } });
    });
    renderDetail('/admin/groups/7?tab=settings');
    await screen.findByTestId('group-settings-tab');

    fireEvent.change(screen.getByTestId('group-settings-order'), { target: { value: '3' } });
    fireEvent.click(screen.getByTestId('group-settings-save'));

    await waitFor(() => {
      const saveCall = api.patch.mock.calls.find(([, body]) => body.display_order === 3);
      expect(saveCall).toBeTruthy();
      expect(saveCall[1]).toMatchObject({ name: 'Bunk Aleph', parent: 3, display_order: 3 });
    });
  });
});
