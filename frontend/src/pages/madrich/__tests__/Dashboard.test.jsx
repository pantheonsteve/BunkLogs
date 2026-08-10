/**
 * Madrich dashboard tests — Step 7_14, Stories 61 and 63.
 *
 * Covers cadence framing (labels derive from each card's server-provided
 * period, Story 61 criterion 5), state→CTA mapping, several concurrent
 * templates rendering as separate cards (Story 63), and the absence of
 * camp-side surfaces.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MadrichDashboard from '../Dashboard';

const getMock = vi.fn();
vi.mock('../../../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'tbe', user: { id: 7 } }),
}));

const weeklyCard = {
  template_id: 12,
  template_name: 'TBE Madrich Weekly 3-2-1',
  cadence: 'weekly',
  recurring: true,
  period: { start: '2026-09-07', end: '2026-09-13' },
  state: 'missing',
  reflection_id: null,
  editable: false,
};

const samplePayload = {
  today: '2026-09-09',
  period: { start: '2026-09-07', end: '2026-09-13', cadence: 'weekly' },
  header: {
    name: 'Maya Madrich',
    role_label: 'Madrich',
    grade_level: 10,
    program_name: 'TBE Religious School 2026-27',
    preferred_language: 'en',
  },
  my_reflections: [weeklyCard],
  history_entry: { url: '/madrich/history' },
};

function payloadWith(...cards) {
  return { ...samplePayload, my_reflections: cards };
}

beforeEach(() => {
  getMock.mockReset();
});

describe('MadrichDashboard', () => {
  it('renders header with name, role, grade, and program', async () => {
    getMock.mockResolvedValue({ data: samplePayload });
    render(<MemoryRouter><MadrichDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByText('Maya Madrich'));
    expect(screen.getByText('TBE Religious School 2026-27')).toBeInTheDocument();
    expect(screen.getByText(/Madrich.*Grade 10/)).toBeInTheDocument();
  });

  it('frames the current week as Monday-Sunday', async () => {
    getMock.mockResolvedValue({ data: samplePayload });
    render(<MemoryRouter><MadrichDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('md-week-label'));
    const label = screen.getByTestId('md-week-label').textContent;
    expect(label).toMatch(/Week of/);
    expect(label).toMatch(/Sep 7/);
    expect(label).toMatch(/13/);
  });

  it('shows "Not yet submitted" + Start CTA when state is missing', async () => {
    getMock.mockResolvedValue({ data: samplePayload });
    render(<MemoryRouter><MadrichDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('md-reflection-cta'));
    expect(screen.getByTestId('md-reflection-status')).toHaveTextContent(/Not yet submitted/);
    expect(screen.getByTestId('md-reflection-cta')).toHaveTextContent('Start reflection');
    expect(screen.getByTestId('md-reflection-cta')).toHaveAttribute(
      'href', '/madrich/reflection/new?template=12',
    );
  });

  it('shows submitted state + Edit CTA when state is complete', async () => {
    getMock.mockResolvedValue({
      data: payloadWith({
        ...weeklyCard, state: 'complete', reflection_id: 99, editable: true,
      }),
    });
    render(<MemoryRouter><MadrichDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('md-reflection-cta'));
    expect(screen.getByTestId('md-reflection-status')).toHaveTextContent(/Submitted for this week/);
    expect(screen.getByTestId('md-reflection-cta')).toHaveTextContent('Edit reflection');
    expect(screen.getByTestId('md-reflection-cta')).toHaveAttribute(
      'href', '/madrich/reflection/99/edit',
    );
  });

  it('shows graceful copy when nothing is assigned', async () => {
    getMock.mockResolvedValue({ data: payloadWith() });
    render(<MemoryRouter><MadrichDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('md-reflection-card'));
    expect(screen.getByTestId('md-reflection-card')).toHaveTextContent(
      /No reflections currently assigned/,
    );
    expect(screen.queryByTestId('md-reflection-cta')).toBeNull();
  });

  it('renders one card per concurrent template, each with its own CTA', async () => {
    getMock.mockResolvedValue({
      data: payloadWith(weeklyCard, {
        template_id: 31,
        template_name: 'Mid-Year Check-In',
        cadence: 'on_demand',
        recurring: false,
        period: { start: '2026-09-09', end: '2026-09-09' },
        state: 'missing',
        reflection_id: null,
        editable: false,
      }),
    });
    render(<MemoryRouter><MadrichDashboard /></MemoryRouter>);
    await waitFor(() => expect(screen.getAllByTestId('md-reflection-card')).toHaveLength(2));

    expect(screen.getByText('TBE Madrich Weekly 3-2-1')).toBeInTheDocument();
    expect(screen.getByText('Mid-Year Check-In')).toBeInTheDocument();
    expect(screen.getAllByTestId('md-reflection-cta').map(a => a.getAttribute('href'))).toEqual([
      '/madrich/reflection/new?template=12',
      '/madrich/reflection/new?template=31',
    ]);
  });

  it('frames an on-demand card as available rather than as a period', async () => {
    getMock.mockResolvedValue({
      data: payloadWith({
        ...weeklyCard,
        template_id: 31,
        template_name: 'Mid-Year Check-In',
        cadence: 'on_demand',
        recurring: false,
      }),
    });
    render(<MemoryRouter><MadrichDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('md-week-label'));
    expect(screen.getByTestId('md-week-label')).toHaveTextContent('Available to submit');
  });

  it('frames a monthly card by its month', async () => {
    getMock.mockResolvedValue({
      data: payloadWith({
        ...weeklyCard,
        template_id: 44,
        template_name: 'Monthly Goals',
        cadence: 'monthly',
        period: { start: '2026-09-01', end: '2026-09-30' },
      }),
    });
    render(<MemoryRouter><MadrichDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('md-week-label'));
    expect(screen.getByTestId('md-week-label')).toHaveTextContent('September 2026');
  });

  it('links history section to /madrich/history', async () => {
    getMock.mockResolvedValue({ data: samplePayload });
    render(<MemoryRouter><MadrichDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('md-history-link'));
    expect(screen.getByTestId('md-history-link')).toHaveAttribute('href', '/madrich/history');
  });

  it('shows an error state on load failure', async () => {
    getMock.mockRejectedValue(new Error('boom'));
    render(<MemoryRouter><MadrichDashboard /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('md-error')).toBeInTheDocument());
  });
});
