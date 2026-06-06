import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
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
  camper_care_help_requested: [],
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

  it('shows empty summary cards when nothing needs attention', () => {
    renderDash(baseData);
    expect(screen.getByTestId('card-not-on-camp')).toHaveAttribute('data-count', '0');
    expect(screen.getByTestId('card-uh-help')).toHaveAttribute('data-count', '0');
    expect(screen.getByTestId('card-cc-help')).toHaveAttribute('data-count', '0');
  });

  it('lists off-camp campers in the Not on Camp card and UH help campers', () => {
    const data = {
      ...baseData,
      off_camp: [{ id: 5, first_name: 'Lee', last_name: 'Ng', preferred_name: null, off_camp: true }],
      help_requested: [{ id: 9, first_name: 'Jamie', last_name: 'Pat', preferred_name: null }],
    };
    renderDash(data);
    expect(within(screen.getByTestId('card-not-on-camp')).getByText('Lee N.')).toBeInTheDocument();
    expect(within(screen.getByTestId('card-uh-help')).getByText('Jamie P.')).toBeInTheDocument();
  });

  it('lists Camper Care help campers from the payload', () => {
    const data = {
      ...baseData,
      camper_care_help_requested: [
        { id: 33, first_name: 'Rae', last_name: 'Kim', preferred_name: null },
      ],
    };
    renderDash(data);
    const card = screen.getByTestId('card-cc-help');
    expect(card).toHaveAttribute('data-count', '1');
    expect(within(card).getByText('Rae K.')).toBeInTheDocument();
  });

  it('shows the score grid with an On Camp column and hides triage columns', () => {
    const data = {
      ...baseData,
      off_camp: [{ id: 2, first_name: 'Bo', last_name: 'Lee', preferred_name: null, off_camp: true }],
      score_grid: {
        columns: [
          { label: 'on_camp', field_key: 'on_camp', field_type: 'single_choice', category_key: null, scale_max: null, header: 'Was the camper on camp today?' },
          { label: 'social', field_key: 'camper_scores', field_type: 'rating_group', category_key: 'social', scale_max: 5, header: 'Social' },
        ],
        rows: [
          { camper: { id: 1, first_name: 'A', last_name: 'B', preferred_name: 'A' }, cells: { on_camp: 'yes', social: 4 }, reflection_id: 99 },
          { camper: { id: 2, first_name: 'Bo', last_name: 'Lee', preferred_name: null }, cells: { on_camp: null, social: null }, reflection_id: null },
        ],
      },
    };
    renderDash(data);
    expect(screen.getByTestId('score-grid')).toBeInTheDocument();
    // Dedicated authoritative On Camp column is present...
    expect(screen.getByTestId('score-col-oncamp')).toBeInTheDocument();
    // ...and the redundant single_choice on-camp template column is hidden.
    expect(screen.queryByTestId('score-col-on_camp')).not.toBeInTheDocument();
    expect(screen.getByTestId('score-col-social')).toBeInTheDocument();
  });

  it('derives the completion badge from expected (on-camp) rows', () => {
    const data = {
      ...baseData,
      off_camp: [{ id: 2, first_name: 'Bo', last_name: 'Lee', preferred_name: null, off_camp: true }],
      score_grid: {
        columns: [{ label: 'social', field_type: 'rating_group', category_key: 'social', scale_max: 5 }],
        rows: [
          { camper: { id: 1, first_name: 'A', last_name: 'B', preferred_name: 'A' }, cells: { social: 4 }, reflection_id: 99 },
          { camper: { id: 2, first_name: 'Bo', last_name: 'Lee', preferred_name: null }, cells: { social: null }, reflection_id: null },
        ],
      },
    };
    renderDash(data);
    expect(screen.getByTestId('bunk-completion')).toHaveTextContent('1 of 1 reflections submitted');
  });

  it('orders section counts open / in-progress / resolved', () => {
    const data = {
      ...baseData,
      orders: {
        today: [
          { id: 1, kind: 'maintenance', location: 'Cabin 3 bathroom', status: 'new', submitter: 'Pat', submitted_at: '2026-07-04T12:00:00Z' },
        ],
        carried_over: [
          { id: 2, kind: 'camper_care', item: 'Lice check', status: 'in_progress', submitter: 'Sam', submitted_at: '2026-07-03T12:00:00Z', subject: { id: 8, first_name: 'Q', last_name: 'Z', preferred_name: null } },
        ],
        counts: { open: 1, in_progress: 1, resolved: 0 },
      },
    };
    renderDash(data);
    expect(screen.getByTestId('section-orders')).toHaveAttribute('data-state', 'populated');
    expect(screen.getByTestId('order-1')).toHaveTextContent('Cabin 3 bathroom');
    expect(screen.getByTestId('order-2')).toHaveTextContent('Lice check');
  });

  it('renders notes in a single stream with tags and sensitive-note footnote', () => {
    const data = {
      ...baseData,
      bunk_concerns: [{
        reflection_id: 42,
        author: 'Pat L.',
        author_role: 'counselor',
        note: 'Worried about cabin dynamics',
        submitted_at: '2026-07-04T14:00:00Z',
      }],
      observations: [{
        id: 7,
        body_preview: 'Checked in after lunch.',
        author_name: 'Sam R.',
        subjects: [{ id: 3, name: 'Jamie Pat' }],
        sensitivity: 'sensitive',
        context: 'mealtime',
        observed_at: '2026-07-04T16:00:00Z',
      }],
      specialist_reports: { today: [], recent: [], sensitive_counts_by_camper: { 1: 1, 2: 2 } },
    };
    renderDash(data);
    const section = screen.getByTestId('section-notes');
    expect(section).toHaveAttribute('data-state', 'populated');
    expect(screen.getByTestId('notes-stream')).toBeInTheDocument();
    expect(screen.queryByText('Bunk concerns')).not.toBeInTheDocument();
    expect(screen.queryByText('Specialist reports')).not.toBeInTheDocument();
    expect(screen.getByTestId('bunk-observation-7')).toHaveTextContent('Checked in after lunch.');
    expect(screen.getByRole('link', { name: /Checked in after lunch/ })).toHaveAttribute(
      'href',
      '/observations/7',
    );
    expect(screen.getByTestId('bunk-observation-7')).toHaveTextContent('Unit Heads and above');
    expect(screen.getByTestId('bunk-observation-7')).toHaveTextContent('mealtime');
    expect(screen.getByTestId('bunk-concern-42')).toHaveTextContent('Worried about cabin dynamics');
    expect(screen.getByTestId('bunk-concern-42')).toHaveTextContent('Bunk concern');
    expect(section).toHaveTextContent('3 sensitive notes');
  });

  it('links observations back to the group dashboard when profileLinkContext is set', () => {
    const data = {
      ...baseData,
      observations: [{
        id: 12,
        body_preview: 'Evening check-in.',
        author_name: 'Pat L.',
        subjects: [{ id: 3, name: 'Jamie Pat' }],
        sensitivity: 'normal',
        observed_at: '2026-07-04T20:00:00Z',
      }],
    };
    renderDash(data, {
      profileLinkContext: { groupId: 78, date: '2026-07-04' },
    });
    const link = screen.getByRole('link', { name: /Evening check-in/ });
    expect(link.getAttribute('href')).toBe(
      '/observations/12?from=%2Fdashboards%2Fgroup%2F78%3Fdate%3D2026-07-04&from_label=Bunk+Alpha',
    );
  });
});
