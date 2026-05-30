import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import TicketDetail from '../TicketDetail';

const fetchTicketDetailMock = vi.fn();

vi.mock('../../../api/maintenance', () => ({
  fetchTicketDetail: (...args) => fetchTicketDetailMock(...args),
  transitionTicket: vi.fn(),
  correctLastTransition: vi.fn(),
  createTicketNote: vi.fn(),
  editTicketNote: vi.fn(),
  fetchNoteAudience: vi.fn().mockResolvedValue({ label: '' }),
  uploadTicketPhoto: vi.fn(),
}));

vi.mock('../../../components/AuditTrail', () => ({
  default: () => <div data-testid="audit-trail" />,
}));
vi.mock('../../../components/admin/AdminViewingBanner', () => ({
  default: () => null,
}));
vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ user: { email: 'x@t.test' } }),
}));

function detailPayload(scope) {
  return {
    scope,
    ticket: {
      id: '1',
      status: 'in_progress',
      urgency: 'normal',
      location: 'Bunk 12',
      category: 'broken_light',
      description: 'Light out',
      submitter_name: 'Alex Smith',
      available_transitions: scope === 'team' ? ['fulfilled'] : [],
      is_within_correction_window: false,
      created_at: '2026-07-10T08:00:00Z',
    },
    photos: [],
    activity: [],
  };
}

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={['/maintenance/tickets/1']}>
      <Routes>
        <Route path="/maintenance/tickets/:ticketId" element={<TicketDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  fetchTicketDetailMock.mockReset();
});

describe('TicketDetail read-only gating', () => {
  it('hides actions, note form, and audit for a read-only viewer', async () => {
    fetchTicketDetailMock.mockResolvedValue(detailPayload('viewer'));
    renderDetail();

    await waitFor(() => screen.getByTestId('ticket-detail'));
    // Progress is still visible.
    expect(screen.getByTestId('ticket-activity')).toBeDefined();
    // Write affordances are not.
    expect(screen.queryByTestId('ticket-actions')).toBeNull();
    expect(screen.queryByTestId('note-form')).toBeNull();
    expect(screen.queryByTestId('photo-upload-form')).toBeNull();
    expect(screen.queryByTestId('audit-trail')).toBeNull();
  });

  it('shows actions and note form for the maintenance team', async () => {
    fetchTicketDetailMock.mockResolvedValue(detailPayload('team'));
    renderDetail();

    await waitFor(() => screen.getByTestId('ticket-detail'));
    expect(screen.getByTestId('ticket-actions')).toBeDefined();
    expect(screen.getByTestId('note-form')).toBeDefined();
  });
});
