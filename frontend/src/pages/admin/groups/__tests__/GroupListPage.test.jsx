/**
 * Groups list — the surface that absorbed Assignments.
 *
 * The value of the merge is that the two things that break a group are
 * visible on its row, so these cover the warning badges, the dashboard's
 * `?warning=` deep link, and developmental (not alphabetical) sort.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../../api', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));
vi.mock('../../../../api/admin', () => ({
  listAdminGroupsOverview: vi.fn(),
}));
vi.mock('../../../../components/admin/GroupBulkImportPanel', () => ({
  default: () => <div data-testid="group-bulk-import" />,
}));

const mockProgram = {
  programId: '1',
  program: { id: 1, name: 'Crane Lake 2026' },
  ready: true,
};
vi.mock('../../../../context/AdminProgramContext', () => ({
  useAdminProgram: () => mockProgram,
}));

import api from '../../../../api';
import { listAdminGroupsOverview } from '../../../../api/admin';
import GroupListPage from '../GroupListPage';

const GROUPS = [
  {
    id: 1, name: 'Bunk Zebra', group_type: 'bunk', parent_name: 'Unit A',
    is_active: true, display_order: 0, subject_count: 8, author_count: 2,
    submitted: 4, expected: 10,
  },
  {
    id: 2, name: 'Bunk Aleph', group_type: 'bunk', parent_name: 'Unit A',
    is_active: true, display_order: 0, subject_count: 6, author_count: 0,
    submitted: 0, expected: 0,
  },
  {
    id: 3, name: 'Unit A', group_type: 'unit', parent_name: null,
    is_active: true, display_order: 0, subject_count: 0, author_count: 3,
    submitted: 0, expected: 0,
  },
  {
    id: 4, name: 'Bunk Empty', group_type: 'bunk', parent_name: null,
    is_active: true, display_order: 0, subject_count: 0, author_count: 1,
    submitted: 0, expected: 0,
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  listAdminGroupsOverview.mockResolvedValue({ results: GROUPS });
  api.get.mockResolvedValue({ data: { results: [] } });
  api.post.mockResolvedValue({ data: { id: 99, name: 'Bunk New' } });
});

function renderList(initialEntries = ['/admin/groups']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <GroupListPage />
    </MemoryRouter>,
  );
}

describe('GroupListPage (Assignments merged in)', () => {
  it('sorts developmentally, not alphabetically, and shows both counts', async () => {
    renderList();
    await screen.findByTestId('group-list-row-1');

    const rows = screen.getAllByTestId(/^group-list-row-/);
    // Unit before its bunks; bunks alphabetical among themselves.
    expect(rows.map((r) => r.dataset.testid)).toEqual([
      'group-list-row-3',
      'group-list-row-2',
      'group-list-row-4',
      'group-list-row-1',
    ]);
    expect(within(rows[3]).getByText(/8 campers · 2 counselors/)).toBeInTheDocument();
  });

  it('flags a group with no author and one with no subjects', async () => {
    renderList();
    await screen.findByTestId('group-list-row-1');

    expect(screen.getByTestId('group-warning-no-author-2')).toBeInTheDocument();
    expect(screen.getByTestId('group-warning-no-subjects-4')).toBeInTheDocument();
    // A unit holds no subjects by design, so it isn't flagged for having none.
    expect(screen.queryByTestId('group-warning-no-subjects-3')).toBeNull();
  });

  it('narrows to the broken groups when the dashboard deep-links ?warning=', async () => {
    renderList(['/admin/groups?warning=no_author']);
    await screen.findByTestId('group-list-row-2');

    expect(screen.getAllByTestId(/^group-list-row-/)).toHaveLength(1);
    expect(screen.queryByTestId('group-list-attention')).toBeNull();

    fireEvent.click(screen.getByTestId('group-clear-warning-filter'));
    await waitFor(() => {
      expect(screen.getAllByTestId(/^group-list-row-/)).toHaveLength(4);
    });
  });

  it('offers the same narrowing from the attention banner', async () => {
    renderList();
    await screen.findByTestId('group-list-attention');

    fireEvent.click(screen.getByTestId('group-filter-no-subjects'));
    await waitFor(() => {
      expect(screen.getAllByTestId(/^group-list-row-/)).toHaveLength(1);
    });
    expect(screen.getByTestId('group-list-row-4')).toBeInTheDocument();
  });

  it('searches by name without another round trip', async () => {
    renderList();
    await screen.findByTestId('group-list-row-1');
    listAdminGroupsOverview.mockClear();

    fireEvent.change(screen.getByTestId('group-search'), { target: { value: 'aleph' } });
    await waitFor(() => {
      expect(screen.getAllByTestId(/^group-list-row-/)).toHaveLength(1);
    });
    expect(listAdminGroupsOverview).not.toHaveBeenCalled();
  });
});
