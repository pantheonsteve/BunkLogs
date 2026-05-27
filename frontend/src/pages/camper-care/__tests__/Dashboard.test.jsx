import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CamperCareDashboard from '../Dashboard';

const getMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
  window.sessionStorage.clear();
});

const samplePayload = {
  date: '2026-07-04',
  today: '2026-07-04',
  units: [
    {
      id: 100,
      name: 'Senior Village',
      bunks: [
        {
          id: 11,
          name: 'Cabin 1',
          slug: 'cabin-1',
          counselor_names: ['Pat L.'],
          completion: { submitted: 5, expected: 8, off_camp: 1 },
          badges: ['cc_flagged', 'low_completion'],
          camper_count: 9,
        },
        {
          id: 12,
          name: 'Cabin 2',
          slug: 'cabin-2',
          counselor_names: ['Sam R.'],
          completion: { submitted: 8, expected: 8, off_camp: 0 },
          badges: [],
          camper_count: 8,
        },
      ],
      completion: { submitted: 13, expected: 16 },
    },
  ],
  summary: { submitted: 13, expected: 16, flag_count: 2, order_count: 3 },
  self_reflection: { state: 'missing', reflection_id: null, template_id: 7, editable: false },
};

describe('CamperCareDashboard', () => {
  it('renders the caseload tree, summary, workspace entries, and self-reflection card', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(
      <MemoryRouter>
        <CamperCareDashboard />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('cc-dashboard')).toBeInTheDocument();
    });
    expect(screen.getByTestId('cc-summary-submitted')).toHaveTextContent('13 of 16');
    expect(screen.getByTestId('cc-workspace-flags-count')).toHaveTextContent('2');
    expect(screen.getByTestId('cc-workspace-orders-count')).toHaveTextContent('3');
    expect(screen.getByTestId('cc-unit-100')).toBeInTheDocument();
    expect(screen.getByTestId('cc-bunk-row-11')).toBeInTheDocument();
    expect(screen.getByTestId('cc-bunk-row-12')).toBeInTheDocument();
    expect(screen.getAllByTestId('cc-badge-cc_flagged').length).toBeGreaterThan(0);
    expect(screen.getByTestId('cc-self-reflection-state')).toHaveTextContent(/not yet/i);
    expect(screen.getByTestId('cc-self-reflection-action')).toHaveTextContent(/submit reflection/i);
  });

  it('shows the empty state when no units are on the caseload', async () => {
    getMock.mockResolvedValueOnce({
      data: {
        ...samplePayload,
        units: [],
        summary: { submitted: 0, expected: 0, flag_count: 0, order_count: 0 },
      },
    });
    render(
      <MemoryRouter>
        <CamperCareDashboard />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText(/No bunks on your caseload yet/i)).toBeInTheDocument();
    });
  });

  it('surfaces an error banner when the dashboard fetch fails', async () => {
    getMock.mockRejectedValueOnce({ response: { data: { detail: 'Forbidden' } } });
    render(
      <MemoryRouter>
        <CamperCareDashboard />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('cc-dashboard-error')).toHaveTextContent('Forbidden');
    });
  });

  it('persists collapsed units to sessionStorage and re-applies them on remount', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    const { unmount } = render(
      <MemoryRouter>
        <CamperCareDashboard />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('cc-unit-100')).toBeInTheDocument();
    });
    // Initially expanded.
    expect(screen.getByTestId('cc-unit-100')).toHaveAttribute('data-collapsed', 'false');
    fireEvent.click(screen.getByTestId('cc-unit-toggle-100'));
    expect(screen.getByTestId('cc-unit-100')).toHaveAttribute('data-collapsed', 'true');
    // Persisted.
    const stored = JSON.parse(window.sessionStorage.getItem('cc.dashboard.collapsedUnits'));
    expect(stored).toContain('100');
    unmount();
    // Remount — collapse state should survive within the same session.
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(
      <MemoryRouter>
        <CamperCareDashboard />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('cc-unit-100')).toBeInTheDocument();
    });
    expect(screen.getByTestId('cc-unit-100')).toHaveAttribute('data-collapsed', 'true');
  });

  it('links bunk rows to the per-bunk Camper Care dashboard (Story 18 c.9)', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(
      <MemoryRouter>
        <CamperCareDashboard />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('cc-bunk-link-11')).toBeInTheDocument();
    });
    expect(screen.getByTestId('cc-bunk-link-11')).toHaveAttribute(
      'href',
      '/dashboards/group/11',
    );
  });
});
