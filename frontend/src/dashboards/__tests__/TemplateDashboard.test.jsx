import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TemplateDashboard from '../TemplateDashboard';

const getMock = vi.fn();

vi.mock('../../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({ user: null }),
}));

const samplePayload = {
  template: {
    id: 1,
    name: 'LT Weekly',
    slug: 'lt-weekly',
    role: 'leadership_team',
    schema: {
      fields: [
        {
          key: 'overall',
          type: 'single_rating',
          dashboard_role: 'primary_rating',
          scale: [1, 5],
          prompts: { en: 'How are you overall?' },
        },
        {
          key: 'pulse',
          type: 'rating_group',
          dashboard_role: 'category_ratings',
          scale: [1, 4],
          categories: [{ key: 'morale', labels: { en: 'Morale' } }],
        },
        {
          key: 'notes',
          type: 'text',
          dashboard_role: null,
          prompts: { en: 'Extra notes' },
        },
      ],
    },
  },
  period: {
    current_start: '2026-06-01',
    current_end: '2026-06-14',
    prior_start: '2026-05-18',
    prior_end: '2026-05-31',
  },
  summary: { person_count: 5, response_count: 4, eligible_count: 6, completion_rate: 0.667 },
  fields: [
    {
      key: 'overall',
      type: 'single_rating',
      dashboard_role: 'primary_rating',
      data: {
        mean: 3.5,
        prior_mean: 3.0,
        trend: 'up',
        response_count: 4,
        distribution: { '1': 0, '2': 0, '3': 1, '4': 3, '5': 0 },
      },
    },
    {
      key: 'pulse',
      type: 'rating_group',
      dashboard_role: 'category_ratings',
      data: {
        categories: [
          { key: 'morale', mean: 3.8, prior_mean: 3.2, trend: 'up', response_count: 4, distribution: {} },
        ],
      },
    },
    {
      key: 'notes',
      type: 'text',
      dashboard_role: null,
      data: { items: [{ reflection_id: 1, person_id: 1, period_end: '2026-06-14', text: 'Sample note', is_read: false }], total: 1 },
    },
  ],
};

function renderDashboard(props = {}) {
  return render(
    <MemoryRouter>
      <TemplateDashboard templateId={1} {...props} />
    </MemoryRouter>,
  );
}

describe('TemplateDashboard', () => {
  beforeEach(() => {
    getMock.mockReset();
    getMock.mockResolvedValue({ data: samplePayload });
  });

  it('shows loading state initially', () => {
    getMock.mockReturnValue(new Promise(() => {}));
    renderDashboard();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders summary bar after load', async () => {
    renderDashboard();
    await waitFor(() => expect(getMock).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText('66.7%')).toBeInTheDocument());
    expect(screen.getByText('4')).toBeInTheDocument(); // response count
  });

  it('renders role-tagged widgets', async () => {
    renderDashboard();
    await waitFor(() => expect(screen.getByText('3.5')).toBeInTheDocument());
    expect(screen.getByText(/3\.8/)).toBeInTheDocument();
  });

  it('generic fields hidden until expanded', async () => {
    renderDashboard();
    await waitFor(() => expect(getMock).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.getByText(/additional fields/i)).toBeInTheDocument(),
    );
    expect(screen.queryByText('Sample note')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText(/additional fields/i));
    await waitFor(() =>
      expect(screen.getByText('Sample note')).toBeInTheDocument(),
    );
  });

  it('shows access denied message on 403', async () => {
    getMock.mockRejectedValueOnce({ response: { status: 403 } });
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText(/access restricted/i)).toBeInTheDocument(),
    );
  });

  it('shows error message on other failure', async () => {
    getMock.mockRejectedValueOnce({ response: { status: 500, data: { detail: 'Server error' } } });
    renderDashboard();
    await waitFor(() => expect(screen.getByText('Server error')).toBeInTheDocument());
  });

  it('calls API with template id', async () => {
    renderDashboard({ templateId: 42 });
    await waitFor(() => expect(getMock).toHaveBeenCalledWith(
      '/api/v1/dashboards/template/42/',
      expect.any(Object),
    ));
  });

  it('renders title prop', async () => {
    renderDashboard({ title: 'Custom Title' });
    await waitFor(() => expect(screen.getByText('Custom Title')).toBeInTheDocument());
  });
});
