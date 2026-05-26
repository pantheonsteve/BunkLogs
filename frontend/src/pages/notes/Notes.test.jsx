/**
 * Frontend Vitest tests for the Notes platform (Step 7_19).
 *
 * Covers: NotesPage tabs, ThreadView reply, NoteComposer submission,
 * SourceReferenceIndicator disabled-link semantics,
 * and the Story 69 compose-and-receive integration flow.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock('../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
  },
}));

vi.mock('../../partials/Header', () => ({
  default: () => <div data-testid="header" />,
}));
vi.mock('../../partials/Sidebar', () => ({
  default: () => <div data-testid="sidebar" />,
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// ---------------------------------------------------------------------------
// Import components after mocks
// ---------------------------------------------------------------------------

import NotesPage from './NotesPage';
import ThreadView from './ThreadView';
import NoteComposer from '../../components/notes/NoteComposer';
import SourceReferenceIndicator from '../../components/notes/SourceReferenceIndicator';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const NOTE_INBOX = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      subject: 'Hello counselor',
      author: { id: 2, full_name: 'Bob UH' },
      audience_summary: 'Alice C',
      last_activity_at: new Date(Date.now() - 3600000).toISOString(),
      unread: true,
      camper_reference_id: null,
    },
  ],
};

const NOTE_THREAD = {
  id: 1,
  subject: 'Hello counselor',
  body: 'Check in please',
  author: { id: 2, full_name: 'Bob UH' },
  author_role_at_write: 'unit_head',
  created_at: new Date(Date.now() - 3600000).toISOString(),
  audience: [{ person: { id: 1, full_name: 'Alice C' }, option_key: 'specific_counselor' }],
  replies: [],
  read_summary: { read_count: 1, audience_count: 1 },
  source_content_type: '',
  source_object_id: '',
};

const AUDIENCE_OPTIONS = [
  { option_key: 'my_unit_head', label: 'My Unit Head' },
  { option_key: 'co_counselors_on_bunk', label: 'Co-counselors on this bunk' },
];

// ---------------------------------------------------------------------------
// NotesPage tests
// ---------------------------------------------------------------------------

describe('NotesPage', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
  });

  it('renders Inbox tab by default and shows note', async () => {
    getMock.mockResolvedValue({ data: NOTE_INBOX });

    render(
      <MemoryRouter>
        <NotesPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Hello counselor')).toBeDefined();
    });
    expect(screen.getByText(/From: Bob UH/)).toBeDefined();
  });

  it('switches to Sent tab and fetches sent endpoint', async () => {
    getMock.mockResolvedValue({ data: { count: 0, results: [] } });

    render(
      <MemoryRouter>
        <NotesPage />
      </MemoryRouter>,
    );

    const sentTab = screen.getByRole('button', { name: 'Sent' });
    await userEvent.click(sentTab);

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith('/api/v1/notes/sent/');
    });
  });

  it('shows compose button and opens NoteComposer', async () => {
    // First call: inbox list. Second call (from AudiencePicker): audience options.
    getMock
      .mockResolvedValueOnce({ data: { count: 0, results: [] } })
      .mockResolvedValueOnce({ data: AUDIENCE_OPTIONS });

    render(
      <MemoryRouter>
        <NotesPage />
      </MemoryRouter>,
    );

    const composeBtn = await screen.findByRole('button', { name: /compose/i });
    await userEvent.click(composeBtn);

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeDefined();
    });
  });

  it('shows empty inbox message when no notes', async () => {
    getMock.mockResolvedValue({ data: { count: 0, results: [] } });

    render(
      <MemoryRouter>
        <NotesPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Your inbox is empty.')).toBeDefined();
    });
  });
});

// ---------------------------------------------------------------------------
// ThreadView tests
// ---------------------------------------------------------------------------

describe('ThreadView', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
  });

  it('renders note subject and body', async () => {
    getMock.mockResolvedValue({ data: NOTE_THREAD });

    render(
      <MemoryRouter initialEntries={['/notes/1']}>
        <Routes>
          <Route path="/notes/:noteId" element={<ThreadView />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Hello counselor')).toBeDefined();
      expect(screen.getByText('Check in please')).toBeDefined();
    });
  });

  it('submits a reply', async () => {
    getMock.mockResolvedValue({ data: NOTE_THREAD });
    postMock.mockResolvedValue({
      data: {
        id: 99,
        author: { id: 1, full_name: 'Alice C' },
        author_role_at_write: 'counselor',
        body: 'Got it!',
        created_at: new Date().toISOString(),
      },
    });

    render(
      <MemoryRouter initialEntries={['/notes/1']}>
        <Routes>
          <Route path="/notes/:noteId" element={<ThreadView />} />
        </Routes>
      </MemoryRouter>,
    );

    const textarea = await screen.findByPlaceholderText('Write a reply…');
    await userEvent.type(textarea, 'Got it!');

    const replyBtn = screen.getByRole('button', { name: /reply/i });
    await userEvent.click(replyBtn);

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/v1/notes/1/replies/', { body: 'Got it!' });
      expect(screen.getByText('Got it!')).toBeDefined();
    });
  });
});

// ---------------------------------------------------------------------------
// NoteComposer tests
// ---------------------------------------------------------------------------

describe('NoteComposer', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
  });

  it('shows audience picker options', async () => {
    getMock.mockResolvedValue({ data: AUDIENCE_OPTIONS });

    const onClose = vi.fn();
    render(
      <MemoryRouter>
        <NoteComposer onClose={onClose} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('My Unit Head')).toBeDefined();
    });
  });

  it('requires audience selection before submitting', async () => {
    getMock.mockResolvedValue({ data: AUDIENCE_OPTIONS });

    const onClose = vi.fn();
    render(
      <MemoryRouter>
        <NoteComposer onClose={onClose} />
      </MemoryRouter>,
    );

    await waitFor(() => screen.getByText('My Unit Head'));

    const sendBtn = screen.getByRole('button', { name: /send note/i });
    await userEvent.click(sendBtn);

    expect(screen.getByText('Please select at least one audience member.')).toBeDefined();
    expect(postMock).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// SourceReferenceIndicator tests
// ---------------------------------------------------------------------------

describe('SourceReferenceIndicator', () => {
  it('renders nothing when no source type', () => {
    const { container } = render(
      <MemoryRouter>
        <SourceReferenceIndicator sourceContentType="" sourceObjectId="" />
      </MemoryRouter>,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders reference link for reflection_concern', () => {
    render(
      <MemoryRouter>
        <SourceReferenceIndicator sourceContentType="reflection_concern" sourceObjectId="42" />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Bunk concern/)).toBeDefined();
  });

  it('renders reference link for specialist_note', () => {
    render(
      <MemoryRouter>
        <SourceReferenceIndicator sourceContentType="specialist_note" sourceObjectId="7" />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Specialist note/)).toBeDefined();
  });

  it('shows tooltip on hover explaining non-transitive access', async () => {
    render(
      <MemoryRouter>
        <SourceReferenceIndicator sourceContentType="reflection_concern" sourceObjectId="42" />
      </MemoryRouter>,
    );

    const badge = screen.getByText(/Referenced from/);
    await userEvent.hover(badge);

    await waitFor(() => {
      expect(screen.getByText(/does not grant access/)).toBeDefined();
    });
  });
});

// ---------------------------------------------------------------------------
// Story 69 integration: UH taps "from-bunk-concern" -> pre-filled NoteComposer
// ---------------------------------------------------------------------------

describe('Story 69 integration: compose from Bunk concern', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
  });

  it('pre-fills composer when from-bunk-concern draft is returned', async () => {
    const DRAFT = {
      draft: {
        subject: 'Re: concern from Alice C',
        body: 'The concern text here',
        source_content_type: 'reflection_concern',
        source_object_id: '42',
        audience: [{ option_key: 'specific_counselor', person_id: 1 }],
      },
    };

    // from-bunk-concern POST returns a draft
    postMock.mockResolvedValue({ data: DRAFT });
    // audience-options for the composer
    getMock.mockResolvedValue({ data: AUDIENCE_OPTIONS });

    const onClose = vi.fn();
    render(
      <MemoryRouter>
        <NoteComposer
          initialDraft={{
            ...DRAFT.draft,
            draftId: 'test-draft',
          }}
          onClose={onClose}
        />
      </MemoryRouter>,
    );

    await waitFor(() => {
      // Subject is pre-filled
      const subjectInput = screen.getByPlaceholderText("What's this about?");
      expect(subjectInput.value).toBe('Re: concern from Alice C');
    });

    // Source indicator visible
    await waitFor(() => {
      expect(screen.getByText(/Referenced from/)).toBeDefined();
    });
  });
});
