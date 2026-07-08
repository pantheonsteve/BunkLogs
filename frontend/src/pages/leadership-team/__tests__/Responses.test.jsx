import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import LeadershipTeamResponses from '../Responses';

const getMock = vi.fn();
vi.mock('../../../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

const authState = vi.hoisted(() => ({
  orgSlug: 'test-org',
  user: { role: 'Leadership Team' },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => authState,
}));

// Sidebar / Header / SingleDatePicker pull in auth + api side effects we
// don't care about in this test. Stub them to render-nothing so the test
// stays a focused integration test of the Responses page logic.
vi.mock('../../../partials/Sidebar', () => ({
  default: () => <div data-testid="stub-sidebar" />,
}));
vi.mock('../../../partials/Header', () => ({
  default: () => <div data-testid="stub-header" />,
}));
vi.mock('../../../components/ui/SingleDatePicker', () => ({
  default: ({ date }) => (
    <div data-testid="stub-date-picker">{date ? date.toISOString().slice(0, 10) : ''}</div>
  ),
}));

const templatePayload = {
  id: 7,
  name: 'KS Weekly',
  version: 1,
  role: 'kitchen_staff',
  subject_mode: 'other',
  schema: {
    fields: [
      {
        key: 'request_camper_care_help',
        type: 'single_choice',
        prompts: { en: 'Camper Care help requested' },
        options: [
          { value: 'yes', labels: { en: 'Yes' } },
          { value: 'no', labels: { en: 'No' } },
        ],
      },
      {
        key: 'request_unit_head_help',
        type: 'single_choice',
        prompts: { en: 'Unit Head help requested' },
        options: [
          { value: 'yes', labels: { en: 'Yes' } },
          { value: 'no', labels: { en: 'No' } },
        ],
      },
      {
        key: 'camper_scores',
        type: 'rating_group',
        scale: [1, 5],
        categories: [
          { key: 'behavior', labels: { en: 'Behavior' } },
          { key: 'participation', labels: { en: 'Participation' } },
        ],
      },
      {
        key: 'daily_report',
        type: 'textarea',
        prompts: { en: 'Daily report' },
      },
    ],
  },
};

const individualPayload = {
  tab: 'individual',
  template: { id: 7, slug: 'ks-weekly' },
  total: 2,
  page: 1,
  page_size: 25,
  results: [
    {
      id: 401,
      period_start: '2026-07-12',
      period_end: '2026-07-12',
      language: 'en',
      author: { id: 33, name: 'Asha Cook', email: 'asha@example.com' },
      subject: { id: 88, name: 'Rose Postman' },
      template_version: 1,
      created_at: '2026-07-12T18:00:00Z',
      answers: {
        request_camper_care_help: 'yes',
        request_unit_head_help: 'no',
        camper_scores: { behavior: 2, participation: 4 },
        daily_report: 'Rose had a tough afternoon.',
      },
    },
    {
      id: 402,
      period_start: '2026-07-12',
      period_end: '2026-07-12',
      language: 'en',
      author: { id: 33, name: 'Asha Cook', email: 'asha@example.com' },
      subject: { id: 89, name: 'Naomi Fossale' },
      template_version: 1,
      created_at: '2026-07-12T18:30:00Z',
      answers: {
        request_camper_care_help: 'no',
        request_unit_head_help: 'no',
        camper_scores: { behavior: 4, participation: 5 },
        daily_report: 'Great day.',
      },
    },
  ],
};

const selfReflectionTemplatePayload = {
  ...templatePayload,
  subject_mode: 'self',
  role: 'counselor',
};

const selfReflectionIndividualPayload = {
  ...individualPayload,
  total: 1,
  results: [
    {
      ...individualPayload.results[0],
      subject: { id: 88, name: 'Rose Postman' },
      author: { id: 88, name: 'Rose Postman' },
      groups: [
        { id: 501, name: 'Maple', group_type: 'bunk' },
        { id: 502, name: 'Unit A', group_type: 'unit' },
      ],
    },
  ],
};

// Matches the shape emitted by
// ``LeadershipTeamTemplateResponsesView._aggregate`` — language_distribution
// is a list of {language, count}, not a dict, and the dimensions key is
// ``avg_rating_per_dimension``.
const aggregatePayload = {
  tab: 'aggregate',
  total_responses: 2,
  response_volume_per_period: [{ period_start: '2026-07-12', count: 2 }],
  language_distribution: [{ language: 'en', count: 2 }],
  avg_rating_per_dimension: [
    {
      key: 'camper_scores__behavior',
      avg: 3.0,
      count: 2,
      scale_max: 5,
      distribution: { 1: 0, 2: 1, 3: 0, 4: 1, 5: 0 },
      versions: [1],
    },
  ],
  avg_rating_over_time: [
    { date: '2026-07-11', avg: 3.2, count: 3 },
    { date: '2026-07-12', avg: 3.5, count: 4 },
  ],
};

beforeEach(() => {
  getMock.mockReset();
  authState.user = { role: 'Leadership Team' };
});

function renderAt(route) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/admin/templates/:id/responses" element={<LeadershipTeamResponses />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LeadershipTeamResponses', () => {
  it('shows staff assignments under names for self-reflection templates', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/responses/')) {
        return Promise.resolve({ data: selfReflectionIndividualPayload });
      }
      return Promise.resolve({ data: selfReflectionTemplatePayload });
    });
    renderAt('/admin/templates/7/responses');

    const row = await screen.findByTestId('lt-responses-row-401');
    expect(within(row).getByRole('link', { name: 'Maple' })).toHaveAttribute(
      'href', expect.stringContaining('/dashboards/group/501'),
    );
    expect(within(row).getByRole('link', { name: 'Unit A' })).toHaveAttribute(
      'href', expect.stringContaining('/dashboards/group/502'),
    );
    expect(within(row).queryByText('Bunk')).not.toBeInTheDocument();
  });

  it('renders the redesigned individual tab with KPI cards, flag chips, and colour-coded ratings', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/responses/')) return Promise.resolve({ data: individualPayload });
      return Promise.resolve({ data: templatePayload });
    });
    renderAt('/admin/templates/7/responses');

    // Wait for the first row to land.
    const row1 = await screen.findByTestId('lt-responses-row-401');
    const row2 = screen.getByTestId('lt-responses-row-402');

    // Subject column shown with avatar + name. Name is now a link to the
    // per-subject dashboard, deep-linked to the current ?date= value so the
    // dashboard opens on the same day.
    const subjectLink = within(row1).getByRole('link', { name: 'Rose Postman' });
    expect(subjectLink).toHaveAttribute('href', expect.stringMatching(/^\/profile\/88\?date=/));
    expect(within(row2).getByRole('link', { name: 'Naomi Fossale' })).toHaveAttribute(
      'href', expect.stringMatching(/^\/profile\/89\?date=/),
    );

    // Colour-coded rating cells render the numeric value with an
    // aria-label of the form "<label>: <n> of <scaleMax>".
    expect(within(row1).getByLabelText('Behavior: 2 of 5')).toBeInTheDocument();
    expect(within(row1).getByLabelText('Participation: 4 of 5')).toBeInTheDocument();

    // Row 1 answered camper_care_help=yes -> flag chip rendered.
    expect(within(row1).getByTestId('lt-responses-flag-request_camper_care_help')).toBeInTheDocument();
    // Row 2 said no -> no chip.
    expect(within(row2).queryByTestId('lt-responses-flag-request_camper_care_help')).not.toBeInTheDocument();

    // Textarea content folded into the description cell.
    expect(within(row1).getByText('Rose had a tough afternoon.')).toBeInTheDocument();
    expect(within(row1).getByText(/Reporting Author/)).toBeInTheDocument();
    expect(within(row1).getByText(/asha@example.com/)).toBeInTheDocument();

    // KPI cards: Total Log Entries + one per yes/no flag field. Camper-care
    // counter shows 1 (row 401), Unit-Head shows 0.
    expect(screen.getByTestId('lt-kpi-total-log-entries')).toHaveTextContent('2');
    expect(screen.getByTestId('lt-kpi-camper-care-help-requested')).toHaveTextContent('1');
    expect(screen.getByTestId('lt-kpi-unit-head-help-requested')).toHaveTextContent('0');

    // Export href carries the synthesized date_from/date_to from the
    // single-day stepper.
    expect(screen.getByTestId('lt-responses-export')).toHaveAttribute('href', expect.stringContaining('/responses/export/'));
  });

  it('renders a mobile response card per row with name, score boxes, and narrative', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/responses/')) return Promise.resolve({ data: individualPayload });
      return Promise.resolve({ data: templatePayload });
    });
    renderAt('/admin/templates/7/responses');
    const card = await screen.findByTestId('lt-responses-card-401');

    // Sticky header shows the camper name as a link to their profile.
    const nameLink = within(card).getByRole('link', { name: 'Rose Postman' });
    expect(nameLink).toHaveAttribute('href', expect.stringMatching(/^\/profile\/88\?date=/));

    // Colored score boxes reuse the same aria-labels as the table cells.
    expect(within(card).getByLabelText('Behavior: 2 of 5')).toBeInTheDocument();
    expect(within(card).getByLabelText('Participation: 4 of 5')).toBeInTheDocument();

    // Narrative body: description text + reporting author + yes-flag chip.
    expect(within(card).getByText('Rose had a tough afternoon.')).toBeInTheDocument();
    expect(within(card).getByText(/Reporting Author/)).toBeInTheDocument();
    expect(within(card).getByTestId('lt-responses-card-flag-request_camper_care_help')).toBeInTheDocument();
  });

  it('clicking the Camper Care KPI filters the table to yes-only rows', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/responses/')) return Promise.resolve({ data: individualPayload });
      return Promise.resolve({ data: templatePayload });
    });
    renderAt('/admin/templates/7/responses');
    await screen.findByTestId('lt-responses-row-401');
    expect(screen.getByTestId('lt-responses-row-402')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('lt-kpi-camper-care-help-requested'));

    await waitFor(() =>
      expect(screen.queryByTestId('lt-responses-row-402')).not.toBeInTheDocument(),
    );
    expect(screen.getByTestId('lt-responses-row-401')).toBeInTheDocument();
  });

  it('name search filters rows client-side', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/responses/')) return Promise.resolve({ data: individualPayload });
      return Promise.resolve({ data: templatePayload });
    });
    renderAt('/admin/templates/7/responses');
    await screen.findByTestId('lt-responses-row-401');

    fireEvent.change(screen.getByTestId('lt-responses-search'), { target: { value: 'naomi' } });

    await waitFor(() =>
      expect(screen.queryByTestId('lt-responses-row-401')).not.toBeInTheDocument(),
    );
    expect(screen.getByTestId('lt-responses-row-402')).toBeInTheDocument();
  });

  it('routes admin back link to reflections dashboard preserving date', async () => {
    authState.user = { role: 'Admin' };
    getMock.mockImplementation((url) => {
      if (url.includes('/responses/')) return Promise.resolve({ data: individualPayload });
      return Promise.resolve({ data: templatePayload });
    });
    renderAt('/admin/templates/7/responses?date=2026-06-03');
    const back = await screen.findByTestId('lt-responses-back');
    expect(back).toHaveAttribute('href', '/dashboards/reflections?date=2026-06-03');
    expect(back).toHaveTextContent('← Reflections');
  });

  it('routes admin to bunk logs dashboard when opened from logs hub', async () => {
    authState.user = { role: 'Admin' };
    getMock.mockImplementation((url) => {
      if (url.includes('/responses/')) return Promise.resolve({ data: individualPayload });
      return Promise.resolve({ data: templatePayload });
    });
    renderAt('/admin/templates/7/responses?date=2026-06-03&dashboard=logs');
    const back = await screen.findByTestId('lt-responses-back');
    expect(back).toHaveAttribute('href', '/dashboards/logs?date=2026-06-03');
    expect(back).toHaveTextContent('← Bunk Logs');
  });

  it('switches to the aggregate tab and shows rating pie charts with averages', async () => {
    getMock.mockImplementation((url, { params } = {}) => {
      if (!url.includes('/responses/')) return Promise.resolve({ data: templatePayload });
      if (params?.tab === 'aggregate') return Promise.resolve({ data: aggregatePayload });
      return Promise.resolve({ data: individualPayload });
    });
    renderAt('/admin/templates/7/responses?date=2026-07-12');
    await screen.findByTestId('lt-responses-row-401');
    fireEvent.click(screen.getByTestId('lt-responses-tab-aggregate'));
    await waitFor(() =>
      expect(screen.getByTestId('lt-responses-dim-camper_scores__behavior')).toBeInTheDocument(),
    );
    expect(screen.getByText('3.00')).toBeInTheDocument();
    expect(screen.getByTestId('lt-responses-trend-chart')).toBeInTheDocument();
    expect(screen.getByTestId('lt-responses-prev-day')).toBeInTheDocument();
  });

  it('navigates to a trend chart date when clicking a point', async () => {
    getMock.mockImplementation((url, { params } = {}) => {
      if (!url.includes('/responses/')) return Promise.resolve({ data: templatePayload });
      if (params?.tab === 'aggregate') return Promise.resolve({ data: aggregatePayload });
      return Promise.resolve({ data: individualPayload });
    });
    renderAt('/admin/templates/7/responses?date=2026-07-12&tab=aggregate');
    await waitFor(() =>
      expect(screen.getByTestId('lt-responses-trend-point-2026-07-11')).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId('lt-responses-trend-point-2026-07-11'));

    await waitFor(() => {
      const responseCalls = getMock.mock.calls.filter(
        ([url, config]) =>
          url.includes('/responses/')
          && config?.params?.tab === 'aggregate'
          && config?.params?.date_from === '2026-07-11',
      );
      expect(responseCalls.length).toBeGreaterThan(0);
    });
  });
});
