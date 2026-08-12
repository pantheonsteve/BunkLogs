/**
 * Madrich challenge detail tests — Step 4_8, MA7.
 *
 * Covers the own-vs-peer author label the backend redaction drives:
 * the viewer's own challenge shows "You reported this" (and a
 * Withdraw button when eligible); a peer's shows "Submitted by A
 * Madrich" with no Withdraw button.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import MadrichChallengeDetail from '../ChallengeDetail';

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

function renderDetail(id = 'c-1') {
  return render(
    <MemoryRouter initialEntries={[`/madrich/challenges/${id}`]}>
      <Routes>
        <Route path="/madrich/challenges/:challengeId" element={<MadrichChallengeDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

const ownDetail = {
  id: 'c-1',
  category: 'behavior',
  category_label: 'Student behavior',
  session_date: '2026-09-13',
  body: 'Two students were disruptive during Hebrew drill.',
  status: 'open',
  author: { id: 7, display_name: 'Maya Madrich', redacted: false },
  responses: [],
};

const peerDetail = {
  ...ownDetail,
  author: { display: 'A Madrich', redacted: true },
};

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
});

describe('MadrichChallengeDetail', () => {
  it('shows "You reported this" and a Withdraw button for the own submission', async () => {
    getMock.mockResolvedValue({ data: ownDetail });
    renderDetail();
    await waitFor(() => screen.getByTestId('md-challenge-detail-author'));

    expect(screen.getByTestId('md-challenge-detail-author')).toHaveTextContent('You reported this');
    expect(screen.getByTestId('md-challenge-withdraw')).toBeInTheDocument();
  });

  it('shows "Submitted by A Madrich" and no Withdraw button for a peer submission', async () => {
    getMock.mockResolvedValue({ data: peerDetail });
    renderDetail();
    await waitFor(() => screen.getByTestId('md-challenge-detail-author'));

    expect(screen.getByTestId('md-challenge-detail-author')).toHaveTextContent('Submitted by A Madrich');
    expect(screen.queryByTestId('md-challenge-withdraw')).toBeNull();
  });

  it('hides Withdraw once a faculty response exists', async () => {
    getMock.mockResolvedValue({
      data: {
        ...ownDetail,
        responses: [{ id: 'r-1', author: { display_name: 'Rabbi Levy' }, body: 'Thanks!', created_at: '2026-09-13T12:00:00Z' }],
      },
    });
    renderDetail();
    await waitFor(() => screen.getByTestId('md-challenge-detail-author'));
    expect(screen.queryByTestId('md-challenge-withdraw')).toBeNull();
    expect(screen.getByText('Rabbi Levy')).toBeInTheDocument();
  });
});
