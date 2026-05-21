import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import CounselorSelfReflectionPage from '../CounselorSelfReflectionPage';

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

function PathProbe() {
  const loc = useLocation();
  return (
    <div data-testid="path-probe" data-pathname={loc.pathname}>
      probe: {loc.pathname}
    </div>
  );
}

const selfTemplate = {
  id: 9,
  name: 'Counselor Self-Reflection',
  slug: 'counselor-self-reflection',
  version: 1,
  languages: ['en', 'es'],
  supports_privacy: false,
  schema: {
    fields: [
      {
        key: 'day_off',
        type: 'yes_no',
        required: false,
        prompts: { en: 'Are you taking a day off today?' },
      },
      {
        key: 'overall_day',
        type: 'single_rating',
        required: false,
        scale: [1, 5],
        scale_labels: { en: ['Difficult', 'Tough', 'OK', 'Good', 'Great'] },
        prompts: { en: 'How was today overall?' },
      },
      {
        key: 'wins',
        type: 'text_list',
        required: false,
        min_items: 1,
        max_items: 3,
        prompts: { en: 'What went well?' },
      },
      {
        key: 'concern',
        type: 'textarea',
        required: false,
        prompts: { en: 'Anything to flag?' },
      },
    ],
  },
};

const dashboardNoSubmission = {
  today: '2026-07-04',
  sections: {
    self_reflection: {
      state: 'none',
      submitted: false,
      reflection_id: null,
      template: {
        id: 9,
        slug: 'counselor-self-reflection',
        name: 'Counselor Self-Reflection',
        version: 1,
      },
    },
  },
};

function renderCreate() {
  return render(
    <MemoryRouter initialEntries={['/counselor/self-reflection']}>
      <Routes>
        <Route path="/counselor/self-reflection" element={<CounselorSelfReflectionPage />} />
        <Route
          path="/counselor/self-reflection/:reflectionId/edit"
          element={<CounselorSelfReflectionPage />}
        />
        <Route path="/counselor" element={<PathProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

function renderEdit(reflectionId = 501) {
  return render(
    <MemoryRouter initialEntries={[`/counselor/self-reflection/${reflectionId}/edit`]}>
      <Routes>
        <Route
          path="/counselor/self-reflection/:reflectionId/edit"
          element={<CounselorSelfReflectionPage />}
        />
        <Route path="/counselor" element={<PathProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('CounselorSelfReflectionPage', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    patchMock.mockReset();
  });

  describe('create mode', () => {
    function arrangeCreate() {
      // First call: dashboard fetch (to discover the template + existing reflection)
      getMock.mockResolvedValueOnce({ data: dashboardNoSubmission });
      // Second call: template-by-id fetch
      getMock.mockResolvedValueOnce({ data: selfTemplate });
    }

    it('loads the template via dashboard + template-by-id and renders the schema', async () => {
      arrangeCreate();
      renderCreate();
      await waitFor(() => expect(screen.getByText('How was today overall?')).toBeInTheDocument());
      expect(screen.getByText('What went well?')).toBeInTheDocument();
      expect(screen.getByText('Anything to flag?')).toBeInTheDocument();

      // The day_off field should NOT render inside the schema area;
      // it's elevated to the prominent toggle at top.
      const schemaArea = screen.queryByTestId('reflect-input-day_off');
      expect(schemaArea).toBeNull();
      expect(screen.getByTestId('self-reflection-day-off-toggle')).toBeInTheDocument();
    });

    it('shows the audience disclosure with the canonical self-reflection labels', async () => {
      arrangeCreate();
      renderCreate();
      await waitFor(() => expect(screen.getByTestId('audience-disclosure')).toBeInTheDocument());
      expect(screen.getByTestId('audience-disclosure-labels')).toHaveTextContent(
        'Admin, Counselor, Leadership Team, Unit Head',
      );
    });

    it('toggling day-off hides the schema fields and changes the submit label', async () => {
      const user = userEvent.setup();
      arrangeCreate();
      renderCreate();
      await waitFor(() => expect(screen.getByText('How was today overall?')).toBeInTheDocument());

      await user.click(screen.getByTestId('self-reflection-day-off-toggle'));

      expect(screen.queryByText('How was today overall?')).toBeNull();
      expect(screen.queryByText('What went well?')).toBeNull();
      expect(screen.getByTestId('self-reflection-submit')).toHaveTextContent(/Mark day off/i);
    });

    it('POSTs the day-off shortcut payload when toggle is on', async () => {
      const user = userEvent.setup();
      arrangeCreate();
      postMock.mockResolvedValue({ data: { id: 600 }, status: 201 });
      renderCreate();
      await waitFor(() => expect(screen.getByText('How was today overall?')).toBeInTheDocument());

      await user.click(screen.getByTestId('self-reflection-day-off-toggle'));
      await user.click(screen.getByTestId('self-reflection-submit'));

      await waitFor(() => expect(postMock).toHaveBeenCalled());
      const [url, body] = postMock.mock.calls[0];
      expect(url).toBe('/api/v1/counselor/self-reflection/');
      expect(body.day_off).toBe(true);
      expect(body).not.toHaveProperty('answers');
      expect(typeof body.client_submission_id).toBe('string');

      await waitFor(() => expect(screen.getByTestId('path-probe')).toHaveAttribute(
        'data-pathname',
        '/counselor',
      ));
    });

    it('POSTs a full payload when day-off is off and fields are filled', async () => {
      const user = userEvent.setup();
      arrangeCreate();
      postMock.mockResolvedValue({ data: { id: 601 }, status: 201 });
      renderCreate();
      await waitFor(() => expect(screen.getByText('How was today overall?')).toBeInTheDocument());

      // Pick a rating
      const ratingButtons = screen.getAllByRole('button', { name: '4' });
      await user.click(ratingButtons[0]);

      // Fill at least one win
      const wins = screen.getAllByRole('textbox');
      await user.type(wins[0], 'lunchtime activity');

      await user.click(screen.getByTestId('self-reflection-submit'));
      await waitFor(() => expect(postMock).toHaveBeenCalled());

      const body = postMock.mock.calls[0][1];
      expect(body.day_off).toBe(false);
      expect(body.answers.overall_day).toBe(4);
      expect(body.answers.wins).toEqual(expect.arrayContaining(['lunchtime activity']));
    });

    it('redirects to the edit URL when a reflection already exists for today', async () => {
      // Dashboard reports a submitted reflection for today.
      getMock.mockResolvedValueOnce({
        data: {
          today: '2026-07-04',
          sections: {
            self_reflection: {
              state: 'complete',
              submitted: true,
              reflection_id: 777,
              template: {
                id: 9,
                slug: 'counselor-self-reflection',
                name: 'Counselor Self-Reflection',
                version: 1,
              },
            },
          },
        },
      });
      // After redirect, the edit branch loads the reflection + template.
      getMock.mockResolvedValueOnce({
        data: {
          id: 777,
          template: 9,
          subject: 1,
          author: 1,
          answers: { overall_day: 3 },
          language: 'en',
          team_visibility: 'team',
        },
      });
      getMock.mockResolvedValueOnce({ data: selfTemplate });

      renderCreate();

      await waitFor(() => expect(getMock).toHaveBeenCalledTimes(3));
      // Final page renders edit form
      await waitFor(() => expect(screen.getByTestId('self-reflection-submit')).toBeInTheDocument());
      expect(screen.getByTestId('self-reflection-submit')).toHaveTextContent(/Save changes/i);
    });

    it('shows a load error when no self template is configured', async () => {
      getMock.mockResolvedValueOnce({
        data: {
          today: '2026-07-04',
          sections: {
            self_reflection: {
              state: 'complete',
              submitted: false,
              reflection_id: null,
              template: null,
            },
          },
        },
      });
      renderCreate();
      await waitFor(() =>
        expect(screen.getByTestId('self-reflection-load-error')).toBeInTheDocument(),
      );
    });
  });

  describe('edit mode', () => {
    const existing = {
      id: 501,
      template: 9,
      template_meta: { id: 9, slug: 'counselor-self-reflection', name: 'Counselor Self-Reflection', version: 1 },
      answers: { overall_day: 3, wins: ['nice morning'], concern: '' },
      language: 'en',
      subject: 1,
      author: 1,
      team_visibility: 'team',
    };

    function arrangeEdit(reflection = existing, template = selfTemplate) {
      getMock.mockResolvedValueOnce({ data: reflection });
      getMock.mockResolvedValueOnce({ data: template });
    }

    it('prefills existing answers and language', async () => {
      arrangeEdit();
      renderEdit();
      await waitFor(() => expect(screen.getByText('How was today overall?')).toBeInTheDocument());
      const wins = screen.getAllByRole('textbox');
      expect(wins[0]).toHaveValue('nice morning');
    });

    it('detects day-off state in an existing reflection and pre-toggles', async () => {
      arrangeEdit({
        ...existing,
        answers: { day_off: true },
      });
      renderEdit();
      await waitFor(() => expect(screen.getByTestId('self-reflection-day-off-toggle')).toBeChecked());
      expect(screen.queryByText('How was today overall?')).toBeNull();
    });

    it('PATCHes the day-off flip when the user toggles it on', async () => {
      const user = userEvent.setup();
      arrangeEdit();
      patchMock.mockResolvedValue({ data: { id: 501 } });
      renderEdit();
      await waitFor(() => expect(screen.getByText('How was today overall?')).toBeInTheDocument());

      await user.click(screen.getByTestId('self-reflection-day-off-toggle'));
      await user.click(screen.getByTestId('self-reflection-submit'));

      await waitFor(() => expect(patchMock).toHaveBeenCalled());
      const [url, body] = patchMock.mock.calls[0];
      expect(url).toBe('/api/v1/counselor/self-reflection/501/');
      expect(body.day_off).toBe(true);
      expect(body).not.toHaveProperty('answers');
    });

    it('PATCHes answers + language when the user edits without toggling day-off', async () => {
      const user = userEvent.setup();
      arrangeEdit();
      patchMock.mockResolvedValue({ data: { id: 501 } });
      renderEdit();
      await waitFor(() => expect(screen.getByText('How was today overall?')).toBeInTheDocument());

      const wins = screen.getAllByRole('textbox');
      await user.clear(wins[0]);
      await user.type(wins[0], 'updated win');

      await user.click(screen.getByTestId('self-reflection-submit'));
      await waitFor(() => expect(patchMock).toHaveBeenCalled());
      const body = patchMock.mock.calls[0][1];
      expect(body.day_off).toBe(false);
      expect(body.answers.wins).toEqual(expect.arrayContaining(['updated win']));
      expect(body.language).toBe('en');
    });

    it('surfaces a 403 edit-window-closed response verbatim', async () => {
      const user = userEvent.setup();
      arrangeEdit();
      patchMock.mockRejectedValue({
        response: {
          status: 403,
          data: {
            detail: 'This reflection can no longer be edited (the edit window has closed).',
          },
        },
      });
      renderEdit();
      await waitFor(() => expect(screen.getByText('How was today overall?')).toBeInTheDocument());

      const wins = screen.getAllByRole('textbox');
      await user.clear(wins[0]);
      await user.type(wins[0], 'too late');
      await user.click(screen.getByTestId('self-reflection-submit'));
      await waitFor(() => expect(screen.getByTestId('self-reflection-submit-error')).toBeInTheDocument());
      expect(screen.getByTestId('self-reflection-submit-error')).toHaveTextContent(
        /edit window has closed/i,
      );
    });

    it('renders 404 friendly text when the reflection is gone', async () => {
      getMock.mockRejectedValueOnce({ response: { status: 404, data: { detail: 'not found' } } });
      renderEdit();
      await waitFor(() =>
        expect(screen.getByTestId('self-reflection-load-error')).toBeInTheDocument(),
      );
      expect(screen.getByTestId('self-reflection-load-error')).toHaveTextContent(
        /Reflection not found/i,
      );
    });
  });
});
