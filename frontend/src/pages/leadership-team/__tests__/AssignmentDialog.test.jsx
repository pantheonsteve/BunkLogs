import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import AssignmentDialog from '../AssignmentDialog';

const postMock = vi.fn();
vi.mock('../../../api', () => ({
  default: { post: (...args) => postMock(...args) },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'test-org' }),
}));

beforeEach(() => { postMock.mockReset(); });

const template = { id: 9, name: 'Kitchen weekly', version: 2, role: 'kitchen_staff' };

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
});
