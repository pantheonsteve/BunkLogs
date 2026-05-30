/**
 * Frontend Vitest tests for the Subject Notes feature.
 *
 * Covers: SubjectNotesPage feed render + grouping, opening the composer,
 * subject typeahead debounce, and submission via createSubjectNote.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock('../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
  },
}));

vi.mock('../../api/subjects', async () => {
  const actual = await vi.importActual('../../api/subjects');
  return {
    ...actual,
    createSubjectNote: vi.fn(),
  };
});

import SubjectNotesPage from './SubjectNotesPage';
import SubjectNoteComposer from '../../components/subject-notes/SubjectNoteComposer';
import { createSubjectNote } from '../../api/subjects';

const FEED = {
  notes: [
    {
      id: 11,
      subject: { id: 5, full_name: 'Kim Camper' },
      body: 'Doing well today',
      context: '',
      visibility: 'team',
      is_sensitive: false,
      subject_visible: false,
      amendment_of: null,
      author: { id: 2, name: 'LT Lead' },
      created_at: '2026-05-26T12:00:00Z',
    },
    {
      id: 12,
      subject: { id: 5, full_name: 'Kim Camper' },
      body: 'Follow-up observation',
      context: 'wellness',
      visibility: 'supervisors_only',
      is_sensitive: false,
      subject_visible: false,
      amendment_of: null,
      author: { id: 2, name: 'LT Lead' },
      created_at: '2026-05-26T13:00:00Z',
    },
    {
      id: 13,
      subject: { id: 7, full_name: 'Sam Other' },
      body: 'Different camper note',
      context: '',
      visibility: 'team',
      is_sensitive: false,
      subject_visible: false,
      amendment_of: null,
      author: { id: 2, name: 'LT Lead' },
      created_at: '2026-05-26T14:00:00Z',
    },
  ],
};

describe('SubjectNotesPage', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    createSubjectNote.mockReset();
  });

  it('groups notes by subject and renders dashboard links', async () => {
    getMock.mockResolvedValueOnce({ data: FEED });
    render(
      <MemoryRouter>
        <SubjectNotesPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Doing well today')).toBeDefined();
    });

    // Two groups: Kim and Sam
    expect(screen.getByTestId('subject-notes-group-5')).toBeDefined();
    expect(screen.getByTestId('subject-notes-group-7')).toBeDefined();
    // Kim group contains both notes
    const kimGroup = screen.getByTestId('subject-notes-group-5');
    expect(kimGroup.textContent).toContain('Doing well today');
    expect(kimGroup.textContent).toContain('Follow-up observation');
  });

  it('shows empty state when feed is empty', async () => {
    getMock.mockResolvedValueOnce({ data: { notes: [] } });
    render(
      <MemoryRouter>
        <SubjectNotesPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText(/No subject notes you have access to/)).toBeDefined();
    });
  });

  it('opens the composer when New note is clicked', async () => {
    getMock.mockResolvedValueOnce({ data: { notes: [] } });
    render(
      <MemoryRouter>
        <SubjectNotesPage />
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByText(/No subject notes/));

    const newBtn = screen.getByTestId('subject-notes-compose');
    await userEvent.click(newBtn);
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /Compose a subject note/i })).toBeDefined();
    });
  });
});

describe('SubjectNoteComposer', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    createSubjectNote.mockReset();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  it('typeahead debounces and renders results', async () => {
    getMock.mockResolvedValue({
      data: { subjects: [{ id: 5, full_name: 'Kim Camper' }] },
    });
    render(
      <MemoryRouter>
        <SubjectNoteComposer onClose={() => {}} />
      </MemoryRouter>,
    );
    const search = screen.getByTestId('subject-note-composer-search');
    await userEvent.type(search, 'Kim');
    // Advance debounce timer
    await act(async () => {
      vi.advanceTimersByTime(250);
    });
    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith(expect.stringContaining('/api/v1/subject-notes/subjects/?q=Kim'));
      expect(screen.getByText('Kim Camper')).toBeDefined();
    });
  });

  it('blocks submit until subject and body are picked', async () => {
    render(
      <MemoryRouter>
        <SubjectNoteComposer onClose={() => {}} />
      </MemoryRouter>,
    );
    const submit = screen.getByTestId('subject-note-composer-submit');
    await userEvent.click(submit);
    expect(screen.getByText(/Please pick a subject/)).toBeDefined();
    expect(createSubjectNote).not.toHaveBeenCalled();
  });

  it('submits to createSubjectNote with the picked subject id', async () => {
    getMock.mockResolvedValue({
      data: { subjects: [{ id: 5, full_name: 'Kim Camper' }] },
    });
    createSubjectNote.mockResolvedValue({ data: { id: 99 }, status: 201 });
    const onSent = vi.fn();
    const onClose = vi.fn();
    render(
      <MemoryRouter>
        <SubjectNoteComposer onClose={onClose} onSent={onSent} />
      </MemoryRouter>,
    );

    const search = screen.getByTestId('subject-note-composer-search');
    await userEvent.type(search, 'Kim');
    await act(async () => {
      vi.advanceTimersByTime(250);
    });
    await waitFor(() => screen.getByText('Kim Camper'));
    await userEvent.click(screen.getByText('Kim Camper'));

    const body = screen.getByTestId('subject-note-composer-body');
    await userEvent.type(body, 'Quick observation');

    const submit = screen.getByTestId('subject-note-composer-submit');
    await userEvent.click(submit);

    await waitFor(() => {
      expect(createSubjectNote).toHaveBeenCalledWith(5, expect.objectContaining({
        body: 'Quick observation',
        visibility: 'supervisors_only',
      }));
      expect(onSent).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });
});
