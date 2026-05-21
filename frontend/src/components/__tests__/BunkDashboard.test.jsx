import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import BunkDashboard from '../BunkDashboard';

function renderDash(data, extra = {}) {
  return render(
    <MemoryRouter>
      <BunkDashboard data={data} selectedDate={data?.header?.date} {...extra} />
    </MemoryRouter>,
  );
}

const baseData = {
  header: {
    today: '2026-07-04',
    date: '2026-07-04',
    bunk: { id: 1, name: 'Bunk Alpha', unit_name: 'Unit One' },
    counselor_names: ['Pat L.', 'Sam R.'],
  },
  help_requested: [],
  off_camp: [],
  bunk_concerns: [],
  score_grid: { columns: [], rows: [] },
  orders: { today: [], carried_over: [], counts: { open: 0, in_progress: 0, resolved: 0 } },
  specialist_reports: { today: [], recent: [], sensitive_counts_by_camper: {} },
};

describe('BunkDashboard', () => {
  it('renders the bunk header with name + unit', () => {
    renderDash(baseData);
    expect(screen.getByText('Bunk Alpha')).toBeInTheDocument();
    expect(screen.getByText('Unit One')).toBeInTheDocument();
  });

  it('collapses empty sections to single-line summary', () => {
    renderDash(baseData);
    expect(screen.getByTestId('section-help-requested')).toHaveAttribute('data-state', 'empty');
    expect(screen.getByTestId('section-off-camp')).toHaveAttribute('data-state', 'empty');
    expect(screen.getByTestId('section-bunk-concerns')).toHaveAttribute('data-state', 'empty');
  });

  it('renders help requested + bunk concerns when populated', () => {
    const data = {
      ...baseData,
      help_requested: [{ id: 9, first_name: 'Jamie', last_name: 'Pat', preferred_name: null }],
      bunk_concerns: [{
        reflection_id: 42,
        author: 'Pat L.',
        author_role: 'counselor',
        note: 'Worried about cabin dynamics',
      }],
    };
    renderDash(data);
    expect(screen.getByTestId('section-help-requested')).toHaveAttribute('data-state', 'populated');
    expect(screen.getByTestId('camper-pill-9')).toBeInTheDocument();
    expect(screen.getByTestId('bunk-concern-42')).toHaveTextContent('Worried about cabin dynamics');
  });

  it('shows the score grid when the payload includes campers + columns', () => {
    const data = {
      ...baseData,
      score_grid: {
        columns: [{ label: 'social', field_type: 'rating_group', category_key: 'social', scale_max: 5 }],
        rows: [{
          camper: { id: 1, first_name: 'A', last_name: 'B', preferred_name: 'A' },
          cells: { social: 4 },
          reflection_id: 99,
        }],
      },
    };
    renderDash(data);
    expect(screen.getByTestId('score-grid')).toBeInTheDocument();
    expect(screen.getByTestId('score-row-1')).toBeInTheDocument();
  });

  it('orders section counts open / in-progress / resolved', () => {
    const data = {
      ...baseData,
      orders: {
        today: [
          { id: 1, kind: 'maintenance', location: 'Cabin 3 bathroom', status: 'new', submitter: 'Pat', submitted_at: '2026-07-04T12:00:00Z' },
        ],
        carried_over: [
          { id: 2, kind: 'camper_care', item: 'Lice check', status: 'in_progress', submitter: 'Sam', submitted_at: '2026-07-03T12:00:00Z' },
        ],
        counts: { open: 1, in_progress: 1, resolved: 0 },
      },
    };
    renderDash(data);
    expect(screen.getByTestId('section-orders')).toHaveAttribute('data-state', 'populated');
    expect(screen.getByTestId('order-1')).toHaveTextContent('Cabin 3 bathroom');
    expect(screen.getByTestId('order-2')).toHaveTextContent('Lice check');
  });

  it('surfaces sensitive-note counts when notes are excluded', () => {
    const data = {
      ...baseData,
      specialist_reports: {
        today: [],
        recent: [],
        sensitive_counts_by_camper: { 1: 1, 2: 2 },
      },
    };
    renderDash(data);
    const section = screen.getByTestId('section-specialist-reports');
    expect(section).toHaveAttribute('data-state', 'populated');
    expect(section).toHaveTextContent('3 sensitive notes');
  });
});
