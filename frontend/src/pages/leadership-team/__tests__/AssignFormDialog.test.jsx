import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import AssignFormDialog from '../AssignFormDialog';

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'test-org' }),
}));

vi.mock('../../../api/leadershipTeam', () => ({
  createAssignment: vi.fn(),
  listAssignmentGroups: vi.fn(),
}));

import { createAssignment, listAssignmentGroups } from '../../../api/leadershipTeam';

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const summerProgramId = 1;

const template = {
  id: 7,
  name: 'Daily Bunk Log',
  version: 1,
  status: 'published',
};

const groups = [
  {
    id: 3, name: 'Bunk Birch', group_type: 'bunk', program: summerProgramId,
    program_name: 'Summer 2026', is_active: true,
  },
  {
    id: 4, name: 'Bunk Oak', group_type: 'bunk', program: summerProgramId,
    program_name: 'Summer 2026', is_active: true,
  },
];

const newAssignment = {
  id: 42,
  template: 7,
  template_slug: 'daily-bunk-log',
  target_type: 'assignment_group',
  assignment_group: 3,
  assignment_group_name: 'Bunk Birch',
  is_required: true,
  display_title: 'Daily Bunk Log',
  start_date: '2026-05-28',
  end_date: null,
  status: 'scheduled',
};

function makeConflictError(conflicts) {
  const err = new Error('conflict');
  err.response = {
    status: 409,
    data: {
      detail: 'Assignment conflict requires conflict_resolution.',
      conflicts,
      choices: ['replace', 'run_both', 'cancel'],
    },
  };
  return err;
}

function make400Error(detail) {
  const err = new Error('bad request');
  err.response = { status: 400, data: { detail } };
  return err;
}

function selectGroupFilters(programId = summerProgramId, groupType = 'bunk') {
  fireEvent.change(screen.getByTestId('assign-form-program-filter'), {
    target: { value: String(programId) },
  });
  fireEvent.change(screen.getByTestId('assign-form-group-type-filter'), {
    target: { value: groupType },
  });
}

async function waitForGroupList() {
  await waitFor(() => expect(screen.getByTestId('assign-form-program-filter')).toBeInTheDocument());
  selectGroupFilters();
  await waitFor(() => expect(screen.getByTestId('assign-form-group-list')).toBeInTheDocument());
}

function selectGroup(id) {
  fireEvent.click(screen.getByTestId(`assign-form-group-${id}`));
}

function renderDialog({ onClose = vi.fn(), onCreated = vi.fn() } = {}) {
  return render(
    <AssignFormDialog template={template} onClose={onClose} onCreated={onCreated} />,
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('AssignFormDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAssignmentGroups.mockResolvedValue(groups);
  });

  it('renders all required fields', async () => {
    renderDialog();
    expect(screen.getByTestId('assign-form-target-assignment_group')).toBeInTheDocument();
    expect(screen.getByTestId('assign-form-target-role')).toBeInTheDocument();
    expect(screen.getByTestId('assign-form-target-tag_group')).toBeInTheDocument();
    expect(screen.getByTestId('assign-form-target-individuals')).toBeDisabled();
    expect(screen.getByTestId('assign-form-title')).toBeInTheDocument();
    expect(screen.getByTestId('assign-form-required')).toBeInTheDocument();
    expect(screen.getByTestId('assign-form-start-date')).toBeInTheDocument();
    expect(screen.getByTestId('assign-form-end-date')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('assign-form-program-filter')).toBeInTheDocument());
    expect(screen.getByTestId('assign-form-groups-filter-hint')).toBeInTheDocument();
  });

  it('builds the correct POST payload on submit', async () => {
    createAssignment.mockResolvedValue(newAssignment);
    const onCreated = vi.fn();
    const onClose = vi.fn();
    renderDialog({ onCreated, onClose });

    await waitForGroupList();
    selectGroup(3);
    fireEvent.change(screen.getByTestId('assign-form-title'), { target: { value: 'My Title' } });
    fireEvent.click(screen.getByTestId('assign-form-required'));
    fireEvent.change(screen.getByTestId('assign-form-start-date'), {
      target: { value: '2026-06-01' },
    });
    fireEvent.click(screen.getByTestId('assign-form-submit'));

    await waitFor(() => expect(createAssignment).toHaveBeenCalledOnce());
    const payload = createAssignment.mock.calls[0][1];
    expect(payload.template).toBe(7);
    expect(payload.target_type).toBe('assignment_group');
    expect(payload.assignment_group).toBe(3);
    expect(payload.title).toBe('My Title');
    expect(payload.is_required).toBe(false);
    expect(payload.start_date).toBe('2026-06-01');

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(newAssignment));
    expect(onClose).toHaveBeenCalled();
  });

  it('creates one assignment per checked group', async () => {
    createAssignment.mockImplementation((_org, body) => Promise.resolve({
      ...newAssignment,
      id: body.assignment_group,
      assignment_group: body.assignment_group,
    }));
    const onCreated = vi.fn();
    const onClose = vi.fn();
    renderDialog({ onCreated, onClose });

    await waitForGroupList();
    selectGroup(3);
    selectGroup(4);
    expect(screen.getByTestId('assign-form-submit')).toHaveTextContent('Assign to 2 groups');
    fireEvent.click(screen.getByTestId('assign-form-submit'));

    await waitFor(() => expect(createAssignment).toHaveBeenCalledTimes(2));
    const groupIds = createAssignment.mock.calls.map(([, body]) => body.assignment_group);
    expect(groupIds).toEqual(expect.arrayContaining([3, 4]));
    expect(onCreated).toHaveBeenCalledTimes(2);
    expect(onClose).toHaveBeenCalled();
  });

  it('shows inline conflict resolution on 409 and re-submits with chosen resolution', async () => {
    const conflictAssignment = {
      id: 10,
      display_title: 'Old Log',
      title: 'Old Log',
      start_date: '2026-01-01',
      end_date: null,
      assignment_group_name: 'Bunk Birch',
    };
    createAssignment
      .mockRejectedValueOnce(makeConflictError([conflictAssignment]))
      .mockResolvedValueOnce(newAssignment);
    const onCreated = vi.fn();
    renderDialog({ onCreated });

    await waitForGroupList();
    selectGroup(3);
    fireEvent.click(screen.getByTestId('assign-form-submit'));

    await waitFor(() => expect(screen.getByTestId('assign-form-conflicts')).toBeInTheDocument());
    expect(screen.getByTestId('conflict-item-10')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('conflict-choice-replace'));
    fireEvent.click(screen.getByTestId('assign-form-submit'));

    await waitFor(() => expect(createAssignment).toHaveBeenCalledTimes(2));
    const secondCall = createAssignment.mock.calls[1][1];
    expect(secondCall.conflict_resolution).toBe('replace');
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(newAssignment));
  });

  it('shows the scored-camper guard callout on 400 with matching error text', async () => {
    createAssignment.mockRejectedValueOnce(
      make400Error(
        "This bunk already has an active scored camper form ('Daily Log') for an overlapping date range.",
      ),
    );
    renderDialog();

    await waitForGroupList();
    selectGroup(3);
    fireEvent.click(screen.getByTestId('assign-form-submit'));

    await waitFor(() =>
      expect(screen.getByTestId('assign-form-scored-camper-error')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('assign-form-scored-camper-error')).toHaveTextContent(
      'scored camper form',
    );
  });

  it('validates end_date >= start_date client-side and shows error before submitting', async () => {
    renderDialog();
    await waitForGroupList();
    selectGroup(3);
    fireEvent.change(screen.getByTestId('assign-form-start-date'), {
      target: { value: '2026-08-01' },
    });
    fireEvent.change(screen.getByTestId('assign-form-end-date'), {
      target: { value: '2026-07-01' },
    });
    fireEvent.click(screen.getByTestId('assign-form-submit'));

    await waitFor(() =>
      expect(screen.getByTestId('assign-form-date-error')).toBeInTheDocument(),
    );
    expect(createAssignment).not.toHaveBeenCalled();
  });

  it('requires at least one group before submitting', async () => {
    renderDialog();
    fireEvent.click(screen.getByTestId('assign-form-submit'));
    await waitFor(() => expect(screen.getByTestId('assign-form-error')).toBeInTheDocument());
    expect(screen.getByTestId('assign-form-error')).toHaveTextContent(/at least one group/i);
    expect(createAssignment).not.toHaveBeenCalled();
  });

  it('shows a role picker when Role target type is selected', async () => {
    renderDialog();
    fireEvent.click(screen.getByTestId('assign-form-target-role'));
    expect(screen.getByTestId('assign-form-role')).toBeInTheDocument();
    expect(screen.queryByTestId('assign-form-group-list')).not.toBeInTheDocument();
  });

  it('shows a tag input when Tag group target type is selected', async () => {
    renderDialog();
    fireEvent.click(screen.getByTestId('assign-form-target-tag_group'));
    expect(screen.getByTestId('assign-form-tag')).toBeInTheDocument();
    expect(screen.queryByTestId('assign-form-group-list')).not.toBeInTheDocument();
  });

  it('shows cadence override when Advanced section is expanded', async () => {
    renderDialog();
    expect(screen.queryByTestId('assign-form-cadence')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('assign-form-advanced-toggle'));
    expect(screen.getByTestId('assign-form-cadence')).toBeInTheDocument();
  });

  it('program and group type filters narrow the visible list', async () => {
    listAssignmentGroups.mockResolvedValue([
      {
        id: 11, name: 'Bunk Birch', group_type: 'bunk', program: summerProgramId,
        program_name: 'Summer 2026', is_active: true,
      },
      {
        id: 20, name: 'Unit Maple', group_type: 'unit', program: summerProgramId,
        program_name: 'Summer 2026', is_active: true,
      },
      {
        id: 30, name: 'Fall Bunk', group_type: 'bunk', program: 2,
        program_name: 'Fall 2026', is_active: true,
      },
    ]);
    renderDialog();

    await waitFor(() => expect(screen.getByTestId('assign-form-program-filter')).toBeInTheDocument());
    selectGroupFilters(summerProgramId, 'bunk');
    await waitFor(() => expect(screen.getByTestId('assign-form-group-11')).toBeInTheDocument());
    expect(screen.queryByTestId('assign-form-group-20')).not.toBeInTheDocument();
    expect(screen.queryByTestId('assign-form-group-30')).not.toBeInTheDocument();

    fireEvent.change(screen.getByTestId('assign-form-group-type-filter'), {
      target: { value: 'unit' },
    });
    expect(screen.queryByTestId('assign-form-group-11')).not.toBeInTheDocument();
    expect(screen.getByTestId('assign-form-group-20')).toBeInTheDocument();
  });

  it('select all checks every visible group', async () => {
    renderDialog();
    await waitForGroupList();
    fireEvent.click(screen.getByTestId('assign-form-group-select-all'));
    expect(screen.getByTestId('assign-form-group-3')).toBeChecked();
    expect(screen.getByTestId('assign-form-group-4')).toBeChecked();
    expect(screen.getByTestId('assign-form-groups-selected-count')).toHaveTextContent('2 groups selected');
  });
});
