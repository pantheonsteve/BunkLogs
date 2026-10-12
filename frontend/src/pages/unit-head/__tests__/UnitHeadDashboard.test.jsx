import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import UnitHeadDashboard from '../UnitHeadDashboard';

const getMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

const summary = {
  today: '2026-07-04',
  bunks: [
    {
      id: 11, name: 'Bunk 24', unit_name: 'Chalutzim', counselor_names: ['Maya L.', 'Theo R.'],
      completion: { submitted: 1, expected: 2, off_camp: 0 }, badges: ['help_requested'],
    },
    {
      id: 12, name: 'Bunk 21', unit_name: 'Chalutzim', counselor_names: ['Ari G.'],
      completion: { submitted: 1, expected: 1, off_camp: 1 }, badges: [],
    },
  ],
  self_reflection: { state: 'missing', reflection_id: null, template_id: 9, editable: false },
};

const columns = [
  { label: 'social', field_key: 'camper_scores', field_type: 'rating_group', category_key: 'social', scale_max: 5, header: 'Social' },
  { label: 'behavior', field_key: 'camper_scores', field_type: 'rating_group', category_key: 'behavior', scale_max: 5, header: 'Behavior' },
  { label: 'notes', field_key: 'notes', field_type: 'textarea', category_key: null, scale_max: null, header: 'Notes' },
];

const camper = (id, first, last) => ({ id, first_name: first, last_name: last, preferred_name: null });

const bunk11 = {
  header: { bunk: { id: 11, name: 'Bunk 24' }, date: '2026-07-04', today: '2026-07-04' },
  help_requested: [camper(1, 'Theo', 'Marcus')],
  camper_care_help_requested: [camper(1, 'Theo', 'Marcus')],
  off_camp: [],
  score_grid: {
    columns,
    rows: [
      { camper: camper(1, 'Theo', 'Marcus'), reflection_id: 501, cells: { social: 2, behavior: 3, notes: '<p>Refused evening program.</p>' } },
      { camper: camper(2, 'Noah', 'Feldman'), reflection_id: null, cells: { social: null, behavior: null, notes: null } },
    ],
  },
};

const bunk12 = {
  header: { bunk: { id: 12, name: 'Bunk 21' }, date: '2026-07-04', today: '2026-07-04' },
  help_requested: [],
  camper_care_help_requested: [],
  off_camp: [camper(4, 'Leo', 'Sachs')],
  score_grid: {
    columns,
    rows: [
      { camper: camper(3, 'Ari', 'Gold'), reflection_id: 601, cells: { social: 5, behavior: 4, notes: 'Great day.' } },
      { camper: camper(4, 'Leo', 'Sachs'), reflection_id: null, cells: { social: null, behavior: null, notes: null } },
    ],
  },
};

const staff = {
  header: { date: '2026-07-04', today: '2026-07-04' },
  bunks: [{
    id: 11,
    name: 'Bunk 24',
    counselor_self_reflections: [
      { person_id: 70, counselor_name: 'Maya Levin', state: 'complete', answers: { overall_day: 2, staff_care_support_needed: true } },
      { person_id: 71, counselor_name: 'Theo Rubin', state: 'day_off', answers: {} },
    ],
  }],
};

function mockApi(overrides = {}) {
  const routes = {
    '/api/v1/unit-head/dashboard/': summary,
    '/api/v1/dashboards/group/11/': bunk11,
    '/api/v1/dashboards/group/12/': bunk12,
    '/api/v1/unit-head/staff-reflections/': staff,
    ...overrides,
  };
  getMock.mockImplementation((url) => Promise.resolve({ data: routes[url] }));
}

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={['/unit-head']}>
      <UnitHeadDashboard />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  getMock.mockReset();
});

describe('UnitHeadDashboard', () => {
  it('rolls up attention cards across bunks and shows a detail card per bunk', async () => {
    mockApi();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId('uh-attention-uh-help')).toHaveAttribute('data-count', '1');
    });
    expect(screen.getByTestId('uh-attention-cc-help')).toHaveAttribute('data-count', '1');
    expect(screen.getByTestId('uh-attention-off-camp')).toHaveAttribute('data-count', '1');
    expect(within(screen.getByTestId('uh-attention-off-camp')).getByText('Leo S.')).toBeInTheDocument();

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Chalutzim');
    expect(screen.getByText('2 bunks · 4 campers · 3 counselors')).toBeInTheDocument();
    expect(screen.getByTestId('uh-logs-progress')).toHaveTextContent('2 / 3');

    // Tiles link to the full dashboard; every bunk gets its own scores card.
    expect(screen.getByTestId('uh-bunk-card-11').getAttribute('href')).toMatch(/^\/dashboards\/group\/11/);
    const detail = screen.getByTestId('uh-detail-11');
    expect(detail).toHaveTextContent('Bunk 24 · Camper daily scores');
    const theo = within(detail).getByTestId('uh-detail-row-1');
    expect(theo).toHaveTextContent('Unit Head help');
    expect(theo).toHaveTextContent('Camper Care');
    expect(theo).toHaveTextContent('Refused evening program.');
    expect(within(detail).getByTestId('uh-detail-row-2')).toHaveTextContent('Not started');

    const second = screen.getByTestId('uh-detail-12');
    expect(second).toHaveTextContent('Bunk 21 · Camper daily scores');
    expect(within(second).getByTestId('uh-detail-row-4')).toHaveTextContent('Not on camp');

    expect(screen.getByTestId('uh-staff-70')).toHaveTextContent('Support');
    expect(screen.getByTestId('uh-staff-71')).toHaveTextContent('Day off');
    expect(screen.getByTestId('uh-self-reflection-state')).toHaveTextContent('Your reflection: not yet');
    expect(screen.getByTestId('uh-self-reflection-action')).toHaveTextContent('Write reflection');
  });

  it('switches the CTA to edit once the reflection is in', async () => {
    mockApi({
      '/api/v1/unit-head/dashboard/': {
        ...summary,
        self_reflection: { state: 'complete', reflection_id: 42, template_id: 9, editable: true },
      },
    });
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByTestId('uh-self-reflection-state')).toHaveTextContent('submitted');
    });
    expect(screen.getByTestId('uh-self-reflection-action')).toHaveTextContent('Edit reflection');
  });

  it('surfaces an error banner when the dashboard fetch fails', async () => {
    getMock.mockRejectedValueOnce({ response: { data: { detail: 'Boom' } } });
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Boom');
    });
  });
});
