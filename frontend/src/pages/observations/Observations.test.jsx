/**
 * Frontend Vitest tests for the Observations UI (Step 7_23).
 *
 * Covers: ObservationsInbox list, ObservationThread reply, and the
 * ObservationComposer (multi-subject chips + sensitivity-filtered recipients).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock('../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
  },
}));

vi.mock('../../partials/Header', () => ({ default: () => <div data-testid="header" /> }));
vi.mock('../../partials/Sidebar', () => ({ default: () => <div data-testid="sidebar" /> }));

const authState = { user: { role: 'Counselor' } };
vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => authState,
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useNavigate: () => mockNavigate };
});

import ObservationsInbox from './ObservationsInbox';
import ObservationThread from './ObservationThread';
import ObservationComposer from '../../components/observations/ObservationComposer';

const INBOX = {
  count: 1,
  next: null,
  results: [
    {
      id: 1,
      author: { id: 2, full_name: 'Bob UH' },
      sensitivity: 'sensitive',
      subjects_summary: 'Cam Per',
      last_activity_at: new Date(Date.now() - 3600000).toISOString(),
      unread: true,
    },
  ],
};

const THREAD = {
  id: 1,
  body: 'Saw something at swim',
  author: { id: 2, full_name: 'Bob UH' },
  author_role_at_write: 'unit_head',
  sensitivity: 'sensitive',
  context: 'swim',
  observed_at: '2026-06-02T15:00:00Z',
  created_at: new Date(Date.now() - 3600000).toISOString(),
  subjects: [{ id: 5, full_name: 'Cam Per', can_view_profile: true }],
  recipients: [],
  replies: [],
  read_summary: { read_count: 0, audience_count: 0 },
};

describe('ObservationsInbox', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    authState.user = { role: 'Counselor' };
  });

  it('renders inbox items with subject summary', async () => {
    getMock.mockResolvedValue({ data: INBOX });
    render(
      <MemoryRouter>
        <ObservationsInbox />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Cam Per')).toBeDefined();
    });
    expect(screen.getByText(/From Bob UH/)).toBeDefined();
  });

  it('shows empty state when no observations', async () => {
    getMock.mockResolvedValue({ data: { count: 0, results: [] } });
    render(
      <MemoryRouter>
        <ObservationsInbox />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Your observations inbox is empty.')).toBeDefined();
    });
  });

  it('shows message counts next to the Inbox and Sent tabs', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/all/')) return Promise.resolve({ data: { count: 0, results: [] } });
      if (url.includes('/sent/')) {
        return Promise.resolve({ data: { count: 4, results: [] } });
      }
      return Promise.resolve({ data: INBOX }); // count: 1
    });
    render(
      <MemoryRouter>
        <ObservationsInbox />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('observations-tab-count-inbox')).toHaveTextContent('1');
      expect(screen.getByTestId('observations-tab-count-sent')).toHaveTextContent('4');
    });
  });

  it('shows an All tab for admins with every observation', async () => {
    authState.user = { role: 'Admin' };
    getMock.mockImplementation((url) => {
      if (url.includes('/all/')) {
        return Promise.resolve({
          data: {
            count: 2,
            results: [
              { id: 10, author: { full_name: 'Bob UH' }, sensitivity: 'normal', subjects_summary: 'Cam Per', last_activity_at: new Date().toISOString(), unread: false, viewer_is_author: false },
              { id: 11, author: { full_name: 'Org Admin' }, sensitivity: 'sensitive', subjects_summary: 'Sam Smith', last_activity_at: new Date().toISOString(), unread: false, viewer_is_author: true },
            ],
          },
        });
      }
      if (url.includes('/sent/')) return Promise.resolve({ data: { count: 0, results: [] } });
      return Promise.resolve({ data: { count: 0, results: [] } });
    });
    render(
      <MemoryRouter>
        <ObservationsInbox />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /All/i })).toBeDefined();
      expect(screen.getByTestId('observations-tab-count-all')).toHaveTextContent('2');
    });

    await userEvent.click(screen.getByRole('button', { name: /All/i }));
    await waitFor(() => {
      expect(screen.getByText('Cam Per')).toBeDefined();
      expect(screen.getByText('Sam Smith')).toBeDefined();
      expect(screen.getByText(/From Bob UH/)).toBeDefined();
      expect(screen.getByText('You wrote this')).toBeDefined();
    });
  });

  it('does not show the All tab for counselors', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/sent/')) return Promise.resolve({ data: { count: 0, results: [] } });
      return Promise.resolve({ data: { count: 0, results: [] } });
    });
    render(
      <MemoryRouter>
        <ObservationsInbox />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Inbox/i })).toBeDefined();
    });
    expect(screen.queryByRole('button', { name: /^All/i })).toBeNull();
    expect(getMock.mock.calls.some(([url]) => url.includes('/all/'))).toBe(false);
  });

  it('filters the list by search query and shows a no-match state', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('/all/')) return Promise.resolve({ data: { count: 0, results: [] } });
      if (url.includes('/sent/')) return Promise.resolve({ data: { count: 0, results: [] } });
      return Promise.resolve({
        data: {
          count: 2,
          results: [
            { id: 1, author: { full_name: 'Bob UH' }, sensitivity: 'normal', subjects_summary: 'Cam Per', last_activity_at: new Date().toISOString(), unread: false },
            { id: 2, author: { full_name: 'Dana C' }, sensitivity: 'normal', subjects_summary: 'Sam Smith', last_activity_at: new Date().toISOString(), unread: false },
          ],
        },
      });
    });
    render(
      <MemoryRouter>
        <ObservationsInbox />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByText('Cam Per')).toBeDefined());

    await userEvent.type(screen.getByTestId('observations-search'), 'Sam');
    await waitFor(() => {
      expect(screen.queryByText('Cam Per')).toBeNull();
      expect(screen.getByText('Sam Smith')).toBeDefined();
    });

    await userEvent.clear(screen.getByTestId('observations-search'));
    await userEvent.type(screen.getByTestId('observations-search'), 'nobody');
    await waitFor(() => {
      expect(screen.getByText('No observations match your search.')).toBeDefined();
    });
  });

  it('reorders the list when sort changes to oldest first', async () => {
    const older = new Date(Date.now() - 7200000).toISOString();
    const newer = new Date(Date.now() - 600000).toISOString();
    getMock.mockImplementation((url) => {
      if (url.includes('/all/')) return Promise.resolve({ data: { count: 0, results: [] } });
      if (url.includes('/sent/')) return Promise.resolve({ data: { count: 0, results: [] } });
      return Promise.resolve({
        data: {
          count: 2,
          results: [
            { id: 1, author: { full_name: 'A' }, sensitivity: 'normal', subjects_summary: 'Newer One', last_activity_at: newer, unread: false },
            { id: 2, author: { full_name: 'B' }, sensitivity: 'normal', subjects_summary: 'Older One', last_activity_at: older, unread: false },
          ],
        },
      });
    });
    render(
      <MemoryRouter>
        <ObservationsInbox />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getAllByTestId('observation-inbox-item').length).toBe(2));

    const recentOrder = screen.getAllByTestId('observation-inbox-item');
    expect(recentOrder[0]).toHaveTextContent('Newer One');

    await userEvent.selectOptions(screen.getByTestId('observations-sort'), 'oldest');
    await waitFor(() => {
      const oldestOrder = screen.getAllByTestId('observation-inbox-item');
      expect(oldestOrder[0]).toHaveTextContent('Older One');
    });
  });
});

describe('ObservationThread', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
  });

  it('renders subjects, body, and submits a reply', async () => {
    getMock.mockResolvedValue({ data: THREAD });
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
      <MemoryRouter initialEntries={['/observations/1']}>
        <Routes>
          <Route path="/observations/:observationId" element={<ObservationThread />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Saw something at swim')).toBeDefined();
      expect(screen.getByText('Cam Per')).toBeDefined();
    });

    const textarea = screen.getByPlaceholderText('Write a reply…');
    await userEvent.type(textarea, 'Got it!');
    await userEvent.click(screen.getByRole('button', { name: /reply/i }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/api/v1/observations/1/replies/', { body: 'Got it!' });
      expect(screen.getByText('Got it!')).toBeDefined();
    });
  });

  it('links subject to profile with observed date when can_view_profile', async () => {
    getMock.mockResolvedValue({ data: THREAD });
    render(
      <MemoryRouter initialEntries={['/observations/1']}>
        <Routes>
          <Route path="/observations/:observationId" element={<ObservationThread />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      const link = screen.getByRole('link', { name: 'Cam Per' });
      expect(link.getAttribute('href')).toBe('/profile/5?date=2026-06-02');
    });
  });

  it('links subject to profile returnTo when from query matches subject', async () => {
    getMock.mockResolvedValue({ data: THREAD });
    const from = encodeURIComponent('/profile/5?date_start=2026-05-01&date_end=2026-05-31');
    render(
      <MemoryRouter initialEntries={[`/observations/1?from=${from}`]}>
        <Routes>
          <Route path="/observations/:observationId" element={<ObservationThread />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      const link = screen.getByRole('link', { name: 'Cam Per' });
      expect(link.getAttribute('href')).toBe('/profile/5?date_start=2026-05-01&date_end=2026-05-31');
    });
  });

  it('shows inbox and contextual back links when from query is set', async () => {
    getMock.mockResolvedValue({ data: THREAD });
    render(
      <MemoryRouter initialEntries={['/observations/1?from=%2Fprofile%2F221%3Fdate%3D2026-05-23']}>
        <Routes>
          <Route path="/observations/:observationId" element={<ObservationThread />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByTestId('observation-back-inbox')).toHaveAttribute('href', '/observations');
      const context = screen.getByTestId('observation-back-context');
      expect(context).toHaveTextContent('Back to profile');
      expect(context).toHaveAttribute('href', '/profile/221?date=2026-05-23');
    });
  });

  it('shows a labeled group-dashboard back link when from_label is set', async () => {
    getMock.mockResolvedValue({ data: THREAD });
    render(
      <MemoryRouter
        initialEntries={[
          '/observations/1?from=%2Fdashboards%2Fgroup%2F78%3Fdate%3D2026-06-03&from_label=Cabin+Birch',
        ]}
      >
        <Routes>
          <Route path="/observations/:observationId" element={<ObservationThread />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      const context = screen.getByTestId('observation-back-context');
      expect(context).toHaveTextContent('Back to Cabin Birch');
      expect(context).toHaveAttribute('href', '/dashboards/group/78?date=2026-06-03');
    });
  });

  it('renders subject name without link when can_view_profile is false', async () => {
    getMock.mockResolvedValue({
      data: {
        ...THREAD,
        subjects: [{ id: 5, full_name: 'Cam Per', can_view_profile: false }],
      },
    });
    render(
      <MemoryRouter initialEntries={['/observations/1']}>
        <Routes>
          <Route path="/observations/:observationId" element={<ObservationThread />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Cam Per')).toBeDefined();
    });
    expect(screen.queryByRole('link', { name: 'Cam Per' })).toBeNull();
  });
});

describe('ObservationComposer', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    // Default: recipient-candidates returns Bob UH; subject search returns Cam Per.
    getMock.mockImplementation((url) => {
      if (url.includes('recipient-candidates')) {
        if (url.includes('confidential')) return Promise.resolve({ data: { persons: [] } });
        return Promise.resolve({ data: { persons: [{ id: 2, full_name: 'Bob UH' }] } });
      }
      if (url.includes('observations/subjects')) {
        return Promise.resolve({ data: { subjects: [{ id: 5, full_name: 'Cam Per' }] } });
      }
      return Promise.resolve({ data: {} });
    });
  });

  it('lists recipient candidates for the default sensitivity', async () => {
    render(
      <MemoryRouter>
        <ObservationComposer onClose={vi.fn()} />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Bob UH')).toBeDefined();
    });
  });

  it('re-filters recipients when sensitivity changes to confidential', async () => {
    render(
      <MemoryRouter>
        <ObservationComposer onClose={vi.fn()} />
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByText('Bob UH'));

    await userEvent.selectOptions(
      screen.getByTestId('observation-composer-sensitivity'),
      'confidential',
    );
    await waitFor(() => {
      expect(screen.getByTestId('observation-no-candidates')).toBeDefined();
    });
  });

  it('adds a subject chip from search', async () => {
    render(
      <MemoryRouter>
        <ObservationComposer onClose={vi.fn()} />
      </MemoryRouter>,
    );
    const search = screen.getByTestId('observation-composer-search');
    await userEvent.type(search, 'Cam');
    const result = await screen.findByRole('button', { name: 'Cam Per' });
    await userEvent.click(result);
    await waitFor(() => {
      const chips = screen.getByTestId('observation-subject-chips');
      expect(chips.textContent).toContain('Cam Per');
    });
  });

  it('shows a message when subject search has no matches', async () => {
    getMock.mockImplementation((url) => {
      if (url.includes('recipient-candidates')) {
        return Promise.resolve({ data: { persons: [] } });
      }
      if (url.includes('observations/subjects')) {
        return Promise.resolve({ data: { subjects: [] } });
      }
      return Promise.resolve({ data: {} });
    });
    render(
      <MemoryRouter>
        <ObservationComposer onClose={vi.fn()} />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByTestId('observation-composer-search'), 'Nobody');
    await waitFor(() => {
      expect(screen.getByText('No matching campers.')).toBeDefined();
    });
  });

  it('blocks submit with no subject', async () => {
    render(
      <MemoryRouter>
        <ObservationComposer onClose={vi.fn()} />
      </MemoryRouter>,
    );
    await waitFor(() => screen.getByText('Bob UH'));
    await userEvent.click(screen.getByTestId('observation-composer-submit'));
    expect(screen.getByText('Please add at least one subject.')).toBeDefined();
    expect(postMock).not.toHaveBeenCalled();
  });
});
