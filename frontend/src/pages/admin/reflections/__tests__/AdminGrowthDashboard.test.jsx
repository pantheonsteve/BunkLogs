import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AdminGrowthDashboard from '../AdminGrowthDashboard';

const fetchMock = vi.fn();
const examplesMock = vi.fn();
const exportUrlMock = vi.fn();
vi.mock('../../../../api/adminGrowth', () => ({
  fetchAdminGrowth: (...args) => fetchMock(...args),
  fetchAdminGrowthExamples: (...args) => examplesMock(...args),
  exportAdminGrowthUrl: (...args) => exportUrlMock(...args),
}));

// jsdom has no canvas, so stand in for Chart.js entirely. The chart is a
// presentation detail; the assertions below cover the data the page derives.
const chartCtor = vi.fn();
vi.mock('chart.js', () => ({
  Chart: class {
    constructor(...args) {
      chartCtor(...args);
    }
    destroy() {}
  },
}));
vi.mock('chart.js/auto', () => ({}));

// The component still asks the canvas for a 2d context; jsdom logs a stack
// trace for that unless we stub it.
HTMLCanvasElement.prototype.getContext = () => ({});

const mockUseAuth = vi.fn();
vi.mock('../../../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// Pin tenant resolution to "unscoped host" so the single-org fixtures below
// resolve regardless of any local VITE_DEV_ORGANIZATION_SLUG.
vi.mock('../../../../utils/orgSlug', async (importOriginal) => ({
  ...(await importOriginal()),
  resolveOrganizationSlug: () => null,
}));

function adminIn(programTypes) {
  return {
    user: {
      organizations: [{
        slug: 'org',
        name: 'Org',
        capability: 'admin',
        roles: ['admin'],
        program_types: programTypes,
      }],
      membership_roles: ['admin'],
    },
    loading: false,
  };
}

const samplePayload = {
  header: {
    role: 'madrich',
    role_label: 'Madrich',
    program: { id: 1, name: 'TBE Religious School' },
    template: { id: 5, slug: 'tbe-madrich-3-2-1-weekly' },
    period: { start: '2026-09-01', end: '2027-05-31' },
    taxonomy_version: 'v1',
    coverage: { reflections: 10, tagged: 8, pending: 1, failed: 0, untagged: 1 },
  },
  taxonomy: [
    { key: 'classroom_management', label: 'Classroom management & behavior', complexity_tier: 1 },
    { key: 'conflict_resolution', label: 'Conflict & difficult conversations', complexity_tier: 3 },
    { key: 'other', label: 'Other', complexity_tier: 1 },
  ],
  grades: [
    {
      grade_level: 8,
      member_count: 4,
      reflection_count: 6,
      themes: [
        {
          theme_key: 'classroom_management',
          label: 'Classroom management & behavior',
          complexity_tier: 1,
          open_concern_count: 5,
          wins_count: 1,
          improvements_count: 0,
          total_count: 6,
          share_of_concerns: 1.0,
        },
      ],
      ratings: [{ category_key: 'initiative', label: 'Initiative', mean: 2.0, n: 6 }],
      concern_complexity_index: 1.0,
    },
    {
      grade_level: 11,
      member_count: 2,
      reflection_count: 4,
      themes: [
        {
          theme_key: 'conflict_resolution',
          label: 'Conflict & difficult conversations',
          complexity_tier: 3,
          open_concern_count: 4,
          wins_count: 0,
          improvements_count: 2,
          total_count: 6,
          share_of_concerns: 1.0,
        },
      ],
      ratings: [{ category_key: 'initiative', label: 'Initiative', mean: 3.5, n: 4 }],
      concern_complexity_index: 3.0,
    },
  ],
  milestones: [
    {
      metric_key: 'initiative',
      label: 'Initiative',
      by_grade: [
        { grade_level: 8, value: 2.0 },
        { grade_level: 11, value: 3.5 },
      ],
      slope: 0.5,
      direction: 'improving',
    },
    {
      metric_key: '__concern_complexity',
      label: 'Concern complexity index',
      by_grade: [
        { grade_level: 8, value: 1.0 },
        { grade_level: 11, value: 3.0 },
      ],
      slope: 0.6667,
      direction: 'improving',
    },
  ],
};

beforeEach(() => {
  fetchMock.mockReset();
  examplesMock.mockReset();
  exportUrlMock.mockReset();
  chartCtor.mockReset();
  exportUrlMock.mockReturnValue('/api/v1/admin/reflections/growth/export/');
  mockUseAuth.mockReset();
  mockUseAuth.mockReturnValue(adminIn(['religious_school']));
});

function renderAt(route = '/admin/reflections/growth') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AdminGrowthDashboard />
    </MemoryRouter>,
  );
}

describe('AdminGrowthDashboard', () => {
  it('contrasts what each grade raises and calls out the derived progression', async () => {
    fetchMock.mockResolvedValue(samplePayload);
    renderAt();

    await waitFor(() => expect(screen.getByText('Growth by grade')).toBeInTheDocument());

    // The headline answers the question the dashboard exists for.
    expect(screen.getByTestId('admin-growth-headline')).toHaveTextContent(
      /Older Madrichim are raising more sophisticated concerns/,
    );
    expect(screen.getByTestId('admin-growth-milestone-__concern_complexity')).toHaveTextContent(
      /Rising with grade/,
    );

    // Theme rows are ordered fundamentals-first and carry per-grade counts.
    const rows = screen.getAllByTestId(/^admin-growth-row-/);
    expect(rows.map((r) => r.getAttribute('data-testid'))).toEqual([
      'admin-growth-row-classroom_management',
      'admin-growth-row-conflict_resolution',
    ]);
    expect(screen.getByTestId('admin-growth-row-classroom_management')).toHaveTextContent('5');
    expect(screen.getByTestId('admin-growth-row-conflict_resolution')).toHaveTextContent('4');

    // Cohort sizes are surfaced so a thin grade can be discounted.
    expect(screen.getByTestId('admin-growth-cohort-11')).toHaveTextContent(
      '2 members, 4 reflections',
    );

    // Coverage warns that the picture is incomplete.
    expect(screen.getByTestId('admin-growth-coverage')).toHaveTextContent(
      /8 of 10 reflections categorized/,
    );
    expect(screen.getByTestId('admin-growth-coverage')).toHaveTextContent(
      /2 still uncategorized/,
    );

    expect(screen.getByTestId('admin-growth-export')).toHaveAttribute(
      'href',
      '/api/v1/admin/reflections/growth/export/',
    );
    // The chart is built in a passive effect, which React can flush after the
    // markup above is already assertable — so this has to be awaited.
    await waitFor(() => expect(chartCtor).toHaveBeenCalled());
  });

  it('renders an unavailable state for a camp organization', async () => {
    mockUseAuth.mockReturnValue(adminIn(['summer_camp']));
    renderAt();

    expect(screen.getByTestId('admin-growth-unavailable')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('refetches with the selected grade levels when a grade pill is toggled', async () => {
    fetchMock.mockResolvedValue(samplePayload);
    renderAt();
    // The pills are derived from the payload, so waiting on the fetch call
    // alone races the state flush that renders them.
    const pill = await screen.findByTestId('admin-growth-grade-8');
    expect(fetchMock).toHaveBeenCalledTimes(1);

    fireEvent.click(pill);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ gradeLevels: [8] }),
    );
  });

  it('loads excerpts on demand rather than shipping them in the main payload', async () => {
    fetchMock.mockResolvedValue(samplePayload);
    examplesMock.mockResolvedValue({
      items: [{
        reflection_id: 7,
        grade_level: 11,
        field_key: 'question_or_concern',
        dashboard_role: 'open_concern',
        period_start: '2026-10-05',
        excerpt: 'Two students keep fighting and I do not know what to do',
      }],
    });
    renderAt();
    await waitFor(() => expect(screen.getByText('Growth by grade')).toBeInTheDocument());

    // No free text until the Director explicitly drills in.
    expect(screen.queryByTestId('admin-growth-examples')).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('admin-growth-examples-conflict_resolution'));

    await waitFor(() =>
      expect(screen.getByTestId('admin-growth-examples')).toHaveTextContent(
        'Two students keep fighting and I do not know what to do',
      ),
    );
    expect(examplesMock).toHaveBeenCalledWith(
      expect.objectContaining({
        theme: 'conflict_resolution',
        dashboardRole: 'open_concern',
      }),
    );
  });

  it('surfaces a flat progression as a coaching signal', async () => {
    fetchMock.mockResolvedValue({
      ...samplePayload,
      milestones: [{
        metric_key: '__concern_complexity',
        label: 'Concern complexity index',
        by_grade: [
          { grade_level: 8, value: 2.0 },
          { grade_level: 11, value: 2.0 },
        ],
        slope: 0,
        direction: 'flat',
      }],
    });
    renderAt();

    await waitFor(() => expect(screen.getByTestId('admin-growth-headline')).toBeInTheDocument());
    expect(screen.getByTestId('admin-growth-headline')).toHaveTextContent(
      /not yet raising harder concerns .* worth coaching/,
    );
  });

  it('shows an error state when the request fails', async () => {
    fetchMock.mockRejectedValue({ response: { status: 403 } });
    renderAt();

    await waitFor(() => expect(screen.getByTestId('admin-growth-error')).toBeInTheDocument());
    expect(screen.getByTestId('admin-growth-error')).toHaveTextContent('Admin access required.');
  });
});
