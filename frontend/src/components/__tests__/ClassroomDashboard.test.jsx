/**
 * ClassroomDashboard tests — Steps 4_8 (MA7) and 7_24.
 *
 * The faculty-only blocks (challenges, completion, availability) arrive
 * together; the backend omits all three for non-faculty viewers, who
 * keep the stub. `completion` / `availability` arrive as explicit nulls
 * when unconfigured, which is a different message than "not yours".
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import ClassroomDashboard from '../ClassroomDashboard';

vi.mock('../../api/observations', async (importOriginal) => ({
  ...(await importOriginal()),
  searchObservationSubjects: vi.fn().mockResolvedValue([]),
  fetchRecipientCandidates: vi.fn().mockResolvedValue([]),
}));

const basePayload = {
  header: { group: { id: 12, name: 'Grade 9 — Room 204' } },
  summary: { subject_count: 2, author_count: 1 },
  subjects: [],
  authors: [],
};

const roster = [
  { id: 41, first_name: 'Sam', last_name: 'Student', preferred_name: '', membership_role: 'student' },
  { id: 42, first_name: 'Mira', last_name: 'Madrich', preferred_name: '', membership_role: 'madrich' },
];

const facultyPayload = {
  ...basePayload,
  challenges: {
    open_count: 2,
    recent: [
      {
        id: 'c-1',
        category_label: 'Student behavior',
        body_preview: 'Two students were disruptive…',
        status: 'open',
      },
    ],
    list_url: '/faculty/challenges?classroom=12',
  },
  completion: {
    template_name: 'Weekly 3-2-1',
    period: { start: '2026-08-10', end: '2026-08-16', cadence: 'weekly' },
    submitted_count: 1,
    expected_count: 2,
    students: [
      { person_id: 1, name: 'Ari Rich', grade_level: 10, state: 'complete', reflection_id: 9 },
      { person_id: 2, name: 'Bex Rich', grade_level: 10, state: 'missing', reflection_id: null },
    ],
  },
  availability: {
    sessions: ['2026-08-16'],
    rows: [
      {
        person_id: 1,
        display_name: 'Ari Rich',
        grade_level: 10,
        cells: [{ session_date: '2026-08-16', status: 'available', note: '' }],
      },
      {
        person_id: 2,
        display_name: 'Bex Rich',
        grade_level: 10,
        cells: [{ session_date: '2026-08-16', status: null, note: '' }],
      },
    ],
    available_counts: { '2026-08-16': 1 },
    unset_counts: { '2026-08-16': 1 },
    next_session: { date: '2026-08-16', available: 1, unset: 1 },
  },
};

function renderDashboard(data) {
  return render(<MemoryRouter><ClassroomDashboard data={data} /></MemoryRouter>);
}

describe('ClassroomDashboard', () => {
  it('shows the faculty-only stub for viewers without the faculty blocks', () => {
    renderDashboard(basePayload);
    expect(screen.getByTestId('classroom-reflections-stub')).toBeInTheDocument();
    expect(screen.queryByTestId('classroom-challenges-section')).toBeNull();
    expect(screen.queryByTestId('classroom-completion-section')).toBeNull();
    expect(screen.queryByTestId('classroom-availability-section')).toBeNull();
  });

  it('renders challenges, completion, and availability for faculty viewers', () => {
    renderDashboard(facultyPayload);

    expect(screen.queryByTestId('classroom-reflections-stub')).toBeNull();

    expect(screen.getByTestId('classroom-challenges-open-count')).toHaveTextContent('(2)');
    expect(screen.getByTestId('classroom-challenges-inbox-link')).toHaveAttribute(
      'href', '/faculty/challenges?classroom=12',
    );
    expect(screen.getByTestId('classroom-challenge-c-1')).toHaveTextContent('Two students were disruptive…');

    const completion = screen.getByTestId('classroom-completion-section');
    expect(completion).toHaveTextContent('1 of 2 submitted');
    expect(completion).toHaveTextContent('Weekly 3-2-1');
    expect(screen.getByTestId('classroom-completion-1')).toHaveTextContent('Submitted');
    expect(screen.getByTestId('classroom-completion-open-1')).toHaveAttribute(
      'href', '/reflections/9?returnTo=%2Fdashboards%2Fgroup%2F12',
    );
    expect(screen.getByTestId('classroom-completion-2')).toHaveTextContent('Missing');
    expect(screen.queryByTestId('classroom-completion-open-2')).toBeNull();

    expect(screen.getByTestId('classroom-availability-1')).toHaveTextContent('Available');
    expect(screen.getByTestId('classroom-availability-2')).toHaveTextContent('Not set');
  });

  it('explains a null completion rather than showing a zero count', () => {
    renderDashboard({ ...facultyPayload, completion: null, availability: null });

    expect(screen.getByTestId('classroom-completion-section')).toHaveTextContent(
      'No weekly reflection form is assigned to this program yet.',
    );
    expect(screen.getByTestId('classroom-availability-section')).toHaveTextContent(
      'No upcoming sessions are scheduled.',
    );
  });
});

describe('ClassroomDashboard roster', () => {
  it('links students to their profile and keeps Madrichim off a Madrich view', () => {
    renderDashboard({
      ...basePayload,
      subjects: roster,
      viewer: { is_faculty_author: false },
    });

    expect(screen.getByTestId('classroom-subject-link-41')).toHaveAttribute(
      'href', '/profile/41?group=12',
    );
    expect(screen.queryByTestId('classroom-subject-42')).toBeNull();
    expect(screen.queryByTestId('section-madrichim')).toBeNull();
    expect(screen.queryByTestId('section-authors')).toBeNull();
  });

  it('gives faculty the Madrichim roster alongside the students', () => {
    renderDashboard({
      ...basePayload,
      subjects: roster,
      viewer: { is_faculty_author: true },
    });

    expect(screen.getByTestId('classroom-subject-41')).toBeInTheDocument();
    expect(screen.getByTestId('classroom-madrich-42')).toHaveTextContent('Mira Madrich');
  });

  it('opens the composer prefilled with the student that was clicked', async () => {
    const user = userEvent.setup();
    renderDashboard({
      ...basePayload,
      subjects: roster,
      viewer: { is_faculty_author: false },
    });

    await user.click(screen.getByTestId('classroom-observe-41'));

    expect(screen.getByTestId('observation-subject-chips')).toHaveTextContent('Sam Student');
    expect(screen.getByTestId('observation-composer-body')).toBeInTheDocument();
  });
});
