/**
 * Madrich challenge log tests — Step 4_8, MA7.
 *
 * Focus: the peer-safe "Our classroom" tab renders the redacted
 * "A Madrich" author label per MA7 (peer Madrichim never see who
 * submitted a challenge, only their own submissions).
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import MadrichChallengeLog from '../ChallengeLog';

const getMock = vi.fn();
vi.mock('../../../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'tbe', user: { id: 7 } }),
}));

const classroomsPayload = {
  classrooms: [
    { assignment_group_id: 12, name: 'Grade 9 — Room 204', session_date_default: '2026-09-13' },
  ],
};

const peerChallenges = {
  results: [
    {
      id: 'c-1',
      category: 'behavior',
      category_label: 'Student behavior',
      session_date: '2026-09-13',
      body_preview: 'Two students were disruptive…',
      status: 'open',
      author: { display: 'A Madrich', redacted: true },
      response_count: 0,
      created_at: '2026-09-13T10:00:00Z',
    },
  ],
};

const mineChallenges = {
  results: [
    {
      id: 'c-2',
      category: 'materials',
      category_label: 'Materials / curriculum',
      session_date: '2026-09-13',
      body_preview: 'We ran out of worksheets.',
      status: 'resolved',
      author: { id: 7, display_name: 'Maya Madrich', redacted: false },
      response_count: 1,
      created_at: '2026-09-13T10:00:00Z',
    },
  ],
};

beforeEach(() => {
  getMock.mockReset();
});

describe('MadrichChallengeLog', () => {
  it('shows the redacted "A Madrich" author on the classroom tab', async () => {
    getMock.mockImplementation((url) => {
      if (url.endsWith('/classrooms/')) return Promise.resolve({ data: classroomsPayload });
      return Promise.resolve({ data: peerChallenges });
    });

    render(<MemoryRouter><MadrichChallengeLog /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('md-challenge-card-c-1'));

    expect(screen.getByTestId('md-challenge-card-c-1')).toHaveTextContent('A Madrich');
  });

  it('switches to "My reports" and shows the viewer\'s own name', async () => {
    getMock.mockImplementation((url, config) => {
      if (url.endsWith('/classrooms/')) return Promise.resolve({ data: classroomsPayload });
      if (config?.params?.mine === '1') return Promise.resolve({ data: mineChallenges });
      return Promise.resolve({ data: peerChallenges });
    });
    const user = userEvent.setup();

    render(<MemoryRouter><MadrichChallengeLog /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('md-challenge-tab-mine'));
    await user.click(screen.getByTestId('md-challenge-tab-mine'));

    await waitFor(() => screen.getByTestId('md-challenge-card-c-2'));
    expect(screen.getByTestId('md-challenge-card-c-2')).toHaveTextContent('Maya Madrich');
  });

  it('shows an empty state when there are no challenges', async () => {
    getMock.mockImplementation((url) => {
      if (url.endsWith('/classrooms/')) return Promise.resolve({ data: classroomsPayload });
      return Promise.resolve({ data: { results: [] } });
    });

    render(<MemoryRouter><MadrichChallengeLog /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('md-challenge-log-empty'));
  });
});
