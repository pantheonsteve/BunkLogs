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

beforeEach(() => {
  getMock.mockReset();
});

const samplePayload = {
  today: '2026-07-04',
  bunks: [
    {
      id: 11,
      name: 'Alpha',
      slug: 'alpha',
      unit_name: 'Unit One',
      counselor_names: ['Pat L.'],
      completion: { submitted: 5, expected: 8, off_camp: 1 },
      badges: ['help_requested', 'low_completion'],
    },
    {
      id: 12,
      name: 'Bravo',
      slug: 'bravo',
      unit_name: 'Unit One',
      counselor_names: ['Sam R.'],
      completion: { submitted: 8, expected: 8, off_camp: 0 },
      badges: [],
    },
  ],
  self_reflection: {
    state: 'missing',
    reflection_id: null,
    template_id: 9,
    editable: false,
  },
};

describe('UnitHeadDashboard', () => {
  it('renders supervised bunks with badges and completion stats', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(
      <MemoryRouter>
        <UnitHeadDashboard />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('uh-bunk-row-11')).toBeInTheDocument();
    });
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('5 of 8 submitted')).toBeInTheDocument();
    expect(screen.getByText('1 off-camp')).toBeInTheDocument();
    const helpBadges = screen.getAllByTestId('uh-badge-help_requested');
    expect(helpBadges.length).toBeGreaterThan(0);
  });

  it('renders the empty-state message when no bunks are supervised', async () => {
    getMock.mockResolvedValueOnce({
      data: { ...samplePayload, bunks: [] },
    });
    render(
      <MemoryRouter>
        <UnitHeadDashboard />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText(/No supervised bunks yet/i)).toBeInTheDocument();
    });
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
