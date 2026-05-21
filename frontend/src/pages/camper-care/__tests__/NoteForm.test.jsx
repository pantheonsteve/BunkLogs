import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import CamperCareNoteForm from '../NoteForm';

const getMock = vi.fn();
const postMock = vi.fn();
const patchMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
    patch: (...args) => patchMock(...args),
  },
}));

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  patchMock.mockReset();
});

function wireAudienceCalls() {
  getMock.mockImplementation((url, opts) => {
    if (url === '/api/v1/camper-care/notes/audience/') {
      const isSensitive = opts?.params?.is_sensitive === 'true';
      return Promise.resolve({
        data: {
          is_sensitive: isSensitive,
          audience: isSensitive
            ? ['Camper Care', 'Health Center', 'Special Diets', 'Admin']
            : ['Camper Care', 'Leadership Team', 'Admin'],
        },
      });
    }
    return Promise.reject(new Error(`unexpected GET ${url}`));
  });
}

describe('CamperCareNoteForm — create', () => {
  it('shows the non-sensitive audience by default and refreshes when Sensitive toggles', async () => {
    wireAudienceCalls();
    render(
      <MemoryRouter initialEntries={['/camper-care/notes/new?camperId=42']}>
        <Routes>
          <Route path="/camper-care/notes/new" element={<CamperCareNoteForm />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('audience-disclosure-labels')).toHaveTextContent(
        'Camper Care, Leadership Team, Admin',
      );
    });
    const user = userEvent.setup();
    await user.click(screen.getByTestId('cc-noteform-sensitive'));
    await waitFor(() => {
      expect(screen.getByTestId('audience-disclosure-labels')).toHaveTextContent(
        'Camper Care, Health Center, Special Diets, Admin',
      );
    });
  });

  it('submits a valid note and shows the success banner', async () => {
    wireAudienceCalls();
    postMock.mockResolvedValueOnce({
      data: {
        id: 17,
        subject_id: 42,
        author_id: 99,
        note_type: 'camper_care',
        body: 'Camper reports feeling homesick.',
        category: 'social',
        is_sensitive: false,
        language: 'en',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        is_within_edit_window: true,
      },
      status: 201,
    });

    render(
      <MemoryRouter initialEntries={['/camper-care/notes/new?camperId=42']}>
        <Routes>
          <Route path="/camper-care/notes/new" element={<CamperCareNoteForm />} />
        </Routes>
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByTestId('cc-noteform-form')).toBeInTheDocument();
    });

    await user.type(screen.getByTestId('cc-noteform-body'), 'Camper reports feeling homesick.');
    await user.selectOptions(screen.getByTestId('cc-noteform-category'), 'social');
    await user.click(screen.getByTestId('cc-noteform-submit'));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalled();
    });
    const [url, payload] = postMock.mock.calls[0];
    expect(url).toBe('/api/v1/camper-care/notes/');
    expect(payload).toMatchObject({
      subject_id: 42,
      body: 'Camper reports feeling homesick.',
      category: 'social',
      is_sensitive: false,
      language: 'en',
    });
    await waitFor(() => {
      expect(screen.getByTestId('cc-noteform-success')).toHaveTextContent(/note added/i);
    });
  });

  it('blocks submission when required fields are missing', async () => {
    wireAudienceCalls();
    render(
      <MemoryRouter initialEntries={['/camper-care/notes/new?camperId=42']}>
        <Routes>
          <Route path="/camper-care/notes/new" element={<CamperCareNoteForm />} />
        </Routes>
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByTestId('cc-noteform-form')).toBeInTheDocument();
    });
    await user.click(screen.getByTestId('cc-noteform-submit'));
    expect(postMock).not.toHaveBeenCalled();
    expect(screen.getAllByText(/Required\./i).length).toBeGreaterThan(0);
  });
});

describe('CamperCareNoteForm — edit', () => {
  it('renders an editable form when navigated with location.state.note inside the 24h window', async () => {
    wireAudienceCalls();
    const recent = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    const note = {
      id: 99,
      subject_id: 42,
      body: 'Initial body.',
      category: 'medical',
      is_sensitive: true,
      language: 'en',
      created_at: recent,
      updated_at: recent,
      is_within_edit_window: true,
    };
    patchMock.mockResolvedValueOnce({
      data: { ...note, body: 'Edited body.' },
    });

    render(
      <MemoryRouter initialEntries={[{ pathname: '/camper-care/notes/99/edit', state: { note } }]}>
        <Routes>
          <Route path="/camper-care/notes/:noteId/edit" element={<CamperCareNoteForm />} />
        </Routes>
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByTestId('cc-noteform-body')).toHaveValue('Initial body.');
    });
    await user.clear(screen.getByTestId('cc-noteform-body'));
    await user.type(screen.getByTestId('cc-noteform-body'), 'Edited body.');
    await user.click(screen.getByTestId('cc-noteform-submit'));
    await waitFor(() => {
      expect(patchMock).toHaveBeenCalled();
    });
    const [url, payload] = patchMock.mock.calls[0];
    expect(url).toBe('/api/v1/camper-care/notes/99/');
    expect(payload.body).toBe('Edited body.');
  });

  it('renders a missing-state notice when no location.state is supplied', async () => {
    wireAudienceCalls();
    render(
      <MemoryRouter initialEntries={['/camper-care/notes/99/edit']}>
        <Routes>
          <Route path="/camper-care/notes/:noteId/edit" element={<CamperCareNoteForm />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('cc-noteform-missing-state')).toBeInTheDocument();
    });
  });
});
