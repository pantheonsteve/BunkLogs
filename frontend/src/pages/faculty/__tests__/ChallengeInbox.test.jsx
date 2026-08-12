/**
 * Faculty challenge inbox tests — Step 4_8, MA7.
 *
 * Faculty always see full author identity (semi-anonymity is
 * peer-Madrich only), so the inbox renders real names.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import FacultyChallengeInbox from '../ChallengeInbox';

const getMock = vi.fn();
vi.mock('../../../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'tbe', user: { id: 42 } }),
}));

const inboxPayload = {
  results: [
    {
      id: 'c-1',
      category: 'behavior',
      category_label: 'Student behavior',
      session_date: '2026-09-13',
      body_preview: 'Two students were disruptive…',
      status: 'open',
      author: { id: 7, display_name: 'Maya Madrich', redacted: false },
      assignment_group: { id: 12, name: 'Grade 9 — Room 204' },
      response_count: 0,
      created_at: '2026-09-13T10:00:00Z',
    },
  ],
};

beforeEach(() => {
  getMock.mockReset();
});

describe('FacultyChallengeInbox', () => {
  it('renders the author name from the API', async () => {
    getMock.mockResolvedValue({ data: inboxPayload });
    render(<MemoryRouter><FacultyChallengeInbox /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('faculty-challenge-row-c-1'));

    expect(screen.getByTestId('faculty-challenge-row-c-1')).toHaveTextContent('Maya Madrich');
  });

  it('shows an empty state when no challenges match', async () => {
    getMock.mockResolvedValue({ data: { results: [] } });
    render(<MemoryRouter><FacultyChallengeInbox /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('faculty-challenge-empty'));
  });
});
