/**
 * Madrich challenge form tests — Step 4_8, MA7.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import MadrichChallengeForm from '../ChallengeForm';

const getMock = vi.fn();
const postMock = vi.fn();
vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
  },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'tbe', user: { id: 7 } }),
}));

const classroomsPayload = {
  classrooms: [
    { assignment_group_id: 12, name: 'Grade 9 — Room 204', session_date_default: '2026-09-13' },
  ],
};

function renderForm() {
  return render(
    <MemoryRouter initialEntries={['/madrich/challenges/new']}>
      <Routes>
        <Route path="/madrich/challenges/new" element={<MadrichChallengeForm />} />
        <Route path="/madrich/challenges/:challengeId" element={<div data-testid="detail-stub" />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

describe('MadrichChallengeForm', () => {
  it('submits a POST with the classroom, session date, category, and body', async () => {
    getMock.mockResolvedValue({ data: classroomsPayload });
    postMock.mockResolvedValue({ data: { id: 'abc-123' } });
    const user = userEvent.setup();

    renderForm();
    await waitFor(() => screen.getByTestId('md-challenge-body-input'));

    await user.type(screen.getByTestId('md-challenge-body-input'), 'Two students were disruptive.');
    await user.selectOptions(screen.getByTestId('md-challenge-category-input'), 'behavior');
    await user.click(screen.getByTestId('md-challenge-submit'));

    await waitFor(() => expect(postMock).toHaveBeenCalledWith(
      '/api/v1/madrich/challenges/',
      {
        assignment_group_id: 12,
        session_date: '2026-09-13',
        category: 'behavior',
        body: 'Two students were disruptive.',
      },
      expect.objectContaining({ headers: { 'X-Organization-Slug': 'tbe' } }),
    ));

    await waitFor(() => screen.getByTestId('detail-stub'));
  });

  it('shows the audience disclosure before submit', async () => {
    getMock.mockResolvedValue({ data: classroomsPayload });
    renderForm();
    await waitFor(() => screen.getByTestId('md-challenge-disclosure'));
    expect(screen.getByTestId('md-challenge-disclosure')).toHaveTextContent(
      'Other Madrichim in your classroom cannot.',
    );
  });

  it('shows a fallback state with no assigned classroom', async () => {
    getMock.mockResolvedValue({ data: { classrooms: [] } });
    renderForm();
    await waitFor(() => screen.getByTestId('md-challenge-form-no-classroom'));
  });
});
