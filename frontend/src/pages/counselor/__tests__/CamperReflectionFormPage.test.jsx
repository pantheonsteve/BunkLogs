import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import { getPendingEntries, markConfirmed } from '../../../lib/submissionQueue/queue';
import CamperReflectionFormPage from '../CamperReflectionFormPage';

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

function ListProbe() {
  const loc = useLocation();
  return (
    <div data-testid="list-probe" data-pathname={loc.pathname}>
      list
    </div>
  );
}

const templateSchema = {
  fields: [
    { key: 'note', type: 'text', prompts: { en: 'Note?' } },
    {
      key: 'r',
      type: 'rating_group',
      prompts: { en: 'Ratings?' },
      scale_labels: { en: ['1', '2', '3', '4'] },
      categories: [{ key: 'effort', labels: { en: 'Effort' } }],
    },
  ],
};

const templatePayload = {
  id: 7,
  name: 'Camper daily',
  slug: 'camper-daily',
  version: 1,
  languages: ['en', 'es'],
  supports_privacy: true,
  schema: templateSchema,
};

const rosterPayload = {
  date: '2026-07-04',
  editable: true,
  template: { id: 7, slug: 'camper-daily', name: 'Camper daily', version: 1 },
  bunks: [
    {
      id: 100,
      slug: 'bunk-a',
      name: 'Bunk A',
      covered: 0,
      total: 1,
      campers: [
        {
          id: 11,
          name: 'Diana W.',
          preferred_name: 'Diana',
          first_name: 'Diana',
          last_initial: 'W',
          submitted: false,
          reflection_id: null,
          submitted_at: null,
          submitter: null,
          editable: false,
        },
      ],
      off_camp: [],
    },
  ],
};

function renderCreate(query = '?subject=11&bunk=100&name=Diana%20W.') {
  return render(
    <MemoryRouter initialEntries={[`/counselor/camper-reflections/new${query}`]}>
      <Routes>
        <Route
          path="/counselor/camper-reflections/new"
          element={<CamperReflectionFormPage />}
        />
        <Route path="/counselor/camper-reflections" element={<ListProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

function renderEdit(reflectionId = 501) {
  return render(
    <MemoryRouter initialEntries={[`/counselor/camper-reflections/${reflectionId}/edit`]}>
      <Routes>
        <Route
          path="/counselor/camper-reflections/:reflectionId/edit"
          element={<CamperReflectionFormPage />}
        />
        <Route path="/counselor/camper-reflections" element={<ListProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

function arrangeCreateRoute() {
  // First call: roster fetch (for template id).
  getMock.mockResolvedValueOnce({ data: rosterPayload });
  // Second call: template-by-id fetch (for schema).
  getMock.mockResolvedValueOnce({ data: templatePayload });
}

describe('CamperReflectionFormPage', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    patchMock.mockReset();
    localStorage.clear();
  });

  describe('create mode', () => {
    it('loads the active template schema and renders fields', async () => {
      arrangeCreateRoute();
      renderCreate();
      await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
      expect(screen.getByText('Ratings?')).toBeInTheDocument();
      expect(screen.getByText(/About Diana W\./i)).toBeInTheDocument();
    });

    it('shows the audience disclosure with the camper-reflection labels', async () => {
      arrangeCreateRoute();
      renderCreate();
      await waitFor(() => expect(screen.getByTestId('audience-disclosure')).toBeInTheDocument());
      expect(screen.getByTestId('audience-disclosure-labels')).toHaveTextContent(
        'Admin, Camper Care, Counselor, Leadership Team, Unit Head',
      );
    });

    it('blocks submit while required fields are missing', async () => {
      const user = userEvent.setup();
      arrangeCreateRoute();
      renderCreate();
      await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
      await user.click(screen.getByTestId('camper-reflection-submit'));
      expect(postMock).not.toHaveBeenCalled();
      expect(screen.getByText(/Rate every category/i)).toBeInTheDocument();
    });

    it('POSTs with subject + bunk + a UUID client_submission_id, then navigates back to the list', async () => {
      const user = userEvent.setup();
      arrangeCreateRoute();
      postMock.mockResolvedValue({ data: { id: 999 }, status: 201 });
      renderCreate();
      await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());

      await user.type(screen.getByTestId('reflect-input-note'), 'great day');
      const ratingButtons = screen.getAllByRole('button', { name: '3' });
      await user.click(ratingButtons[0]);

      await user.click(screen.getByTestId('camper-reflection-submit'));
      await waitFor(() => expect(postMock).toHaveBeenCalled());

      expect(postMock.mock.calls[0][0]).toBe('/api/v1/counselor/camper-reflections/');
      const body = postMock.mock.calls[0][1];
      expect(body.subject_id).toBe(11);
      expect(body.assignment_group_id).toBe(100);
      expect(body.answers.note).toBe('great day');
      expect(body.answers.r).toEqual({ effort: 3 });
      expect(body.team_visibility).toBe('team');
      expect(typeof body.client_submission_id).toBe('string');
      expect(body.client_submission_id.length).toBeGreaterThanOrEqual(36);

      await waitFor(() => expect(screen.getByTestId('list-probe')).toBeInTheDocument());
    });

    it('queues submission with stable client_submission_id on retryable server error', async () => {
      const entries = await getPendingEntries();
      await Promise.all(entries.map((entry) => markConfirmed(entry.id)));

      const user = userEvent.setup();
      arrangeCreateRoute();
      postMock.mockRejectedValue({ response: { status: 500, data: { detail: 'oops' } } });
      renderCreate();
      await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
      await user.type(screen.getByTestId('reflect-input-note'), 'retry note');
      const ratingButtons = screen.getAllByRole('button', { name: '3' });
      await user.click(ratingButtons[0]);

      await user.click(screen.getByTestId('camper-reflection-submit'));
      await waitFor(() => expect(screen.getByTestId('list-probe')).toBeInTheDocument());

      const pending = await getPendingEntries();
      expect(pending).toHaveLength(1);
      expect(pending[0].clientSubmissionId).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
      );
      expect(pending[0].metadata?.subjectId).toBe(11);
    });

    it('restores draft answers and client_submission_id after remount', async () => {
      arrangeCreateRoute();
      const { unmount } = renderCreate();
      await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());

      const draftKey = 'counselorDraft:camper:11:2026-07-04';
      localStorage.setItem(
        draftKey,
        JSON.stringify({
          answers: { note: 'saved draft' },
          clientSubmissionId: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
          updatedAt: Date.now(),
        }),
      );

      unmount();
      arrangeCreateRoute();
      renderCreate();
      await waitFor(() => expect(screen.getByTestId('reflect-input-note')).toHaveValue('saved draft'));
    });

    it('surfaces a 403 from the server on closed edit window', async () => {
      const user = userEvent.setup();
      arrangeCreateRoute();
      postMock.mockRejectedValue({
        response: {
          status: 403,
          data: { detail: 'Camper is marked off-camp today.' },
        },
      });
      renderCreate();
      await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
      await user.type(screen.getByTestId('reflect-input-note'), 'late');
      const ratingButtons = screen.getAllByRole('button', { name: '3' });
      await user.click(ratingButtons[0]);
      await user.click(screen.getByTestId('camper-reflection-submit'));
      await waitFor(() => expect(screen.getByTestId('camper-reflection-submit-error')).toBeInTheDocument());
      expect(screen.getByTestId('camper-reflection-submit-error')).toHaveTextContent(
        /Camper is marked off-camp today/i,
      );
    });

    it('renders the load error when no template is configured', async () => {
      getMock.mockResolvedValueOnce({
        data: { date: '2026-07-04', editable: true, template: null, bunks: [] },
      });
      renderCreate();
      await waitFor(() =>
        expect(screen.getByTestId('camper-reflection-load-error')).toBeInTheDocument(),
      );
    });
  });

  describe('edit mode', () => {
    const existingReflection = {
      id: 501,
      subject: 11,
      assignment_group: 100,
      template: 7,
      template_meta: { id: 7, slug: 'camper-daily', name: 'Camper daily', version: 1 },
      answers: { note: 'already filled', r: { effort: 4 } },
      language: 'en',
      team_visibility: 'team',
    };

    function arrangeEditRoute() {
      // First call: GET /api/v1/reflections/501/
      getMock.mockResolvedValueOnce({ data: existingReflection });
      // Second call: GET /api/v1/templates/7/
      getMock.mockResolvedValueOnce({ data: templatePayload });
    }

    it('pre-fills existing answers, language, and visibility', async () => {
      arrangeEditRoute();
      renderEdit();
      await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
      expect(screen.getByTestId('reflect-input-note')).toHaveValue('already filled');
      expect(screen.getByTestId('camper-reflection-visibility-team')).toHaveAttribute(
        'aria-pressed',
        'true',
      );
    });

    it('PATCHes only the changed fields', async () => {
      const user = userEvent.setup();
      arrangeEditRoute();
      patchMock.mockResolvedValue({ data: { id: 501 } });
      renderEdit();
      await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());

      const noteInput = screen.getByTestId('reflect-input-note');
      await user.clear(noteInput);
      await user.type(noteInput, 'edited note');

      await user.click(screen.getByTestId('camper-reflection-submit'));
      await waitFor(() => expect(patchMock).toHaveBeenCalled());

      expect(patchMock.mock.calls[0][0]).toBe('/api/v1/counselor/camper-reflections/501/');
      const body = patchMock.mock.calls[0][1];
      expect(body.answers.note).toBe('edited note');
      expect(body.team_visibility).toBe('team');
      expect(body).not.toHaveProperty('client_submission_id');
      await waitFor(() => expect(screen.getByTestId('list-probe')).toBeInTheDocument());
    });

    it('surfaces a 403 edit-window-closed response', async () => {
      const user = userEvent.setup();
      arrangeEditRoute();
      patchMock.mockRejectedValue({
        response: {
          status: 403,
          data: {
            detail: 'This reflection can no longer be edited (the edit window has closed).',
          },
        },
      });
      renderEdit();
      await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
      const noteInput = screen.getByTestId('reflect-input-note');
      await user.clear(noteInput);
      await user.type(noteInput, 'too late');
      await user.click(screen.getByTestId('camper-reflection-submit'));
      await waitFor(() => expect(screen.getByTestId('camper-reflection-submit-error')).toBeInTheDocument());
      expect(screen.getByTestId('camper-reflection-submit-error')).toHaveTextContent(
        /edit window has closed/i,
      );
    });

    it('renders 404 friendly text when the reflection is gone', async () => {
      getMock.mockRejectedValueOnce({ response: { status: 404, data: { detail: 'not found' } } });
      renderEdit();
      await waitFor(() => expect(screen.getByTestId('camper-reflection-load-error')).toBeInTheDocument());
      expect(screen.getByTestId('camper-reflection-load-error')).toHaveTextContent(/Reflection not found/i);
    });
  });
});
