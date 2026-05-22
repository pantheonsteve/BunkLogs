import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';

vi.mock('../../../api/admin', () => ({
  listAdminAssignments: vi.fn(),
  createAdminAssignment: vi.fn(),
  patchAdminAssignment: vi.fn(),
}));

import {
  listAdminAssignments,
  createAdminAssignment,
} from '../../../api/admin';
import AdminAssignments from '../Assignments';

beforeEach(() => {
  vi.clearAllMocks();
  listAdminAssignments.mockResolvedValue({ results: [] });
});

describe('AdminAssignments (7_13 PR2)', () => {
  it('renders all five sub-tabs and switches between them', async () => {
    render(<AdminAssignments />);
    expect(await screen.findByTestId('assignment-sub-tab-counselor_bunk')).toBeInTheDocument();
    expect(screen.getByTestId('assignment-sub-tab-uh_counselor')).toBeInTheDocument();
    expect(screen.getByTestId('assignment-sub-tab-cc_caseload')).toBeInTheDocument();
    expect(screen.getByTestId('assignment-sub-tab-lt_team')).toBeInTheDocument();
    expect(screen.getByTestId('assignment-sub-tab-camper_bunk')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('assignment-sub-tab-uh_counselor'));
    await waitFor(() =>
      expect(listAdminAssignments).toHaveBeenLastCalledWith('uh_counselor'),
    );
  });

  it('renders the backdated-clamp warning when the API reports one', async () => {
    createAdminAssignment.mockResolvedValueOnce({
      backdated_clamped: true,
      requested_start_date: '2020-01-01',
      warnings: [
        { supervision_id: 7, supervisor_membership_id: 12, supervisor_name: 'Sue', kind: 'co_supervisor' },
      ],
      supervision: { id: 1 },
    });
    render(<AdminAssignments />);
    await screen.findByTestId('assignment-create-form');

    fireEvent.click(screen.getByTestId('assignment-create-submit'));

    await waitFor(() => expect(createAdminAssignment).toHaveBeenCalled());
    expect(await screen.findByTestId('backdated-warning')).toBeInTheDocument();
    expect(screen.getByTestId('assignment-warnings')).toBeInTheDocument();
  });
});
