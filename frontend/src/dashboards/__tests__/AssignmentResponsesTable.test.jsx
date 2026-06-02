import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AssignmentResponsesTable from '../AssignmentResponsesTable';

const block = {
  schema_fields: [
    {
      key: 'camper_scores',
      type: 'rating_group',
      scale: [1, 5],
      categories: [
        { key: 'behavior', labels: { en: 'Behavior — How was behavior?' } },
        { key: 'social', labels: { en: 'Social — Inclusion today?' } },
      ],
    },
    { key: 'daily_report', type: 'textarea', prompts: { en: 'Daily report' } },
    {
      key: 'not_on_camp',
      type: 'single_choice',
      prompts: { en: 'Camper not on camp today' },
      options: [{ value: 'no' }, { value: 'yes' }],
    },
  ],
  reflections: [
    {
      id: 1,
      date: '2025-07-17',
      subject: { id: 10, name: 'Ada Lovelace' },
      assignment_group: { id: 5, name: 'Bunk 4' },
      answers: {
        camper_scores: { behavior: 4, social: 5 },
        daily_report: 'Great day',
        not_on_camp: 'no',
      },
      language: 'en',
      team_visibility: 'team',
    },
  ],
};

function renderTable(props = {}) {
  return render(
    <MemoryRouter>
      <AssignmentResponsesTable block={block} {...props} />
    </MemoryRouter>,
  );
}

describe('AssignmentResponsesTable', () => {
  it('renders one column per template field including scores and text', () => {
    renderTable();
    expect(screen.getByRole('columnheader', { name: 'Behavior' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Social' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Daily report' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Camper not on camp today' })).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('Great day')).toBeInTheDocument();
  });

  it('shows group column when aggregating multiple groups', () => {
    renderTable({ showGroup: true });
    expect(screen.getByRole('columnheader', { name: 'Group' })).toBeInTheDocument();
    const groupLink = screen.getByRole('link', { name: 'Bunk 4' });
    expect(groupLink).toHaveAttribute('href', '/dashboards/group/5?date=2025-07-17');
  });

  it('does not render a date column', () => {
    renderTable();
    expect(screen.queryByRole('columnheader', { name: 'Date' })).not.toBeInTheDocument();
  });

  it('renders flag fields as coloured yes/no pills', () => {
    renderTable();
    expect(screen.getByText('No')).toHaveClass('bg-emerald-100');
  });
});
