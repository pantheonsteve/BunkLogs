import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SpecialistDashboard from '../Dashboard';

const getMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
  window.sessionStorage?.clear?.();
});

const samplePayload = {
  today: '2026-07-10',
  header: { name: 'Alex Water', role_label: 'Waterfront Specialist', program_name: 'Summer 2026' },
  write_camper_note: { url: '/specialist/notes/new' },
  self_reflection: { state: 'missing', reflection_id: null, template_id: 5, editable: false },
  recent_notes: [
    {
      id: 1,
      subject_id: 42,
      subject_name: 'Jake S.',
      bunk_name: 'Elm',
      category: 'positive',
      body_preview: 'Great backstroke technique.',
      is_sensitive: false,
      flag_raised: false,
      created_at: new Date().toISOString(),
      is_within_edit_window: true,
    },
  ],
};

describe('SpecialistDashboard', () => {
  it('renders all three sections', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(<MemoryRouter><SpecialistDashboard /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByTestId('sp-dashboard')).toBeInTheDocument();
    });
    expect(screen.getByTestId('sp-write-note-btn')).toBeInTheDocument();
    expect(screen.getByTestId('sp-self-reflection-card')).toBeInTheDocument();
    expect(screen.getByTestId('sp-recent-notes')).toBeInTheDocument();
  });

  it('shows role label and program in header', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(<MemoryRouter><SpecialistDashboard /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('sp-dashboard')).toBeInTheDocument());
    expect(screen.getByText(/Waterfront Specialist/)).toBeInTheDocument();
    expect(screen.getByText(/Alex Water/)).toBeInTheDocument();
  });

  it('renders recent notes with camper name and preview', async () => {
    getMock.mockResolvedValueOnce({ data: samplePayload });
    render(<MemoryRouter><SpecialistDashboard /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('sp-dashboard')).toBeInTheDocument());
    expect(screen.getByText('Jake S.')).toBeInTheDocument();
    expect(screen.getByText('Great backstroke technique.')).toBeInTheDocument();
  });

  it('shows empty state when no recent notes', async () => {
    getMock.mockResolvedValueOnce({ data: { ...samplePayload, recent_notes: [] } });
    render(<MemoryRouter><SpecialistDashboard /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('sp-recent-notes')).toBeInTheDocument());
    expect(screen.getByText(/No notes yet/i)).toBeInTheDocument();
  });

  it('shows self-reflection as complete when state=complete', async () => {
    const payload = {
      ...samplePayload,
      self_reflection: { state: 'complete', reflection_id: 7, template_id: 5, editable: true },
    };
    getMock.mockResolvedValueOnce({ data: payload });
    render(<MemoryRouter><SpecialistDashboard /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('sp-self-reflection-card')).toBeInTheDocument());
    expect(screen.getByText('Done')).toBeInTheDocument();
  });

  it('shows loading state initially', () => {
    getMock.mockReturnValue(new Promise(() => {}));
    render(<MemoryRouter><SpecialistDashboard /></MemoryRouter>);
    expect(screen.getByTestId('sp-dashboard-loading')).toBeInTheDocument();
  });
});
