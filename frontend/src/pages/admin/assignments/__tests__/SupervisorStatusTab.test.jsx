import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';

vi.mock('../../../../api/admin', () => ({
  buildAdminPeopleListParams: (p) => ({ ...p }),
  listAdminPeople: vi.fn(),
  getAdminSupervisorStatus: vi.fn(),
}));

import { listAdminPeople, getAdminSupervisorStatus } from '../../../../api/admin';
import SupervisorStatusTab from '../SupervisorStatusTab';

beforeEach(() => {
  vi.clearAllMocks();
  listAdminPeople.mockResolvedValue({
    results: [{ id: 594, full_name: 'Tal Oren' }],
  });
  getAdminSupervisorStatus.mockResolvedValue({
    person: { id: 594, name: 'Tal Oren' },
    is_supervisor: true,
    can_view_reflections: true,
    supervised_entities: {
      units: [{ id: 108, name: 'Lower Chaverim' }],
      bunks: [],
      teams: [],
      supervisions: [],
    },
    supervised_people: {
      count: 1,
      people: [{ id: 692, name: 'Samantha Nadel', role: 'counselor' }],
    },
  });
});

describe('SupervisorStatusTab', () => {
  it('loads a person and shows their derived supervisor status', async () => {
    render(<SupervisorStatusTab />);

    const personButton = await screen.findByText('Tal Oren');
    fireEvent.click(personButton);

    await waitFor(() => {
      expect(getAdminSupervisorStatus).toHaveBeenCalledWith(594);
    });

    expect(await screen.findByText('Supervisor')).toBeInTheDocument();
    expect(
      screen.getByText('Can view self + other reflections'),
    ).toBeInTheDocument();
    expect(screen.getByText('Lower Chaverim')).toBeInTheDocument();
    expect(screen.getByText('Samantha Nadel')).toBeInTheDocument();
  });
});
