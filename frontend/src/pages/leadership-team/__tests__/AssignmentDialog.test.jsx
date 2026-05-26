import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import AssignmentDialog from '../AssignmentDialog';

const postMock = vi.fn();
const getMock = vi.fn();
const patchMock = vi.fn();
const deleteMock = vi.fn();
vi.mock('../../../api', () => ({
  default: {
    post: (...args) => postMock(...args),
    get: (...args) => getMock(...args),
    patch: (...args) => patchMock(...args),
    delete: (...args) => deleteMock(...args),
  },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'test-org' }),
}));

beforeEach(() => {
  postMock.mockReset();
  getMock.mockReset();
  patchMock.mockReset();
  deleteMock.mockReset();
  // The dialog now fetches existing assignments on mount; default to empty
  // so per-test setups only override when they need rows.
  getMock.mockResolvedValue({ data: { assignments: [] } });
});

const template = {
  id: 9,
  name: 'Kitchen weekly',
  version: 2,
  role: 'kitchen_staff',
  subject_mode: 'self',
  assignment_scope: 'none',
  assignment_group_types: [],
};

describe('AssignmentDialog', () => {
  it('submits a role-targeted assignment and calls onCreated', async () => {
    postMock.mockResolvedValue({ data: { id: 1, target_type: 'role' } });
    const onCreated = vi.fn();
    const onClose = vi.fn();
    render(<AssignmentDialog template={template} onClose={onClose} onCreated={onCreated} />);

    fireEvent.change(screen.getByTestId('lt-assignment-start'), {
      target: { value: '2026-07-12' },
    });
    fireEvent.click(screen.getByTestId('lt-assignment-submit'));
    await waitFor(() => expect(onCreated).toHaveBeenCalled());
    expect(postMock).toHaveBeenCalledTimes(1);
    const [, body] = postMock.mock.calls[0];
    expect(body.target_type).toBe('role');
    expect(body.target_payload).toEqual({ role: 'kitchen_staff' });
    // is_required defaults to true and is always included in the payload.
    expect(body.is_required).toBe(true);
  });

  it('shows template-level config badges (subject_mode, scope, group types)', () => {
    const richTemplate = {
      ...template,
      subject_mode: 'single_subject',
      assignment_scope: 'per_subject_in_group',
      assignment_group_types: ['bunk', 'unit'],
    };
    render(<AssignmentDialog template={richTemplate} onClose={() => {}} onCreated={() => {}} />);
    expect(screen.getByTestId('lt-assignment-subject-mode-badge')).toHaveTextContent('Single subject');
    expect(screen.getByTestId('lt-assignment-scope-badge')).toHaveTextContent('Per-subject in group');
    expect(screen.getByTestId('lt-assignment-group-type-badge-bunk')).toHaveTextContent('Bunk');
    expect(screen.getByTestId('lt-assignment-group-type-badge-unit')).toHaveTextContent('Unit');
    // scope='none' badge is hidden (not rendered)
    expect(screen.queryByTestId('lt-assignment-scope-badge')).toBeInTheDocument();
  });

  it('hides scope badge when assignment_scope is none', () => {
    render(<AssignmentDialog template={template} onClose={() => {}} onCreated={() => {}} />);
    // subject_mode='self' → scope='none' → scope badge not rendered
    expect(screen.queryByTestId('lt-assignment-scope-badge')).not.toBeInTheDocument();
  });

  it('includes title and is_required in the POST payload when set', async () => {
    postMock.mockResolvedValue({ data: { id: 2, target_type: 'role' } });
    render(<AssignmentDialog template={template} onClose={() => {}} onCreated={() => {}} />);

    fireEvent.change(screen.getByTestId('lt-assignment-title'), {
      target: { value: 'Weekly kitchen check-in' },
    });
    // Uncheck is_required to send false.
    fireEvent.click(screen.getByTestId('lt-assignment-is-required'));
    fireEvent.change(screen.getByTestId('lt-assignment-start'), {
      target: { value: '2026-07-01' },
    });
    fireEvent.click(screen.getByTestId('lt-assignment-submit'));

    await waitFor(() => expect(postMock).toHaveBeenCalledTimes(1));
    const [, body] = postMock.mock.calls[0];
    expect(body.title).toBe('Weekly kitchen check-in');
    expect(body.is_required).toBe(false);
  });

  it('renders the conflict picker and resubmits with conflict_resolution=replace', async () => {
    postMock.mockRejectedValueOnce({
      response: {
        status: 409,
        data: {
          detail: 'Assignment conflict requires conflict_resolution.',
          conflicts: [{ id: 99, start_date: '2026-06-01', end_date: null, target_type: 'role' }],
        },
      },
    });
    postMock.mockResolvedValueOnce({ data: { id: 12 } });
    const onCreated = vi.fn();
    render(<AssignmentDialog template={template} onCreated={onCreated} onClose={() => {}} />);
    fireEvent.change(screen.getByTestId('lt-assignment-start'), {
      target: { value: '2026-07-12' },
    });
    fireEvent.click(screen.getByTestId('lt-assignment-submit'));
    await waitFor(() => expect(screen.getByTestId('lt-assignment-conflicts')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('lt-conflict-replace'));
    fireEvent.click(screen.getByTestId('lt-assignment-submit'));
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith({ id: 12 }));
    expect(postMock).toHaveBeenCalledTimes(2);
    expect(postMock.mock.calls[1][1].conflict_resolution).toBe('replace');
  });

  it('shows a validation error when start_date is missing', async () => {
    render(<AssignmentDialog template={template} onCreated={() => {}} onClose={() => {}} />);
    fireEvent.click(screen.getByTestId('lt-assignment-submit'));
    await waitFor(() => expect(screen.getByTestId('lt-assignment-error')).toBeInTheDocument());
    expect(postMock).not.toHaveBeenCalled();
  });

  it('assigns to multiple checked assignment groups, one POST per group', async () => {
    getMock.mockImplementation((url) => {
      if (url?.includes('/assignment-groups/')) {
        return Promise.resolve({
          data: [
            { id: 11, name: 'Bunk Birch', group_type: 'bunk', is_active: true },
            { id: 12, name: 'Bunk Cedar', group_type: 'bunk', is_active: true },
            { id: 20, name: 'Unit Maple', group_type: 'unit', is_active: true },
          ],
        });
      }
      return Promise.resolve({ data: { assignments: [] } });
    });
    postMock.mockResolvedValue({ data: { id: 42, target_type: 'assignment_group' } });
    const onCreated = vi.fn();
    const onClose = vi.fn();
    render(<AssignmentDialog template={template} onCreated={onCreated} onClose={onClose} />);

    fireEvent.click(screen.getByTestId('lt-assignment-target-assignment_group'));
    await waitFor(() => expect(screen.getByTestId('lt-assignment-groups-panel')).toBeInTheDocument());
    await waitFor(() => expect(getMock).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId('lt-assignment-group-11')).toBeInTheDocument());
    // Sections are grouped by group_type.
    expect(screen.getByTestId('lt-assignment-group-section-bunk')).toBeInTheDocument();
    expect(screen.getByTestId('lt-assignment-group-section-unit')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('lt-assignment-group-11'));
    fireEvent.click(screen.getByTestId('lt-assignment-group-20'));
    fireEvent.change(screen.getByTestId('lt-assignment-start'), {
      target: { value: '2026-07-01' },
    });
    fireEvent.click(screen.getByTestId('lt-assignment-submit'));

    await waitFor(() => expect(postMock).toHaveBeenCalledTimes(2));
    expect(onCreated).toHaveBeenCalledTimes(2);
    const groupIds = postMock.mock.calls.map(([, body]) => body.assignment_group);
    expect(groupIds).toEqual(expect.arrayContaining([11, 20]));
    for (const [, body] of postMock.mock.calls) {
      expect(body.target_type).toBe('assignment_group');
      expect(body.start_date).toBe('2026-07-01');
    }
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it('group_type filter narrows visible groups without affecting selection', async () => {
    getMock.mockImplementation((url) => {
      if (url?.includes('/assignment-groups/')) {
        return Promise.resolve({
          data: [
            { id: 11, name: 'Bunk Birch', group_type: 'bunk', is_active: true },
            { id: 20, name: 'Unit Maple', group_type: 'unit', is_active: true },
          ],
        });
      }
      return Promise.resolve({ data: { assignments: [] } });
    });
    postMock.mockResolvedValue({ data: { id: 42, target_type: 'assignment_group' } });
    render(<AssignmentDialog template={template} onCreated={() => {}} onClose={() => {}} />);

    fireEvent.click(screen.getByTestId('lt-assignment-target-assignment_group'));
    await waitFor(() => screen.getByTestId('lt-assignment-group-type-filter'));

    // Filter to bunk — unit section disappears.
    fireEvent.change(screen.getByTestId('lt-assignment-group-type-filter'), {
      target: { value: 'bunk' },
    });
    expect(screen.getByTestId('lt-assignment-group-section-bunk')).toBeInTheDocument();
    expect(screen.queryByTestId('lt-assignment-group-section-unit')).not.toBeInTheDocument();

    // Reset filter — both sections are visible again.
    fireEvent.change(screen.getByTestId('lt-assignment-group-type-filter'), {
      target: { value: '' },
    });
    expect(screen.getByTestId('lt-assignment-group-section-unit')).toBeInTheDocument();
  });

  it('lists current assignments and unassigns an active one via PATCH end_date', async () => {
    getMock.mockResolvedValue({
      data: {
        assignments: [
          {
            id: 77,
            target_type: 'role',
            target_payload: { role: 'kitchen_staff' },
            start_date: '2026-06-01',
            end_date: null,
            status: 'active',
            display_title: 'Kitchen weekly',
          },
        ],
      },
    });
    patchMock.mockResolvedValue({ data: { id: 77, status: 'ended' } });
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const onCreated = vi.fn();
    render(<AssignmentDialog template={template} onCreated={onCreated} onClose={() => {}} />);

    const row = await screen.findByTestId('lt-current-row-77');
    expect(row).toHaveTextContent('Role: kitchen_staff');

    fireEvent.click(screen.getByTestId('lt-unassign-77'));
    await waitFor(() => expect(patchMock).toHaveBeenCalledTimes(1));
    const [url, body] = patchMock.mock.calls[0];
    expect(url).toMatch(/\/assignments\/77\//);
    expect(body).toHaveProperty('end_date');
    expect(body.end_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(onCreated).toHaveBeenCalledWith(expect.objectContaining({ _unassigned: true }));
    confirmSpy.mockRestore();
  });

  it('unassigns a scheduled assignment via DELETE', async () => {
    getMock.mockResolvedValueOnce({
      data: {
        assignments: [
          {
            id: 88,
            target_type: 'assignment_group',
            assignment_group: 11,
            assignment_group_name: 'Bunk Birch',
            target_payload: {},
            start_date: '2099-01-01',
            end_date: null,
            status: 'scheduled',
          },
        ],
      },
    });
    getMock.mockResolvedValue({ data: { assignments: [] } });
    deleteMock.mockResolvedValue({});
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    render(<AssignmentDialog template={template} onCreated={() => {}} onClose={() => {}} />);

    const row = await screen.findByTestId('lt-current-row-88');
    expect(row).toHaveTextContent('Group: Bunk Birch');

    fireEvent.click(screen.getByTestId('lt-unassign-88'));
    await waitFor(() => expect(deleteMock).toHaveBeenCalledTimes(1));
    expect(deleteMock.mock.calls[0][0]).toMatch(/\/assignments\/88\//);
    expect(patchMock).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });
});
