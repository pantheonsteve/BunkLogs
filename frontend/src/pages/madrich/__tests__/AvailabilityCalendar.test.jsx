/**
 * Madrich availability calendar tests — Step 4_7.
 *
 * Covers rendering upcoming sessions, PUT-ing the correct body on a
 * status tap, and the disabled/explanation state once a session has
 * locked (MA6).
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import AvailabilityCalendar from '../AvailabilityCalendar';

const getMock = vi.fn();
const putMock = vi.fn();
vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    put: (...args) => putMock(...args),
    delete: vi.fn(),
  },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'tbe', user: { id: 7 } }),
}));

const samplePayload = {
  program: { id: 1, name: 'TBE Religious School 2026-27', slug: 'rs-2026-27' },
  timezone: 'America/New_York',
  edit_deadline_rule: 'saturday_18:00_eastern',
  sessions: [
    { session_date: '2026-09-13', label: 'Sun Sep 13', editable: true, commitment: null },
    {
      session_date: '2026-09-20', label: 'Sun Sep 20', editable: false,
      commitment: { status: 'available', note: '', updated_at: '2026-09-01T00:00:00Z' },
    },
  ],
};

beforeEach(() => {
  getMock.mockReset();
  putMock.mockReset();
});

describe('AvailabilityCalendar', () => {
  it('renders upcoming sessions grouped with their labels', async () => {
    getMock.mockResolvedValue({ data: samplePayload });
    render(<MemoryRouter><AvailabilityCalendar /></MemoryRouter>);
    await waitFor(() => screen.getByText('Sun Sep 13'));
    expect(screen.getByText('Sun Sep 20')).toBeInTheDocument();
  });

  it('PUTs the correct body when a status is tapped', async () => {
    getMock.mockResolvedValue({ data: samplePayload });
    putMock.mockResolvedValue({
      data: {
        session_date: '2026-09-13', label: 'Sun Sep 13', editable: true,
        commitment: { status: 'available', note: '', updated_at: '2026-09-05T00:00:00Z' },
      },
    });
    const user = userEvent.setup();
    render(<MemoryRouter><AvailabilityCalendar /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('availability-status-2026-09-13-available'));

    await user.click(screen.getByTestId('availability-status-2026-09-13-available'));

    await waitFor(() => expect(putMock).toHaveBeenCalledWith(
      '/api/v1/madrich/availability/2026-09-13/',
      { status: 'available', note: '' },
      expect.objectContaining({ headers: { 'X-Organization-Slug': 'tbe' } }),
    ));
  });

  it('disables status buttons and explains the lock once editable is false', async () => {
    getMock.mockResolvedValue({ data: samplePayload });
    render(<MemoryRouter><AvailabilityCalendar /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('availability-locked-2026-09-20'));

    expect(screen.getByTestId('availability-locked-2026-09-20')).toHaveTextContent(
      'Availability for this Sunday locked Saturday at 6:00 PM.',
    );
    expect(screen.getByTestId('availability-status-2026-09-20-available')).toBeDisabled();
    expect(screen.getByTestId('availability-status-2026-09-20-tentative')).toBeDisabled();
    expect(screen.getByTestId('availability-status-2026-09-20-unavailable')).toBeDisabled();
  });

  it('shows an empty state when there are no upcoming sessions', async () => {
    getMock.mockResolvedValue({ data: { ...samplePayload, sessions: [] } });
    render(<MemoryRouter><AvailabilityCalendar /></MemoryRouter>);
    await waitFor(() => screen.getByTestId('availability-empty'));
  });
});
