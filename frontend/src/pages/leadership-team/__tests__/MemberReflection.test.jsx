import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import LeadershipTeamMemberReflection from '../MemberReflection';

const getMock = vi.fn();
const postMock = vi.fn();
vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
    delete: vi.fn(),
  },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'test-org' }),
}));

const payload = {
  header: {
    person: { id: 11, name: 'Asha Cook', first_name: 'Asha', last_name: 'Cook', preferred_name: 'Asha' },
    role: 'kitchen_staff',
    membership_id: 21,
    language_preference: 'en',
    period: { start: '2026-07-06', end: '2026-07-12', cadence: 'weekly' },
  },
  metadata: {
    reflection_id: 100,
    submitted_at: '2026-07-10T08:00:00Z',
    last_edited_at: null,
    language_of_authorship: 'en',
    team_visibility: 'org_default',
  },
  content: {
    fields: [
      { key: 'mood', type: 'single_rating', prompts: { en: 'Mood' }, answer: { mood: 4 }, scale: [1, 5] },
      { key: 'notes', type: 'textarea', prompts: { en: 'Anything else?' }, answer: 'Things went well today' },
    ],
    translation: null,
  },
  trend: {
    series: [
      {
        label: 'mood',
        field_key: 'mood',
        field_type: 'single_rating',
        scale_max: 5,
        points: [
          { period_start: '2026-06-29', period_end: '2026-07-05', value: 3, reflection_id: 99 },
          { period_start: '2026-07-06', period_end: '2026-07-12', value: 4, reflection_id: 100 },
        ],
      },
    ],
    scale_max: 5,
    period: { start: '2026-06-29', end: '2026-07-12', cadence: 'weekly' },
  },
  attention_markers: [],
};

beforeEach(() => { getMock.mockReset(); postMock.mockReset(); });

function renderAt(route) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route
          path="/leadership-team/teams/:teamRole/members/:membershipId"
          element={<LeadershipTeamMemberReflection />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LeadershipTeamMemberReflection', () => {
  it('renders the reflection content and trend series', async () => {
    getMock.mockResolvedValue({ data: payload });
    renderAt('/leadership-team/teams/kitchen_staff/members/21');
    await waitFor(() => expect(screen.getByText('Asha Cook')).toBeInTheDocument());
    expect(screen.getByText('Things went well today')).toBeInTheDocument();
    expect(screen.getByTestId('lt-trend-series-mood')).toBeInTheDocument();
  });

  it('opens the flag form and POSTs to mark-attention', async () => {
    getMock.mockResolvedValue({ data: payload });
    postMock.mockResolvedValue({ data: { id: 7 } });
    renderAt('/leadership-team/teams/kitchen_staff/members/21');
    await waitFor(() => screen.getByTestId('lt-mark-attention-toggle'));
    fireEvent.click(screen.getByTestId('lt-mark-attention-toggle'));
    fireEvent.change(screen.getByTestId('lt-mark-attention-note'), { target: { value: 'check in next week' } });
    fireEvent.click(screen.getByTestId('lt-mark-attention-submit'));
    await waitFor(() => expect(postMock).toHaveBeenCalled());
    expect(postMock.mock.calls[0][0]).toMatch(/reflections\/100\/mark-attention/);
    expect(postMock.mock.calls[0][1]).toEqual({ note: 'check in next week' });
  });
});
