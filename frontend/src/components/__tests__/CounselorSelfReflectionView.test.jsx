import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import CounselorSelfReflectionView from '../CounselorSelfReflectionView';

describe('CounselorSelfReflectionView', () => {
  const entry = {
    person_id: 7,
    counselor_name: 'Pat Lee',
    submitted_at: '2026-07-07T18:00:00Z',
    answers: {
      day_quality_score: 5,
      support_level_score: 3,
      elaboration: '<p>Great day</p>',
    },
    schema_fields: [
      {
        key: 'day_quality_score',
        type: 'single_rating',
        scale: [1, 5],
        prompts: { en: 'How was your day?' },
      },
      {
        key: 'support_level_score',
        type: 'single_rating',
        scale: [1, 5],
        prompts: { en: 'Support level' },
      },
      {
        key: 'elaboration',
        type: 'textarea',
        prompts: { en: 'Elaborate' },
      },
    ],
  };

  it('renders mobile score boxes and desktop table from schema + answers', () => {
    render(<CounselorSelfReflectionView entry={entry} />);
    const mobile = screen.getByTestId('counselor-self-refl-mobile-7');
    expect(mobile).toBeInTheDocument();
    expect(within(mobile).getByLabelText('How was your day?: 5 of 5')).toBeInTheDocument();
    expect(within(mobile).getByLabelText('Support level: 3 of 5')).toBeInTheDocument();
    expect(screen.getByTestId('counselor-self-refl-table-7')).toBeInTheDocument();
    expect(within(mobile).getByText('Great day').tagName).toBe('P');
  });

  it('falls back to legacy field list when schema_fields are absent', () => {
    render(
      <CounselorSelfReflectionView
        entry={{
          person_id: 8,
          fields: [{ key: 'note', label: 'Note', value: 'Hello' }],
        }}
      />,
    );
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.queryByTestId('counselor-self-refl-mobile-8')).not.toBeInTheDocument();
  });
});
