import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GroupTemplateResponses from '../GroupTemplateResponses';

vi.mock('../../api/observations', () => ({
  fetchRecipientCandidates: vi.fn(() => Promise.resolve([])),
  searchObservationSubjects: vi.fn(() => Promise.resolve([])),
  createObservation: vi.fn(),
  SENSITIVITY_OPTIONS: [{ value: 'normal', label: 'Normal' }],
}));

const templates = [
  {
    template: { id: 16, name: 'Camper daily check-in', slug: 'camper-daily' },
    schema_fields: [
      { key: 'daily_report', type: 'textarea', prompts: { en: 'Daily report' } },
    ],
    summary: { total_reflections: 1, flag_counts: {} },
    rating_series: [],
    reflections: [
      {
        id: 228,
        date: '2026-06-03',
        language: 'en',
        team_visibility: 'team',
        subject: { id: 42, name: 'Alex Cohen' },
        answers: { daily_report: 'Had a good day.' },
      },
    ],
  },
];

describe('GroupTemplateResponses', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows Note + on form-response rows and opens the observation composer', async () => {
    render(
      <MemoryRouter>
        <GroupTemplateResponses
          templates={templates}
          profileLinkContext={{ groupId: 78, date: '2026-06-03' }}
        />
      </MemoryRouter>,
    );

    expect(screen.getByTestId('group-template-add-observation-228')).toHaveTextContent('Note +');
    fireEvent.click(screen.getByTestId('group-template-add-observation-228'));

    await waitFor(() => {
      expect(screen.getByTestId('observation-composer-observed-at')).toHaveValue('2026-06-03T12:00');
    });
    expect(screen.getByTestId('observation-subject-chips')).toHaveTextContent('Alex Cohen');
  });
});
