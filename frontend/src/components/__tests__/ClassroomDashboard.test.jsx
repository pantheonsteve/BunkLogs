/**
 * ClassroomDashboard tests — Step 4_8, MA7.
 *
 * The "Open challenges" section only replaces the reflections-not-
 * configured stub when the backend supplies `data.challenges`
 * (faculty-author viewers only; a Madrich landing here still sees
 * the stub since the backend never populates that key for them).
 */
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ClassroomDashboard from '../ClassroomDashboard';

const basePayload = {
  header: { group: { id: 12, name: 'Grade 9 — Room 204' } },
  summary: { subject_count: 2, author_count: 1 },
  subjects: [],
  authors: [],
};

describe('ClassroomDashboard', () => {
  it('shows the reflections-not-configured stub when no challenges block is present', () => {
    render(<MemoryRouter><ClassroomDashboard data={basePayload} /></MemoryRouter>);
    expect(screen.getByTestId('classroom-reflections-stub')).toBeInTheDocument();
    expect(screen.queryByTestId('classroom-challenges-section')).toBeNull();
  });

  it('renders the open challenges section instead of the stub for faculty viewers', () => {
    const data = {
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
    };
    render(<MemoryRouter><ClassroomDashboard data={data} /></MemoryRouter>);

    expect(screen.queryByTestId('classroom-reflections-stub')).toBeNull();
    expect(screen.getByTestId('classroom-challenges-section')).toBeInTheDocument();
    expect(screen.getByTestId('classroom-challenges-open-count')).toHaveTextContent('(2)');
    expect(screen.getByTestId('classroom-challenges-inbox-link')).toHaveAttribute(
      'href', '/faculty/challenges?classroom=12',
    );
    expect(screen.getByTestId('classroom-challenge-c-1')).toHaveTextContent('Two students were disruptive…');
  });
});
