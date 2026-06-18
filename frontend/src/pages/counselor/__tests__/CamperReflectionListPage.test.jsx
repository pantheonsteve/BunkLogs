import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import {
  markConfirmed,
  persistPending,
  SUBMISSION_KIND,
  getPendingEntries,
} from '../../../lib/submissionQueue/queue';
import CamperReflectionListPage from '../CamperReflectionListPage';

const getMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

function makeRoster(overrides = {}) {
  return {
    date: '2026-07-04',
    editable: true,
    template: { id: 7, slug: 'camper-daily', name: 'Camper Daily', version: 1 },
    bunks: [
      {
        id: 100,
        slug: 'bunk-a',
        name: 'Bunk A',
        covered: 1,
        total: 2,
        campers: [
          {
            id: 1,
            name: 'Alice S.',
            preferred_name: 'Alice',
            first_name: 'Alice',
            last_initial: 'S',
            submitted: true,
            reflection_id: 501,
            submitted_at: '2026-07-04T15:00:00Z',
            submitter: { is_self: true, name: null },
            editable: true,
          },
          {
            id: 2,
            name: 'Bob T.',
            preferred_name: 'Bob',
            first_name: 'Bob',
            last_initial: 'T',
            submitted: false,
            reflection_id: null,
            submitted_at: null,
            submitter: null,
            editable: false,
          },
        ],
        off_camp: [
          { id: 3, name: 'Charlie U.', preferred_name: 'Charlie', first_name: 'Charlie', last_initial: 'U' },
        ],
      },
    ],
    ...overrides,
  };
}

function renderPage({ url = '/counselor/camper-reflections' } = {}) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/counselor/camper-reflections" element={<CamperReflectionListPage />} />
        <Route path="/counselor/camper-reflections/:date" element={<CamperReflectionListPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('CamperReflectionListPage', () => {
  beforeEach(async () => {
    getMock.mockReset();
    const entries = await getPendingEntries();
    await Promise.all(entries.map((entry) => markConfirmed(entry.id)));
  });

  it('renders the bunk roster with submitted and not-submitted rows', async () => {
    getMock.mockResolvedValue({ data: makeRoster() });
    renderPage();

    await waitFor(() => expect(screen.getByText('Bunk A')).toBeInTheDocument());

    const alice = screen.getByTestId('camper-row-1');
    expect(alice).toHaveAttribute('data-submitted', 'true');
    expect(alice).toHaveTextContent('Alice S.');
    expect(alice).toHaveTextContent('Submitted by you');

    const bob = screen.getByTestId('camper-row-2');
    expect(bob).toHaveAttribute('data-submitted', 'false');
    expect(bob).toHaveTextContent('Bob T.');
    expect(bob).toHaveTextContent('Needs reflection');
  });

  it('shows submitter attribution for co-counselor submissions', async () => {
    getMock.mockResolvedValue({
      data: makeRoster({
        bunks: [
          {
            id: 100,
            slug: 'bunk-a',
            name: 'Bunk A',
            covered: 1,
            total: 1,
            campers: [
              {
                id: 1,
                name: 'Alice S.',
                preferred_name: 'Alice',
                first_name: 'Alice',
                last_initial: 'S',
                submitted: true,
                reflection_id: 501,
                submitted_at: '2026-07-04T15:00:00Z',
                submitter: { is_self: false, name: 'Casey C.' },
                editable: true,
              },
            ],
            off_camp: [],
          },
        ],
      }),
    });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('camper-row-1')).toBeInTheDocument());
    expect(screen.getByText('Submitted by Casey C.')).toBeInTheDocument();
  });

  it('renders off-camp campers in their own subsection', async () => {
    getMock.mockResolvedValue({ data: makeRoster() });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('off-camp-row-3')).toBeInTheDocument());
    expect(screen.getByText(/Off-camp today/i)).toBeInTheDocument();
    expect(screen.getByText(/Charlie U\./)).toBeInTheDocument();
  });

  it('renders Add and Edit CTAs for editable today rows', async () => {
    getMock.mockResolvedValue({ data: makeRoster() });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('camper-row-1-edit')).toBeInTheDocument());
    expect(screen.getByTestId('camper-row-1-edit')).toHaveAttribute(
      'href',
      '/counselor/camper-reflections/501/edit',
    );
    expect(screen.getByTestId('camper-row-2-new')).toHaveAttribute(
      'href',
      expect.stringContaining('/counselor/camper-reflections/new?subject=2&bunk=100'),
    );
  });

  it('hides Add/Edit affordances when the roster is read-only (past date)', async () => {
    getMock.mockResolvedValue({
      data: makeRoster({
        date: '2026-07-01',
        editable: false,
        bunks: [
          {
            id: 100,
            slug: 'bunk-a',
            name: 'Bunk A',
            covered: 1,
            total: 1,
            campers: [
              {
                id: 1,
                name: 'Alice S.',
                preferred_name: 'Alice',
                first_name: 'Alice',
                last_initial: 'S',
                submitted: true,
                reflection_id: 501,
                submitted_at: '2026-07-01T15:00:00Z',
                submitter: { is_self: true, name: null },
                editable: false,
              },
            ],
            off_camp: [],
          },
        ],
      }),
    });
    renderPage({ url: '/counselor/camper-reflections/2026-07-01' });
    await waitFor(() => expect(screen.getByTestId('camper-row-1')).toBeInTheDocument());
    expect(screen.getByTestId('camper-roster-readonly-banner')).toBeInTheDocument();
    expect(screen.queryByTestId('camper-row-1-edit')).toBeNull();
    expect(screen.getByTestId('camper-row-1-readonly')).toBeInTheDocument();
  });

  it('passes the date param to the API', async () => {
    getMock.mockResolvedValue({ data: makeRoster({ date: '2026-07-01' }) });
    renderPage({ url: '/counselor/camper-reflections/2026-07-01' });
    await waitFor(() => expect(getMock).toHaveBeenCalled());
    const lastCall = getMock.mock.calls[0];
    expect(lastCall[0]).toBe('/api/v1/counselor/camper-reflections/');
    expect(lastCall[1].params).toEqual({ date: '2026-07-01' });
  });

  it('renders the empty state when the viewer has no bunks', async () => {
    getMock.mockResolvedValue({
      data: { date: '2026-07-04', editable: true, template: null, bunks: [] },
    });
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId('camper-roster-empty')).toBeInTheDocument(),
    );
  });

  it('shows Syncing badge when a camper reflection is pending in the queue', async () => {
    await persistPending({
      kind: SUBMISSION_KIND.CAMPER_REFLECTION,
      clientSubmissionId: '33333333-3333-4333-8333-333333333333',
      metadata: { subjectId: 2, date: '2026-07-04', assignmentGroupId: 100 },
      payload: {
        subjectId: 2,
        assignmentGroupId: 100,
        answers: { note: 'pending' },
        language: 'en',
        teamVisibility: 'team',
      },
    });
    getMock.mockResolvedValue({ data: makeRoster() });
    renderPage();

    await waitFor(() => expect(screen.getByTestId('camper-row-2')).toBeInTheDocument());
    expect(screen.getByTestId('camper-row-2')).toHaveTextContent('Syncing…');
  });

  it('shows the error banner on 400 invalid date', async () => {
    getMock.mockRejectedValue({
      response: { status: 400, data: { detail: "Invalid 'date' query parameter; expected YYYY-MM-DD." } },
    });
    renderPage({ url: '/counselor/camper-reflections/garbage' });
    await waitFor(() => expect(screen.getByTestId('camper-roster-error')).toBeInTheDocument());
  });
});
