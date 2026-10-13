/**
 * Faculty home roster noun once an org has saved group types.
 * The camp word is the fallback when terminology leaves counselor unset.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import FacultyDashboard from '../Dashboard';
import { DEFAULT_TERMS, normalizeTerminology, resolveTerm } from '../../../utils/terminology';

const getMock = vi.fn();
vi.mock('../../../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'camp', user: { id: 7 } }),
}));

let terms = DEFAULT_TERMS;
vi.mock('../../../context/OrgBrandingContext', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useTerm: () => (key, opts) => resolveTerm(terms, key, opts),
  };
});

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useNavigate: () => vi.fn() };
});

const dashboard = {
  today: '2026-09-10',
  period: { start: '2026-09-07', end: '2026-09-13', cadence: 'weekly' },
  header: { name: 'Fran Faculty', role_label: 'Faculty', program_name: 'Summer' },
  classrooms: [{
    id: 3,
    name: 'Grade 3',
    url: '/dashboards/group/3',
    subject_count: 2,
    reflections: { submitted: 1, expected: 2, template_name: 'Weekly' },
    availability: null,
    open_challenge_count: 0,
  }],
  challenges_url: '/faculty/challenges',
  roster_term: 'counselor',
};

function mockApi() {
  getMock.mockImplementation((url) => {
    if (url.includes('/faculty/roster')) {
      return Promise.resolve({
        data: {
          results: [{
            person_id: 9,
            display_name: 'Maya Alpha',
            classroom_id: 3,
            reflection_state: 'missing',
            next_session_availability: 'unset',
            open_challenge_count: 0,
            unread_thread_count: 0,
          }],
          roster_term: 'counselor',
        },
      });
    }
    if (url.includes('/faculty/challenges')) {
      return Promise.resolve({ data: { results: [] } });
    }
    if (url.includes('/reflections/my-tasks/')) {
      return Promise.resolve({ data: { tasks: [] } });
    }
    return Promise.resolve({ data: dashboard });
  });
}

beforeEach(() => {
  terms = DEFAULT_TERMS;
  getMock.mockReset();
  mockApi();
});

describe('Faculty home roster term', () => {
  it('uses the camp word for counselor when terminology is unset', async () => {
    render(<MemoryRouter><FacultyDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('fac-roster-card-3'));

    expect(screen.getByText('1 bunk · 2 counselors')).toBeInTheDocument();
    expect(screen.getByTestId('fac-roster-card-3')).toHaveTextContent('Grade 3 · Counselors');
    expect(screen.getByRole('columnheader', { name: 'Counselor' })).toBeInTheDocument();
  });

  it('follows a saved counselor term', async () => {
    terms = normalizeTerminology({
      counselor: { one: 'guide', other: 'guides' },
    });
    render(<MemoryRouter><FacultyDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('fac-roster-card-3'));

    expect(screen.getByTestId('fac-roster-card-3')).toHaveTextContent('Grade 3 · Guides');
    expect(screen.getByRole('columnheader', { name: 'Guide' })).toBeInTheDocument();
  });
});
