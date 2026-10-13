/**
 * Faculty challenge detail — back navigation to the inbox.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import FacultyChallengeDetail from '../ChallengeDetail';

const getMock = vi.fn();
const postMock = vi.fn();
vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
    patch: vi.fn(),
  },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'tbe', user: { id: 42 } }),
}));

const detail = {
  id: 'c-1',
  category: 'behavior',
  category_label: 'Student behavior',
  session_date: '2026-09-13',
  body: 'Two students were disruptive during Hebrew drill.',
  status: 'open',
  author: { id: 7, display_name: 'Maya Madrich', redacted: false },
  assignment_group: { id: 12, name: 'Grade 9 — Room 204' },
  responses: [],
};

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

describe('FacultyChallengeDetail', () => {
  it('links back to the challenges inbox', async () => {
    getMock.mockResolvedValue({ data: detail });
    render(
      <MemoryRouter initialEntries={['/faculty/challenges/c-1']}>
        <Routes>
          <Route path="/faculty/challenges/:challengeId" element={<FacultyChallengeDetail />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByTestId('faculty-challenge-detail-body'));
    expect(screen.getByTestId('faculty-challenge-detail-back')).toHaveAttribute(
      'href', '/faculty/challenges',
    );
    expect(screen.queryByTestId('faculty-challenge-done')).not.toBeInTheDocument();
  });

  it('shows Done back to the inbox after a reply', async () => {
    getMock.mockResolvedValue({ data: detail });
    postMock.mockResolvedValue({
      data: {
        ...detail,
        responses: [{ id: 'r-1', author: { display_name: 'Sadie Allspaw' }, body: 'I will follow up.' }],
      },
    });
    render(
      <MemoryRouter initialEntries={['/faculty/challenges/c-1']}>
        <Routes>
          <Route path="/faculty/challenges/:challengeId" element={<FacultyChallengeDetail />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByTestId('faculty-challenge-reply-input'));
    fireEvent.change(screen.getByTestId('faculty-challenge-reply-input'), {
      target: { value: 'I will follow up.' },
    });
    fireEvent.click(screen.getByTestId('faculty-challenge-reply-send'));
    await waitFor(() => screen.getByTestId('faculty-challenge-done'));
    expect(screen.getByTestId('faculty-challenge-done')).toHaveAttribute(
      'href', '/faculty/challenges',
    );
  });
});
