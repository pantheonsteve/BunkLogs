/**
 * Admin availability matrix tests — Step 4_7 AC4.
 *
 * Renders the staffing grid (one role tab at a time, columns = sessions)
 * with status labels against a mocked API, and covers the empty/error states.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AvailabilityMatrix from '../AvailabilityMatrix';

const fetchMock = vi.fn();
const exportUrlMock = vi.fn(() => '/api/v1/admin/madrich-availability/export.csv');
vi.mock('../../../../api/adminMadrichAvailability', () => ({
  fetchAdminMadrichAvailability: (...args) => fetchMock(...args),
  exportAdminMadrichAvailabilityUrl: (...args) => exportUrlMock(...args),
}));

const samplePayload = {
  program: { id: 1, name: 'TBE Religious School 2026-27', slug: 'rs-2026-27' },
  sessions: ['2026-09-13', '2026-09-20'],
  rows: [
    {
      person_id: 9, display_name: 'Fran Teacher', grade_level: null, role: 'faculty',
      cells: [
        { session_date: '2026-09-13', status: 'available', note: '' },
        { session_date: '2026-09-20', status: 'available', note: '' },
      ],
    },
    {
      person_id: 21, display_name: 'Maya Alpha', grade_level: 8, role: 'madrich',
      cells: [
        { session_date: '2026-09-13', status: 'available', note: '' },
        { session_date: '2026-09-20', status: null, note: '' },
      ],
    },
    {
      person_id: 22, display_name: 'Ben Beta', grade_level: 10, role: 'madrich',
      cells: [
        { session_date: '2026-09-13', status: 'unavailable', note: 'Family event' },
        { session_date: '2026-09-20', status: 'tentative', note: '' },
      ],
    },
  ],
  summary: {
    available_counts: { '2026-09-13': 1, '2026-09-20': 0 },
    unset_counts: { '2026-09-13': 0, '2026-09-20': 1 },
  },
};

beforeEach(() => {
  fetchMock.mockReset();
  exportUrlMock.mockClear();
});

describe('AvailabilityMatrix', () => {
  it('renders the grid with rows, status labels, and the summary row', async () => {
    fetchMock.mockResolvedValue(samplePayload);
    render(<MemoryRouter><AvailabilityMatrix /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('availability-matrix-grid'));

    expect(screen.getByText('Maya Alpha')).toBeInTheDocument();
    expect(screen.getByText('Ben Beta')).toBeInTheDocument();
    expect(screen.getAllByText('Available').length).toBeGreaterThan(0);
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
    expect(screen.getByText('Tentative')).toBeInTheDocument();
    expect(screen.getAllByText('Unset').length).toBeGreaterThan(0);

    const summary = screen.getByTestId('availability-matrix-summary');
    expect(summary).toHaveTextContent('1');
  });

  it('shows one role at a time, with a summary for that role', async () => {
    fetchMock.mockResolvedValue(samplePayload);
    render(<MemoryRouter><AvailabilityMatrix /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('availability-matrix-block-madrich'));

    const madrichBlock = screen.getByTestId('availability-matrix-block-madrich');
    expect(madrichBlock).toHaveTextContent('Maya Alpha');
    expect(madrichBlock).toHaveTextContent('Ben Beta');
    expect(madrichBlock).not.toHaveTextContent('Fran Teacher');
    expect(screen.getByTestId('availability-matrix-tab-madrich')).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByTestId('availability-matrix-summary')).toHaveTextContent('Madrichim available');

    fireEvent.click(screen.getByTestId('availability-matrix-tab-faculty'));
    const facultyBlock = screen.getByTestId('availability-matrix-block-faculty');
    expect(facultyBlock).toHaveTextContent('Fran Teacher');
    expect(facultyBlock).not.toHaveTextContent('Maya Alpha');
    const facultySummary = screen.getByTestId('availability-matrix-summary');
    expect(facultySummary).toHaveTextContent('Faculty available');
    expect(facultySummary).toHaveTextContent('1');
  });

  it('treats a row with no role as a Madrich so an older payload still renders', async () => {
    fetchMock.mockResolvedValue({
      ...samplePayload,
      rows: [{ ...samplePayload.rows[1], role: undefined }],
    });
    render(<MemoryRouter><AvailabilityMatrix /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('availability-matrix-block-madrich'));
    expect(screen.getByText('Maya Alpha')).toBeInTheDocument();
  });

  it('links the Export CSV button to the export URL', async () => {
    fetchMock.mockResolvedValue(samplePayload);
    render(<MemoryRouter><AvailabilityMatrix /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('availability-matrix-export'));
    expect(screen.getByTestId('availability-matrix-export')).toHaveAttribute(
      'href', '/api/v1/admin/madrich-availability/export.csv',
    );
  });

  it('shows an empty state when there is no configured program', async () => {
    fetchMock.mockResolvedValue({ program: null, sessions: [], rows: [], summary: {} });
    render(<MemoryRouter><AvailabilityMatrix /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('availability-matrix-empty'));
  });

  it('shows an error state when the admin fetch is forbidden', async () => {
    fetchMock.mockRejectedValue({ response: { status: 403 } });
    render(<MemoryRouter><AvailabilityMatrix /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('availability-matrix-error'));
    expect(screen.getByTestId('availability-matrix-error')).toHaveTextContent('Admin access required.');
  });
});
