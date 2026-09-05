/**
 * Faculty response queue and roster — Step 4_9 §5.1-5.3.
 *
 * The queue's whole purpose is to make an old unanswered question impossible
 * to miss, so the ordering and the age escalation are what these assert.
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

const queueItem = (id, name, ageDays, escalation, extra = {}) => ({
  id,
  subject_person: { id: id * 10, display_name: name },
  field_key: 'question_or_concern',
  field_label: 'One question or concern',
  item_index: null,
  excerpt: `${name} asked something`,
  routes_to: 'faculty',
  resolved_at: null,
  created_at: '2026-09-01T12:00:00Z',
  last_message_at: null,
  last_message_preview: '',
  message_count: 0,
  unread: true,
  age_days: ageDays,
  escalation,
  awaiting_reply: true,
  ...extra,
});

const dashboard = {
  today: '2026-09-20',
  period: { start: '2026-09-14', end: '2026-09-20', cadence: 'weekly' },
  header: { name: 'Rabbi Gold', role_label: 'Faculty', program_name: 'TBE Religious School' },
  classrooms: [{
    id: 12,
    name: 'Tzedakah 101',
    slug: 'tzedakah-101',
    url: '/dashboards/group/12',
    subject_count: 2,
    reflections: { submitted: 1, expected: 2, template_name: 'Weekly 3-2-1' },
    availability: { date: '2026-09-27', available: 1, unset: 1 },
    upcoming_sessions: [
      { date: '2026-09-27', available: 1, unset: 1 },
      { date: '2026-10-04', available: 2, unset: 0 },
    ],
    open_challenge_count: 0,
  }],
  challenges_url: '/faculty/challenges',
  response_queue: {
    total: 9,
    overdue_count: 1,
    url: '/faculty/queue',
    items: [
      queueItem(1, 'Old Ari', 21, 'overdue'),
      queueItem(2, 'Mid Ben', 9, 'aging'),
      queueItem(3, 'New Cara', 2, 'fresh'),
    ],
  },
};

const roster = {
  results: [{
    person_id: 10,
    display_name: 'Old Ari',
    grade_level: 9,
    classroom_id: 12,
    reflection_state: 'missing',
    reflection_id: null,
    next_session_availability: null,
    open_thread_count: 2,
    unread_thread_count: 1,
    open_challenge_count: 0,
  }, {
    person_id: 20,
    display_name: 'Ben Submitted',
    grade_level: 10,
    classroom_id: 12,
    reflection_state: 'complete',
    reflection_id: 88,
    next_session_availability: 'available',
    open_thread_count: 0,
    unread_thread_count: 0,
    open_challenge_count: 0,
  }],
  period: { start: '2026-09-14', end: '2026-09-20' },
  next_session: '2026-09-27',
};

beforeEach(() => {
  getMock.mockReset();
  getMock.mockImplementation((url) => Promise.resolve({
    data: url.includes('/faculty/roster/') ? roster : dashboard,
  }));
});

function renderDashboard() {
  return render(<MemoryRouter><FacultyDashboard /></MemoryRouter>);
}

describe('Faculty homepage — response queue and roster', () => {
  it('lists routed questions oldest first with an age escalation label', async () => {
    renderDashboard();
    await waitFor(() => screen.getByTestId('fac-queue-list'));

    const rows = screen.getAllByTestId(/^fac-queue-row-/);
    expect(rows.map((r) => r.dataset.testid)).toEqual([
      'fac-queue-row-1', 'fac-queue-row-2', 'fac-queue-row-3',
    ]);
    expect(screen.getByTestId('fac-queue-escalation-1')).toHaveTextContent('Two weeks waiting');
    expect(screen.getByTestId('fac-queue-escalation-2')).toHaveTextContent('A week waiting');
    expect(screen.getByTestId('fac-queue-escalation-3')).toHaveTextContent('This week');
    expect(screen.getByTestId('fac-queue-overdue')).toHaveTextContent('1 overdue');
  });

  it('links to the full queue when the card is showing a preview', async () => {
    renderDashboard();
    await waitFor(() => screen.getByTestId('fac-queue-link'));
    expect(screen.getByTestId('fac-queue-link')).toHaveAttribute('href', '/faculty/queue');
    expect(screen.getByTestId('fac-queue-row-1')).toHaveAttribute('href', '/faculty/threads/1');
  });

  it('says nothing is waiting rather than showing an empty list', async () => {
    getMock.mockImplementation((url) => Promise.resolve({
      data: url.includes('/faculty/roster/')
        ? roster
        : { ...dashboard, response_queue: { total: 0, overdue_count: 0, items: [], url: '/faculty/queue' } },
    }));
    renderDashboard();
    await waitFor(() => screen.getByTestId('fac-queue-card'));
    expect(screen.getByTestId('fac-queue-card')).toHaveTextContent('No questions are waiting');
    expect(screen.queryByTestId('fac-queue-list')).toBeNull();
    expect(screen.queryByTestId('fac-queue-overdue')).toBeNull();
  });

  it('shows each Madrich\'s state and links to their drill-in', async () => {
    renderDashboard();
    await waitFor(() => screen.getByTestId('fac-roster-row-10'));
    expect(screen.getByTestId('fac-roster-row-10')).toHaveAttribute('href', '/faculty/roster/10');
    expect(screen.getByTestId('fac-roster-state-10')).toHaveTextContent('Not yet');
    expect(screen.getByTestId('fac-roster-row-10')).toHaveTextContent('Old Ari');
    expect(screen.queryByTestId('fac-roster-open-10')).toBeNull();
    expect(screen.getByTestId('fac-roster-availability-header')).toHaveTextContent('Availability');
    expect(screen.getByTestId('fac-roster-availability-header')).toHaveTextContent('Sep 27');
  });

  it('puts an Open button next to a submitted reflection', async () => {
    renderDashboard();
    await waitFor(() => screen.getByTestId('fac-roster-open-20'));
    const row = screen.getByTestId('fac-roster-row-20').closest('tr');
    expect(screen.getByTestId('fac-roster-state-20')).toHaveTextContent('Submitted');
    expect(screen.getByTestId('fac-roster-open-20')).toHaveAttribute(
      'href', '/reflections/88?returnTo=%2Ffaculty',
    );
    expect(screen.getByTestId('fac-roster-open-20')).toHaveTextContent('Open');
    expect(row.textContent).toMatch(/Submitted.*Available.*Open/);
  });

  it('separates an unanswered Sunday from a full house', async () => {
    renderDashboard();
    await waitFor(() => screen.getByTestId('fac-upcoming-card'));
    expect(screen.getByTestId('fac-session-12-2026-09-27')).toHaveTextContent('1 unanswered');
    expect(screen.getByTestId('fac-session-12-2026-10-04')).not.toHaveTextContent('unanswered');
  });
});
