/**
 * Madrich dashboard tests — Step 7_14, Story 61.
 *
 * Covers weekly framing (the "Week of …" label is derived from the
 * server-provided period_start/period_end, criterion 5), state→CTA
 * mapping, and the absence of the no-template / camp-side surfaces.
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
  my_reflection: { state: 'missing', reflection_id: null, template_id: 12, editable: false },
  history_entry: { url: '/madrich/history' },
};

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
      'href', '/madrich/reflection/new',
    );
  });

  it('shows submitted state + Edit CTA when state is complete', async () => {
    getMock.mockResolvedValue({
      data: {
        ...samplePayload,
        my_reflection: { state: 'complete', reflection_id: 99, template_id: 12, editable: true },
      },
    });
    render(<MemoryRouter><MadrichDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('md-reflection-cta'));
    expect(screen.getByTestId('md-reflection-status')).toHaveTextContent(/Submitted for this week/);
    expect(screen.getByTestId('md-reflection-cta')).toHaveTextContent('Edit reflection');
    expect(screen.getByTestId('md-reflection-cta')).toHaveAttribute(
      'href', '/madrich/reflection/99/edit',
    );
  });

  it('shows graceful copy when no template is configured', async () => {
    getMock.mockResolvedValue({
      data: {
        ...samplePayload,
        my_reflection: { state: 'no_template', reflection_id: null, template_id: null, editable: false },
      },
    });
    render(<MemoryRouter><MadrichDashboard /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('md-reflection-card'));
    expect(screen.getByTestId('md-reflection-card')).toHaveTextContent(
      /No reflections currently assigned/,
    );
    expect(screen.queryByTestId('md-reflection-cta')).toBeNull();
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
