import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import AssignmentList from '../AssignmentList';

// ─── Mock the leadershipTeam API ─────────────────────────────────────────────

vi.mock('../../../api/leadershipTeam', () => ({
  listAssignments: vi.fn(),
  cancelAssignment: vi.fn(),
  patchAssignment: vi.fn(),
}));

import { cancelAssignment, listAssignments, patchAssignment } from '../../../api/leadershipTeam';

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const activeRow = {
  id: 1,
  display_title: 'Daily Bunk Log',
  title: 'Daily Bunk Log',
  target_type: 'assignment_group',
  target_payload: {},
  assignment_group: 3,
  assignment_group_name: 'Bunk Birch',
  is_required: true,
  start_date: '2026-06-01',
  end_date: null,
  status: 'active',
};

const scheduledRow = {
  id: 2,
  display_title: 'Weekly Check-in',
  title: 'Weekly Check-in',
  target_type: 'role',
  target_payload: { role: 'counselor' },
  assignment_group: null,
  assignment_group_name: null,
  is_required: false,
  start_date: '2026-07-01',
  end_date: '2026-08-31',
  status: 'scheduled',
};

const endedRow = {
  id: 3,
  display_title: 'Old Form',
  title: 'Old Form',
  target_type: 'assignment_group',
  target_payload: {},
  assignment_group: 5,
  assignment_group_name: 'Bunk Oak',
  is_required: true,
  start_date: '2026-01-01',
  end_date: '2026-05-31',
  status: 'ended',
};

const cancelledRow = {
  id: 4,
  display_title: 'Cancelled Form',
  title: 'Cancelled Form',
  target_type: 'role',
  target_payload: { role: 'unit_head' },
  assignment_group: null,
  assignment_group_name: null,
  is_required: true,
  start_date: '2026-06-01',
  end_date: null,
  status: 'cancelled',
};

function renderList({ templateId = 7, orgSlug = 'test-org', refreshKey = 0 } = {}) {
  return render(
    <AssignmentList templateId={templateId} orgSlug={orgSlug} refreshKey={refreshKey} />,
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('AssignmentList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: suppress window.confirm so actions don't block
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  afterEach(() => {
    window.confirm.mockRestore?.();
  });

  it('renders existing assignments with correct labels, status badges, and actions', async () => {
    listAssignments.mockResolvedValue({
      assignments: [activeRow, scheduledRow, endedRow, cancelledRow],
    });
    renderList();

    await waitFor(() => expect(screen.queryByTestId('assignment-list-skeleton')).not.toBeInTheDocument());

    // Active row
    expect(screen.getByTestId('assignment-row-1')).toBeInTheDocument();
    expect(screen.getByTestId('assignment-status-active')).toBeInTheDocument();
    expect(screen.getByTestId('assignment-target-1')).toHaveTextContent('Bunk Birch');
    expect(screen.getByTestId('assignment-dates-1')).toHaveTextContent('ongoing');
    expect(screen.getByTestId('assignment-required-1')).toHaveTextContent('Required');
    expect(screen.getByTestId('assignment-end-today-1')).toBeInTheDocument();
    expect(screen.queryByTestId('assignment-cancel-1')).not.toBeInTheDocument();

    // Scheduled row
    expect(screen.getByTestId('assignment-status-scheduled')).toBeInTheDocument();
    expect(screen.getByTestId('assignment-target-2')).toHaveTextContent('Role: counselor');
    expect(screen.getByTestId('assignment-required-2')).toHaveTextContent('Optional');
    expect(screen.getByTestId('assignment-cancel-2')).toBeInTheDocument();
    expect(screen.queryByTestId('assignment-end-today-2')).not.toBeInTheDocument();

    // Ended row — no actions
    expect(screen.queryByTestId('assignment-cancel-3')).not.toBeInTheDocument();
    expect(screen.queryByTestId('assignment-end-today-3')).not.toBeInTheDocument();

    // Cancelled row — no actions
    expect(screen.queryByTestId('assignment-cancel-4')).not.toBeInTheDocument();
    expect(screen.queryByTestId('assignment-end-today-4')).not.toBeInTheDocument();
  });

  it('shows empty state when the list is empty', async () => {
    listAssignments.mockResolvedValue({ assignments: [] });
    renderList();

    await waitFor(() =>
      expect(screen.getByTestId('assignment-list-empty')).toBeInTheDocument(),
    );
    expect(screen.queryByTestId('assignment-list')).not.toBeInTheDocument();
  });

  it('hides Cancel/End buttons for ended and cancelled rows', async () => {
    listAssignments.mockResolvedValue({ assignments: [endedRow, cancelledRow] });
    renderList();

    await waitFor(() => expect(screen.queryByTestId('assignment-list-skeleton')).not.toBeInTheDocument());
    expect(screen.queryByTestId('assignment-cancel-3')).not.toBeInTheDocument();
    expect(screen.queryByTestId('assignment-end-today-3')).not.toBeInTheDocument();
    expect(screen.queryByTestId('assignment-cancel-4')).not.toBeInTheDocument();
    expect(screen.queryByTestId('assignment-end-today-4')).not.toBeInTheDocument();
  });

  it('shows loading skeleton while fetching', () => {
    // Never resolve
    listAssignments.mockReturnValue(new Promise(() => {}));
    renderList();
    expect(screen.getByTestId('assignment-list-skeleton')).toBeInTheDocument();
  });

  it('shows inline error if the fetch fails', async () => {
    listAssignments.mockRejectedValue(new Error('network error'));
    renderList();
    await waitFor(() => expect(screen.getByTestId('assignment-list-error')).toBeInTheDocument());
  });

  it('calls cancelAssignment and refreshes when Cancel is confirmed', async () => {
    listAssignments
      .mockResolvedValueOnce({ assignments: [scheduledRow] })
      .mockResolvedValueOnce({ assignments: [] });
    cancelAssignment.mockResolvedValue(undefined);

    renderList();
    await waitFor(() => expect(screen.getByTestId('assignment-cancel-2')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('assignment-cancel-2'));
    await waitFor(() => expect(cancelAssignment).toHaveBeenCalledWith('test-org', scheduledRow.id));
    // After refresh the list should be empty
    await waitFor(() => expect(screen.getByTestId('assignment-list-empty')).toBeInTheDocument());
  });

  it('calls patchAssignment with today and refreshes when End today is confirmed', async () => {
    listAssignments
      .mockResolvedValueOnce({ assignments: [activeRow] })
      .mockResolvedValueOnce({ assignments: [] });
    patchAssignment.mockResolvedValue({});

    renderList();
    await waitFor(() => expect(screen.getByTestId('assignment-end-today-1')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('assignment-end-today-1'));
    await waitFor(() => {
      expect(patchAssignment).toHaveBeenCalledWith(
        'test-org',
        activeRow.id,
        expect.objectContaining({ end_date: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/) }),
      );
    });
    await waitFor(() => expect(screen.getByTestId('assignment-list-empty')).toBeInTheDocument());
  });
});
