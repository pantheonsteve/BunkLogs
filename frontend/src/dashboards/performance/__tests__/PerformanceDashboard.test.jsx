import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import PerformanceDashboard from '../PerformanceDashboard';

vi.mock('../../../api', () => ({
  default: { get: vi.fn() },
}));

import api from '../../../api';

const payload = {
  date: '2026-07-10',
  program: null,
  programs: [{ id: 1, name: 'Summer 2026' }],
  groups: [
    {
      id: 5,
      name: 'Bunk Maple',
      group_type: 'bunk',
      parent_name: 'Unit Aleph',
      author_names: ['Sam Counselor'],
      completion: { submitted: 2, expected: 3, percent: 67, is_complete: false },
      scores: { scale_max: 5, distribution: { '4': 2, '5': 1 }, total_ratings: 3 },
    },
    {
      id: 6,
      name: 'Bunk Oak',
      group_type: 'bunk',
      parent_name: 'Unit Aleph',
      author_names: ['Alex Counselor'],
      completion: { submitted: 4, expected: 4, percent: 100, is_complete: true },
      scores: { scale_max: 5, distribution: { '5': 4 }, total_ratings: 4 },
    },
  ],
};

describe('PerformanceDashboard', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue({ data: payload });
  });

  it('renders filters, group cards, and program name when a program is selected', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <PerformanceDashboard />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Bunk Maple')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('performance-program-name')).not.toBeInTheDocument();

    await user.selectOptions(screen.getByDisplayValue('All programs'), '1');

    await waitFor(() => {
      expect(screen.getByTestId('performance-program-name')).toHaveTextContent('Summer 2026');
    });
    expect(screen.getByText('Sam Counselor')).toBeInTheDocument();

    const mapleLink = screen.getByTestId('performance-group-5');
    expect(mapleLink).toHaveAttribute('href', '/dashboards/group/5?date=2026-07-10');

    expect(api.get).toHaveBeenCalledWith(
      '/api/v1/dashboards/groups/performance/',
      expect.objectContaining({
        params: expect.objectContaining({ group_type: 'bunk' }),
      }),
    );
  });
});
