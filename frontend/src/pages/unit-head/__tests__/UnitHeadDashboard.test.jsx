import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import UnitHeadDashboard from '../UnitHeadDashboard';

const getMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

vi.mock('../../../dashboards/performance/PerformanceDashboard', () => ({
  default: ({ embedded }) => (
    <div data-testid={embedded ? 'performance-dashboard-embedded' : 'performance-dashboard'}>
      Performance dashboard
    </div>
  ),
}));

beforeEach(() => {
  getMock.mockReset();
});

const samplePayload = {
  today: '2026-07-04',
  self_reflection: {
    state: 'missing',
    reflection_id: null,
    template_id: 9,
    editable: false,
  },
};

describe('UnitHeadDashboard', () => {
  it('renders the embedded performance dashboard instead of the bunk list', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(
      <MemoryRouter initialEntries={['/unit-head']}>
        <UnitHeadDashboard />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('performance-dashboard-embedded')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('uh-bunks')).not.toBeInTheDocument();
    expect(screen.queryByTestId('uh-bunk-row-11')).not.toBeInTheDocument();
  });

  it('shows the self-reflection "Submit reflection" CTA when state is missing', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(
      <MemoryRouter>
        <UnitHeadDashboard />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('uh-self-reflection-state')).toHaveTextContent(/not yet/i);
    });
    expect(screen.getByTestId('uh-self-reflection-action')).toHaveTextContent(/submit reflection/i);
  });

  it('shows the "Edit reflection" CTA when self-reflection is complete', async () => {
    getMock.mockResolvedValueOnce({
      data: {
        ...samplePayload,
        self_reflection: {
          state: 'complete',
          reflection_id: 42,
          template_id: 9,
          editable: true,
        },
      },
    });
    render(
      <MemoryRouter>
        <UnitHeadDashboard />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('uh-self-reflection-state')).toHaveTextContent('Submitted');
    });
    expect(screen.getByTestId('uh-self-reflection-action')).toHaveTextContent(/edit reflection/i);
  });

  it('surfaces an error banner when the dashboard fetch fails', async () => {
    getMock.mockRejectedValueOnce({ response: { data: { detail: 'Boom' } } });
    render(
      <MemoryRouter>
        <UnitHeadDashboard />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Boom');
    });
  });
});
