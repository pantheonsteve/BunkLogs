import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import ReflectionDetailPage from './ReflectionDetailPage';

const getMock = vi.fn();

vi.mock('../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

vi.mock('../partials/Header', () => ({ default: () => null }));
vi.mock('../partials/Sidebar', () => ({ default: () => null }));

function renderAt(url) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/reflections/:id" element={<ReflectionDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

const FULL_REFLECTION = {
  id: 91,
  language: 'en',
  period_start: '2026-06-08',
  period_end: '2026-06-14',
  team_visibility: 'supervisors_only',
  submitted_at: '2026-06-12T10:00:00Z',
  template_meta: {
    id: 7,
    name: 'Counselor weekly',
    cadence: 'weekly',
  },
  localized_schema: {
    fields: [
      {
        key: 'wins',
        type: 'short_text',
        prompts: { en: 'What went well?' },
      },
      {
        key: 'support',
        type: 'long_text',
        prompts: { en: 'Where do you need support?' },
      },
    ],
  },
  answers: {
    wins: 'Strong start',
    support: 'Some space to think',
  },
};

describe('ReflectionDetailPage', () => {
  beforeEach(() => {
    getMock.mockReset();
  });

  it('loads and renders prompts + answers with privacy chip when filed privately', async () => {
    getMock.mockResolvedValueOnce({ data: FULL_REFLECTION });
    renderAt('/reflections/91');

    await waitFor(() =>
      expect(screen.getByText('Counselor weekly')).toBeInTheDocument(),
    );

    expect(getMock).toHaveBeenCalledWith('/api/v1/reflections/91/');
    expect(screen.getByText('What went well?')).toBeInTheDocument();
    expect(screen.getByText('Strong start')).toBeInTheDocument();
    expect(screen.getByText('Where do you need support?')).toBeInTheDocument();
    expect(screen.getByText('Some space to think')).toBeInTheDocument();
    expect(screen.getByTestId('privacy-chip')).toBeInTheDocument();
  });

  it('renders a friendly panel on 403', async () => {
    getMock.mockRejectedValueOnce({ response: { status: 403 } });
    renderAt('/reflections/91');

    await waitFor(() =>
      expect(screen.getByText(/don.t have access/i)).toBeInTheDocument(),
    );
  });

  it('renders a friendly panel on 404', async () => {
    getMock.mockRejectedValueOnce({ response: { status: 404 } });
    renderAt('/reflections/91');

    await waitFor(() =>
      expect(screen.getByText(/reflection not found/i)).toBeInTheDocument(),
    );
  });

  it('hides the privacy chip when the reflection is not filed privately', async () => {
    getMock.mockResolvedValueOnce({
      data: { ...FULL_REFLECTION, team_visibility: 'team' },
    });
    renderAt('/reflections/91');

    await waitFor(() =>
      expect(screen.getByText('Counselor weekly')).toBeInTheDocument(),
    );

    expect(screen.queryByTestId('privacy-chip')).toBeNull();
  });

  it('renders textarea answers as formatted HTML, not raw tags', async () => {
    getMock.mockResolvedValueOnce({
      data: {
        ...FULL_REFLECTION,
        localized_schema: {
          fields: [
            {
              key: 'notes',
              type: 'textarea',
              prompts: { en: 'Notes' },
            },
          ],
        },
        answers: { notes: '<p>Great <strong>day</strong></p>' },
      },
    });
    renderAt('/reflections/91');

    await waitFor(() => expect(screen.getByText('Notes')).toBeInTheDocument());

    expect(screen.queryByText('<p>Great')).not.toBeInTheDocument();
    expect(screen.getByText('day')).toBeInTheDocument();
    const strong = document.querySelector('strong');
    expect(strong).not.toBeNull();
    expect(strong.textContent).toBe('day');
  });
});
