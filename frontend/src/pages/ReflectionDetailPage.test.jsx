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

  it('renders subject header, rating cells, raised flags, and choice chips', async () => {
    getMock.mockResolvedValueOnce({
      data: {
        ...FULL_REFLECTION,
        subject: 5,
        subject_name: 'Ari Adler',
        author_name: 'Dov Roth',
        group_name: 'Bunk 24',
        localized_schema: {
          fields: [
            {
              key: 'scores', type: 'rating_group', prompts: { en: 'Today' }, scale: [1, 5],
              categories: [{ key: 'social', labels: { en: 'Social' } }],
            },
            {
              key: 'uh_help', type: 'single_choice', prompts: { en: 'Unit Head help' },
              options: [{ value: 'yes', labels: { en: 'Yes' } }, { value: 'no', labels: { en: 'No' } }],
            },
            {
              key: 'mood', type: 'single_choice', prompts: { en: 'Mood' },
              options: [{ value: 'happy', labels: { en: 'Happy' } }, { value: 'sad', labels: { en: 'Sad' } }],
            },
          ],
        },
        answers: { scores: { social: 4 }, uh_help: 'yes', mood: 'happy' },
      },
    });
    renderAt('/reflections/91');

    expect(await screen.findByRole('heading', { name: 'Ari Adler' })).toBeInTheDocument();
    expect(screen.getByTestId('reflection-subject-link').getAttribute('href')).toMatch(/^\/profile\/5/);
    expect(screen.getByText('Bunk 24')).toBeInTheDocument();
    expect(screen.getByText('Written by Dov Roth')).toBeInTheDocument();
    expect(screen.getByTestId('reflection-score-scores-social')).toHaveTextContent('4');
    expect(screen.getByTestId('reflection-flag-uh_help')).toHaveTextContent('Unit Head help');
    expect(screen.getByText('Happy')).toBeInTheDocument();
  });

  it('renders text_list answers as bullets ahead of trailing self-ratings', async () => {
    getMock.mockResolvedValueOnce({
      data: {
        ...FULL_REFLECTION,
        localized_schema: {
          fields: [
            { key: 'wins', type: 'text_list', prompts: { en: 'Three wins from this week' } },
            {
              key: 'ratings', type: 'rating_group', prompts: { en: 'Rate yourself' }, scale: [1, 4],
              categories: [{ key: 'initiative', labels: { en: 'Initiative' } }],
            },
          ],
        },
        answers: { wins: ['Learned names', 'Led a game'], ratings: { initiative: 3 } },
      },
    });
    renderAt('/reflections/91');

    expect(await screen.findByText('Learned names')).toBeInTheDocument();
    expect(screen.getByText('Led a game')).toBeInTheDocument();
    const responses = screen.getByTestId('reflection-text-answers');
    const scores = screen.getByTestId('reflection-scores');
    expect(responses.compareDocumentPosition(scores) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.queryByTestId('reflection-other-answers')).toBeNull();
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
