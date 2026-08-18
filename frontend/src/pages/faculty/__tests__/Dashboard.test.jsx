/**
 * Faculty home tests — Step 7_24.
 *
 * One card per authored classroom carrying completion, next-session
 * availability, and open challenges; an empty state for faculty who
 * aren't on a roster yet.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import FacultyDashboard from '../Dashboard';

const getMock = vi.fn();
vi.mock('../../../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'tbe', user: { id: 42 } }),
}));

const dashboardPayload = {
  today: '2026-09-10',
  period: { start: '2026-09-07', end: '2026-09-13', cadence: 'weekly' },
  header: {
    name: 'Rabbi Gold',
    role_label: 'Faculty',
    program_name: 'TBE Religious School',
    preferred_language: 'en',
  },
  classrooms: [
    {
      id: 12,
      name: 'Tzedakah 101',
      slug: 'tzedakah-101',
      url: '/dashboards/group/12',
      subject_count: 6,
      reflections: { submitted: 4, expected: 6, template_name: 'Weekly 3-2-1' },
      availability: { date: '2026-09-13', available: 3, unset: 2 },
      open_challenge_count: 2,
    },
  ],
  challenges_url: '/faculty/challenges',
};

function renderDashboard() {
  return render(<MemoryRouter><FacultyDashboard /></MemoryRouter>);
}

beforeEach(() => {
  getMock.mockReset();
});

describe('FacultyDashboard', () => {
  it('renders a card per classroom with its three signals', async () => {
    getMock.mockResolvedValue({ data: dashboardPayload });
    renderDashboard();
    await waitFor(() => screen.getByTestId('fac-classroom-12'));

    expect(getMock).toHaveBeenCalledWith(
      '/api/v1/faculty/dashboard/',
      expect.objectContaining({
        headers: { 'X-Organization-Slug': 'tbe' },
      }),
    );

    const card = screen.getByTestId('fac-classroom-12');
    expect(card).toHaveTextContent('Tzedakah 101');
    expect(card).toHaveTextContent('6 Madrichim');
    expect(screen.getByTestId('fac-classroom-12-reflections')).toHaveTextContent('4 of 6');
    expect(screen.getByTestId('fac-classroom-12-availability')).toHaveTextContent('3 available');
    expect(screen.getByTestId('fac-classroom-12-challenges')).toHaveTextContent('2 open challenges');
    expect(screen.getByTestId('fac-classroom-12-cta')).toHaveAttribute(
      'href', '/dashboards/group/12',
    );
    expect(screen.getByTestId('fac-challenges-section')).toHaveTextContent(
      '2 open across your classrooms',
    );
  });

  it('explains unconfigured signals rather than showing zeroes', async () => {
    getMock.mockResolvedValue({
      data: {
        ...dashboardPayload,
        classrooms: [{
          ...dashboardPayload.classrooms[0],
          reflections: null,
          availability: null,
          open_challenge_count: 0,
        }],
      },
    });
    renderDashboard();
    await waitFor(() => screen.getByTestId('fac-classroom-12'));

    expect(screen.getByTestId('fac-classroom-12-reflections')).toHaveTextContent(
      'No weekly form assigned yet',
    );
    expect(screen.getByTestId('fac-classroom-12-availability')).toHaveTextContent(
      'No upcoming sessions scheduled',
    );
    expect(screen.queryByTestId('fac-classroom-12-challenges')).toBeNull();
  });

  it('shows an empty state for faculty without a classroom', async () => {
    getMock.mockResolvedValue({ data: { ...dashboardPayload, classrooms: [] } });
    renderDashboard();
    await waitFor(() => screen.getByTestId('fac-no-classrooms'));
  });

  it('offers a retry when the dashboard fails to load', async () => {
    getMock.mockRejectedValue(new Error('boom'));
    renderDashboard();
    await waitFor(() => screen.getByTestId('fac-error'));
  });
});
