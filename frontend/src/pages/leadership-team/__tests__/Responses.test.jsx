import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import LeadershipTeamResponses from '../Responses';

const getMock = vi.fn();
vi.mock('../../../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'test-org' }),
}));

const templatePayload = { id: 7, name: 'KS Weekly', version: 1, role: 'kitchen_staff' };

const individualPayload = {
  tab: 'individual',
  template: { id: 7, slug: 'ks-weekly' },
  total: 1,
  page: 1,
  page_size: 25,
  results: [
    {
      id: 401,
      period_start: '2026-07-06',
      period_end: '2026-07-12',
      language: 'en',
      author: { id: 33, name: 'Asha Cook' },
      subject: { id: 33, name: 'Asha Cook' },
      template_version: 1,
      answers: { mood: 4 },
    },
  ],
};

const aggregatePayload = {
  tab: 'aggregate',
  total_responses: 2,
  response_volume_per_period: [{ period_start: '2026-07-06', count: 2 }],
  language_distribution: { en: 2 },
  avg_per_dimension: [
    { key: 'mood', avg: 4.5, count: 2, versions: [1] },
  ],
};

beforeEach(() => { getMock.mockReset(); });

function renderAt(route) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/leadership-team/templates/:id/responses" element={<LeadershipTeamResponses />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LeadershipTeamResponses', () => {
  it('renders the individual tab with a row per reflection', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/responses/')) return Promise.resolve({ data: individualPayload });
      return Promise.resolve({ data: templatePayload });
    });
    renderAt('/leadership-team/templates/7/responses');
    await waitFor(() => expect(screen.getByTestId('lt-responses-row-401')).toBeInTheDocument());
    expect(screen.getByText('Asha Cook')).toBeInTheDocument();
    expect(screen.getByTestId('lt-responses-export')).toHaveAttribute('href', expect.stringContaining('/responses/export/'));
  });

  it('switches to the aggregate tab and shows per-dimension averages', async () => {
    getMock.mockImplementation((url, { params } = {}) => {
      if (!url.includes('/responses/')) return Promise.resolve({ data: templatePayload });
      if (params?.tab === 'aggregate') return Promise.resolve({ data: aggregatePayload });
      return Promise.resolve({ data: individualPayload });
    });
    renderAt('/leadership-team/templates/7/responses');
    await waitFor(() => screen.getByTestId('lt-responses-row-401'));
    fireEvent.click(screen.getByTestId('lt-responses-tab-aggregate'));
    await waitFor(() => expect(screen.getByTestId('lt-responses-dim-mood')).toBeInTheDocument());
    expect(screen.getByText('4.50')).toBeInTheDocument();
  });
});
