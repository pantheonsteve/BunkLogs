import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import AdminReflectionMemberDetail from '../AdminReflectionMemberDetail';

const fetchMock = vi.fn();
vi.mock('../../../../api/adminReflections', () => ({
  fetchAdminReflectionMember: (...args) => fetchMock(...args),
}));

vi.mock('../../../../auth/AuthContext', () => ({
  useAuth: () => ({
    user: {
      organizations: [{ slug: 'tbe', capability: 'admin', roles: ['admin'] }],
      membership_roles: ['admin'],
    },
    loading: false,
  }),
}));

const samplePayload = {
  membership_id: 3189,
  person_id: 42,
  person_name: 'Maya Aronson',
  grade_level: 8,
  role: 'madrich',
  role_label: 'Madrich',
  history: [
    {
      reflection_id: 900,
      period_start: '2026-08-03',
      period_end: '2026-08-09',
      status: 'submitted',
      submitted_at: '2026-08-09T14:00:00Z',
      answers: { ratings: { engagement: 4 }, wins: ['Great circle time'] },
    },
    {
      reflection_id: 901,
      period_start: '2026-07-27',
      period_end: '2026-08-02',
      status: 'day_off',
      submitted_at: null,
      answers: {},
    },
  ],
};

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockResolvedValue(samplePayload);
});

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/reflections/madrich/members/3189']}>
      <Routes>
        <Route
          path="/admin/reflections/:role/members/:membershipId"
          element={<AdminReflectionMemberDetail />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('AdminReflectionMemberDetail', () => {
  it('indexes every period and links each entry to its anchor and detail page', async () => {
    renderPage();

    await waitFor(() => expect(screen.getByText('Maya Aronson')).toBeInTheDocument());

    expect(screen.getByTestId('admin-reflection-member-index-900')).toHaveAttribute(
      'href',
      '#entry-900',
    );
    expect(screen.getByTestId('admin-reflection-member-index-901')).toHaveAttribute(
      'href',
      '#entry-901',
    );
    expect(screen.getByTestId('admin-reflection-member-entry-900')).toHaveAttribute('id', 'entry-900');
    expect(screen.getByTestId('admin-reflection-member-open-901')).toHaveAttribute(
      'href',
      '/reflections/901?returnTo=%2Fadmin%2Freflections%2Fmadrich%2Fmembers%2F3189',
    );
  });

  it('scrolls to the chosen entry and marks it current', async () => {
    const scrollIntoView = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoView;
    renderPage();

    await waitFor(() => expect(screen.getByText('Maya Aronson')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('admin-reflection-member-index-901'));

    expect(scrollIntoView).toHaveBeenCalled();
    expect(screen.getByTestId('admin-reflection-member-index-901')).toHaveAttribute(
      'aria-current',
      'true',
    );
  });

  it('hides the index when there is only one entry', async () => {
    fetchMock.mockResolvedValue({ ...samplePayload, history: [samplePayload.history[0]] });
    renderPage();

    await waitFor(() => expect(screen.getByText('Maya Aronson')).toBeInTheDocument());
    expect(screen.queryByTestId('admin-reflection-member-index')).not.toBeInTheDocument();
  });
});
