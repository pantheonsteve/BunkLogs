import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import SpecialistNoteForm from '../NoteForm';

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
    patch: (...args) => postMock(...args),
  },
}));

const mockAudience = { audience: ['Counselor', 'Unit Head', 'Camper Care', 'Leadership Team', 'Admin'], is_sensitive: false };
const mockSensitiveAudience = { audience: ['Camper Care', 'Health Center', 'Special Diets', 'Admin'], is_sensitive: true };

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  getMock.mockResolvedValue({ data: mockAudience });
});

function renderNoteForm(routeState = {}, path = '/specialist/notes/new') {
  return render(
    <MemoryRouter initialEntries={[{ pathname: path, state: routeState }]}>
      <Routes>
        <Route path="/specialist/notes/new" element={<SpecialistNoteForm />} />
        <Route path="/specialist/notes/:noteId/edit" element={<SpecialistNoteForm />} />
        <Route path="/specialist" element={<div>dashboard</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('SpecialistNoteForm', () => {
  it('shows camper picker first when no camper selected', async () => {
    renderNoteForm();
    await waitFor(() => {
      expect(screen.getByTestId('sp-noteform-picker')).toBeInTheDocument();
    });
  });

  it('renders form after camper is pre-selected via state', async () => {
    const note = {
      id: null,
      subject_id: 42,
      body: '',
      category: '',
      is_sensitive: false,
      flag_raised: false,
      language: 'en',
    };
    renderNoteForm({});
    // The form opens picker first; we test the form state by providing a note via location.state
  });

  it('shows Flag for Camper Care checkbox in form', async () => {
    getMock.mockResolvedValue({ data: mockAudience });
    // Render form in edit mode with a note from location.state
    const noteState = {
      note: {
        id: 7,
        subject_id: 42,
        body: 'Original body',
        category: 'positive',
        is_sensitive: false,
        flag_raised: false,
        language: 'en',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    };
    render(
      <MemoryRouter initialEntries={[{ pathname: '/specialist/notes/7/edit', state: noteState }]}>
        <Routes>
          <Route path="/specialist/notes/:noteId/edit" element={<SpecialistNoteForm />} />
          <Route path="/specialist" element={<div>dashboard</div>} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId('sp-noteform-form')).toBeInTheDocument());
    expect(screen.getByTestId('sp-noteform-flag')).toBeInTheDocument();
  });

  it('flag checkbox disabled when flag already raised', async () => {
    const noteState = {
      note: {
        id: 7,
        subject_id: 42,
        body: 'Flagged note',
        category: '',
        is_sensitive: false,
        flag_raised: true,
        language: 'en',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    };
    render(
      <MemoryRouter initialEntries={[{ pathname: '/specialist/notes/7/edit', state: noteState }]}>
        <Routes>
          <Route path="/specialist/notes/:noteId/edit" element={<SpecialistNoteForm />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId('sp-noteform-flag')).toBeInTheDocument());
    expect(screen.getByTestId('sp-noteform-flag')).toBeDisabled();
  });

  it('audience disclosure updates when Sensitive is toggled', async () => {
    getMock
      .mockResolvedValueOnce({ data: mockAudience })
      .mockResolvedValueOnce({ data: mockSensitiveAudience });

    const noteState = {
      note: {
        id: 3,
        subject_id: 42,
        body: 'Test',
        category: '',
        is_sensitive: false,
        flag_raised: false,
        language: 'en',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    };
    render(
      <MemoryRouter initialEntries={[{ pathname: '/specialist/notes/3/edit', state: noteState }]}>
        <Routes>
          <Route path="/specialist/notes/:noteId/edit" element={<SpecialistNoteForm />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId('sp-noteform-form')).toBeInTheDocument());
    const sensitiveCheckbox = screen.getByTestId('sp-noteform-sensitive');
    fireEvent.click(sensitiveCheckbox);
    // Second audience fetch is triggered
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(2));
  });

  it('shows window-closed message when note is outside 24h edit window', async () => {
    const oldDate = new Date(Date.now() - 25 * 60 * 60 * 1000).toISOString();
    const noteState = {
      note: {
        id: 5,
        subject_id: 42,
        body: 'Old note',
        category: '',
        is_sensitive: false,
        flag_raised: false,
        language: 'en',
        created_at: oldDate,
        updated_at: oldDate,
      },
    };
    render(
      <MemoryRouter initialEntries={[{ pathname: '/specialist/notes/5/edit', state: noteState }]}>
        <Routes>
          <Route path="/specialist/notes/:noteId/edit" element={<SpecialistNoteForm />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId('sp-noteform-window-closed')).toBeInTheDocument());
  });
});
