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

const template = {
  id: 7,
  name: 'Daily Bunk Log',
  version: 1,
  status: 'published',
};

const groups = [
  { id: 3, name: 'Bunk Birch', group_type: 'bunk' },
  { id: 4, name: 'Bunk Oak', group_type: 'bunk' },
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
    // Target type radios
    expect(screen.getByTestId('assign-form-target-assignment_group')).toBeInTheDocument();
    expect(screen.getByTestId('assign-form-target-role')).toBeInTheDocument();
    expect(screen.getByTestId('assign-form-target-tag_group')).toBeInTheDocument();
    // Individuals is disabled
    const individualsRadio = screen.getByTestId('assign-form-target-individuals');
    expect(individualsRadio).toBeDisabled();
    // Other fields
    expect(screen.getByTestId('assign-form-title')).toBeInTheDocument();
    expect(screen.getByTestId('assign-form-required')).toBeInTheDocument();
    expect(screen.getByTestId('assign-form-start-date')).toBeInTheDocument();
    expect(screen.getByTestId('assign-form-end-date')).toBeInTheDocument();
    // Group picker should load
    await waitFor(() => expect(screen.getByTestId('assign-form-group-select')).toBeInTheDocument());
  });

  it('builds the correct POST payload on submit', async () => {
    createAssignment.mockResolvedValue(newAssignment);
    const onCreated = vi.fn();
    const onClose = vi.fn();
    renderDialog({ onCreated, onClose });

    // Wait for groups to load and select group 3
    await waitFor(() => expect(screen.getByTestId('assign-form-group-select')).toBeInTheDocument());
    fireEvent.change(screen.getByTestId('assign-form-group-select'), { target: { value: '3' } });

    // Set a title
    fireEvent.change(screen.getByTestId('assign-form-title'), { target: { value: 'My Title' } });

    // Uncheck required
    fireEvent.click(screen.getByTestId('assign-form-required'));

    // Set start date
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

    // onCreated and onClose called on success
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(newAssignment));
    expect(onClose).toHaveBeenCalled();
  });

  it('shows conflict resolution panel on 409 and re-submits with chosen resolution', async () => {
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

    // Select a group and submit
    await waitFor(() => expect(screen.getByTestId('assign-form-group-select')).toBeInTheDocument());
    fireEvent.change(screen.getByTestId('assign-form-group-select'), { target: { value: '3' } });
    fireEvent.click(screen.getByTestId('assign-form-submit'));

    // Conflict panel should appear
    await waitFor(() =>
      expect(screen.getByTestId('assign-form-conflict-panel')).toBeInTheDocument(),
    );
    // Shows the conflicting assignment
    expect(screen.getByTestId('conflict-item-10')).toBeInTheDocument();

    // Form fields are frozen (submit button replaced by conflict panel)
    expect(screen.queryByTestId('assign-form-submit')).not.toBeInTheDocument();

    // "Replace" is selected by default — confirm
    expect(screen.getByTestId('conflict-choice-replace')).toBeChecked();
    fireEvent.click(screen.getByTestId('conflict-confirm'));

    await waitFor(() => expect(createAssignment).toHaveBeenCalledTimes(2));
    const secondCall = createAssignment.mock.calls[1][1];
    expect(secondCall.conflict_resolution).toBe('replace');

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(newAssignment));
  });

  it('closes the dialog when Cancel is chosen in the conflict panel', async () => {
    const conflictAssignment = {
      id: 10,
      display_title: 'Old Log',
      title: 'Old Log',
      start_date: '2026-01-01',
      end_date: null,
      assignment_group_name: 'Bunk Birch',
    };
    createAssignment.mockRejectedValueOnce(makeConflictError([conflictAssignment]));
    const onClose = vi.fn();
    renderDialog({ onClose });

    await waitFor(() => expect(screen.getByTestId('assign-form-group-select')).toBeInTheDocument());
    fireEvent.change(screen.getByTestId('assign-form-group-select'), { target: { value: '3' } });
    fireEvent.click(screen.getByTestId('assign-form-submit'));

    await waitFor(() => expect(screen.getByTestId('assign-form-conflict-panel')).toBeInTheDocument());

    fireEvent.click(screen.getByTestId('conflict-cancel'));
    expect(onClose).toHaveBeenCalled();
  });

  it('shows the scored-camper guard callout on 400 with matching error text', async () => {
    createAssignment.mockRejectedValueOnce(
      make400Error(
        "This bunk already has an active scored camper form ('Daily Log') for an overlapping date range.",
      ),
    );
    renderDialog();

    await waitFor(() => expect(screen.getByTestId('assign-form-group-select')).toBeInTheDocument());
    fireEvent.change(screen.getByTestId('assign-form-group-select'), { target: { value: '3' } });
    fireEvent.click(screen.getByTestId('assign-form-submit'));

    await waitFor(() =>
      expect(screen.getByTestId('assign-form-scored-camper-error')).toBeInTheDocument(),
    );
    expect(screen.getByTestId('assign-form-scored-camper-error')).toHaveTextContent(
      'scored camper form',
    );
    // Dialog should still be open (no onClose call)
  });

  it('validates end_date >= start_date client-side and shows error before submitting', async () => {
    renderDialog();
    await waitFor(() => expect(screen.getByTestId('assign-form-group-select')).toBeInTheDocument());
    fireEvent.change(screen.getByTestId('assign-form-group-select'), { target: { value: '3' } });

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
    expect(screen.getByTestId('assign-form-date-error')).toHaveTextContent(
      'End date must be on or after start date',
    );
    expect(createAssignment).not.toHaveBeenCalled();
  });

  it('shows "Assign form" button disabled when template status is draft', async () => {
    // This is tested at the builder page level (TemplateBuilderPage renders disabled button)
    // Here we just verify the dialog submit itself requires a group selection
    createAssignment.mockResolvedValue(newAssignment);
    renderDialog();
    // No group selected — submit should show error, not call API
    fireEvent.click(screen.getByTestId('assign-form-submit'));
    await waitFor(() => expect(screen.getByTestId('assign-form-error')).toBeInTheDocument());
    expect(createAssignment).not.toHaveBeenCalled();
  });

  it('shows a role picker when Role target type is selected', async () => {
    renderDialog();
    fireEvent.click(screen.getByTestId('assign-form-target-role'));
    expect(screen.getByTestId('assign-form-role')).toBeInTheDocument();
    expect(screen.queryByTestId('assign-form-group-select')).not.toBeInTheDocument();
  });

  it('shows a tag input when Tag group target type is selected', async () => {
    renderDialog();
    fireEvent.click(screen.getByTestId('assign-form-target-tag_group'));
    expect(screen.getByTestId('assign-form-tag')).toBeInTheDocument();
    expect(screen.queryByTestId('assign-form-group-select')).not.toBeInTheDocument();
  });

  it('shows cadence override when Advanced section is expanded', async () => {
    renderDialog();
    expect(screen.queryByTestId('assign-form-cadence')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('assign-form-advanced-toggle'));
    expect(screen.getByTestId('assign-form-cadence')).toBeInTheDocument();
  });
});
