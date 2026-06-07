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
}));

import api from '../../../api';
import {
  listAdminAssignments,
  listAdminPrograms,
  createAdminAssignment,
} from '../../../api/admin';
import AdminAssignments from '../Assignments';

const program = { id: 1, name: 'Summer 2026', slug: 'summer-2026', is_active: true };
const endedProgram = { id: 2, name: 'Summer 2025', slug: 'summer-2025', is_active: false };

beforeEach(() => {
  vi.clearAllMocks();
  listAdminPrograms.mockResolvedValue({ results: [program, endedProgram] });
  listAdminAssignments.mockResolvedValue({ results: [] });
  api.get.mockImplementation(async (url) => {
    if (url.includes('/assignment-groups/')) {
      return {
        data: {
          results: [{
            id: 10,
            name: 'Bunk Maple',
            parent_name: 'Unit A',
            program_name: 'Summer 2026',
          }],
        },
      };
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
    expect(screen.getByTestId('assignment-sub-tab-uh_counselor')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('assignment-sub-tab-uh_counselor'));
    await waitFor(() => {
      expect(listAdminAssignments).toHaveBeenCalledWith(
        expect.objectContaining({ sub_tab: 'uh_counselor' }),
      );
    });
  });

  it('shows program names with active and ended badges', async () => {
    render(<AdminAssignments />);
    await screen.findByTestId('assignment-program-chips');
    expect(screen.getByText('Summer 2026')).toBeInTheDocument();
    expect(screen.getByText('Summer 2025')).toBeInTheDocument();
    expect(screen.getAllByText('Active').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Ended').length).toBeGreaterThan(0);
  });

  it('passes filter params when listing assignments', async () => {
    render(<AdminAssignments />);
    await screen.findByTestId('assignment-filter-bar');

    fireEvent.click(screen.getByTestId('assignment-program-chip-1'));

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
    });
  });

  it('bulk assign posts once per selected person', async () => {
    createAdminAssignment.mockResolvedValue({ id: 1 });
    render(<AdminAssignments />);
    await screen.findByTestId('assignment-group-list');

    fireEvent.click(screen.getByTestId('assignment-program-chip-1'));
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
