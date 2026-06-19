import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import ReflectionFormPage from './ReflectionFormPage';

function SummaryProbe() {
  const loc = useLocation();
  return (
    <div data-testid="summary" data-state={JSON.stringify(loc.state ?? {})}>
      Summary
    </div>
  );
}

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock('../api', () => ({
  default: {
    get: (...args) => getMock(...args),
    post: (...args) => postMock(...args),
  },
}));

const templatePayload = {
  id: 9,
  name: 'Test weekly',
  cadence: 'weekly',
  languages: ['en', 'es'],
  program_slug: 'prog-a',
  supports_privacy: true,
  schema: {
    fields: [
      { key: 'note', type: 'text', prompts: { en: 'Note?' } },
      {
        key: 'r',
        type: 'rating_group',
        scale_labels: { en: ['1', '2', '3', '4'] },
        categories: [{ key: 'effort', labels: { en: 'Effort' } }],
      },
    ],
  },
  language: 'en',
};

const allFieldsTemplate = {
  id: 20,
  name: 'All fields',
  cadence: 'weekly',
  languages: ['en'],
  program_slug: 'prog-c',
  schema: {
    fields: [
      { key: 'txt', type: 'text', prompts: { en: 'Text field?' } },
      { key: 'ta', type: 'textarea', prompts: { en: 'Textarea field?' }, max_length: 200 },
      { key: 'tl', type: 'text_list', prompts: { en: 'List field?' }, min_items: 1, max_items: 3 },
      {
        key: 'rg',
        type: 'rating_group',
        prompts: { en: 'Ratings?' },
        scale_labels: { en: ['1', '2', '3', '4'] },
        categories: [{ key: 'cat1', labels: { en: 'Cat1' } }],
      },
      {
        key: 'sc',
        type: 'single_choice',
        prompts: { en: 'Single choice?' },
        options: [{ key: 'a', labels: { en: 'Option A' } }],
      },
      {
        key: 'mc',
        type: 'multiple_choice',
        prompts: { en: 'Multi choice?' },
        options: [{ key: 'x', labels: { en: 'Option X' } }],
      },
    ],
  },
  language: 'en',
};

function renderPage(search = '') {
  return render(
    <MemoryRouter initialEntries={[`/reflect${search}`]}>
      <Routes>
        <Route path="/reflect" element={<ReflectionFormPage />} />
        <Route path="/reflect/summary" element={<SummaryProbe />} />
        <Route path="/tasks" element={<div data-testid="tasks-page">Tasks</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ReflectionFormPage', () => {
  beforeEach(() => {
    localStorage.clear();
    getMock.mockReset();
    postMock.mockReset();
    getMock.mockResolvedValue({ data: { ...templatePayload } });
  });

  it('renders dynamic fields from schema', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Test weekly')).toBeInTheDocument());
    expect(screen.getByText('Note?')).toBeInTheDocument();
    expect(screen.getByText('Effort')).toBeInTheDocument();
  });

  it('language switch re-fetches template', async () => {
    const user = userEvent.setup();
    getMock.mockResolvedValueOnce({ data: { ...templatePayload, language: 'en' } });
    getMock.mockResolvedValueOnce({
      data: {
        ...templatePayload,
        language: 'es',
        schema: {
          fields: [{ key: 'note', type: 'text', prompts: { es: 'Nota?' } }],
        },
      },
    });
    renderPage();
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(1));
    const es = screen.getByRole('button', { name: 'Español' });
    await user.click(es);
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(2));
    const lastCall = getMock.mock.calls.at(-1);
    expect(lastCall[0]).toBe('/api/v1/reflections/template-for-me/');
    expect(lastCall[1].params.language).toBe('es');
  });

  it('validation prevents submit when required fields empty', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
    await user.type(screen.getByTestId('reflect-period-start'), '2026-06-01');
    await user.type(screen.getByTestId('reflect-period-end'), '2026-06-07');
    await user.type(screen.getByTestId('reflect-input-note'), 'filled note');
    await user.click(screen.getByRole('button', { name: /Submit reflection/i }));
    expect(postMock).not.toHaveBeenCalled();
    expect(screen.getByText(/Rate every category/i)).toBeInTheDocument();
  });

  it('successful submit posts correct payload and navigates', async () => {
    const user = userEvent.setup();
    postMock.mockResolvedValue({
      data: { id: 100, answers: { note: 'ok', r: { effort: 2 } } },
    });
    renderPage();
    await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
    await user.type(screen.getByTestId('reflect-input-note'), 'ok');
    await user.type(screen.getByTestId('reflect-period-start'), '2026-06-01');
    await user.type(screen.getByTestId('reflect-period-end'), '2026-06-07');
    const effortButtons = screen.getAllByRole('button', { name: '2' });
    await user.click(effortButtons[0]);
    await user.click(screen.getByRole('button', { name: /Submit reflection/i }));
    await waitFor(() => expect(postMock).toHaveBeenCalled());
    const body = postMock.mock.calls[0][1];
    expect(body.program_slug).toBe('prog-a');
    expect(body.template).toBe(9);
    expect(body.answers.note).toBe('ok');
    await waitFor(() => expect(screen.getByTestId('summary')).toBeInTheDocument());
  });

  it('returns to /tasks after submit when opened from tasks (prefilled params)', async () => {
    const user = userEvent.setup();
    postMock.mockResolvedValue({ data: { id: 200, answers: { note: 'ok' } } });
    renderPage('?template=9&program=prog-a&period_start=2026-06-01&period_end=2026-06-01');
    await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
    await user.type(screen.getByTestId('reflect-input-note'), 'ok');
    const effortButtons = screen.getAllByRole('button', { name: '2' });
    await user.click(effortButtons[0]);
    await user.click(screen.getByRole('button', { name: /Submit reflection/i }));
    await waitFor(() => expect(postMock).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByTestId('tasks-page')).toBeInTheDocument());
    expect(screen.queryByTestId('summary')).not.toBeInTheDocument();
  });

  it('defaults team_visibility to team in the submit payload', async () => {
    const user = userEvent.setup();
    postMock.mockResolvedValue({ data: { id: 101 } });
    renderPage();
    await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
    await user.type(screen.getByTestId('reflect-input-note'), 'team default');
    await user.type(screen.getByTestId('reflect-period-start'), '2026-06-01');
    await user.type(screen.getByTestId('reflect-period-end'), '2026-06-07');
    const effortButtons = screen.getAllByRole('button', { name: '2' });
    await user.click(effortButtons[0]);
    await user.click(screen.getByRole('button', { name: /Submit reflection/i }));
    await waitFor(() => expect(postMock).toHaveBeenCalled());
    expect(postMock.mock.calls[0][1].team_visibility).toBe('team');
  });

  it('sends team_visibility=supervisors_only when toggled', async () => {
    const user = userEvent.setup();
    postMock.mockResolvedValue({ data: { id: 102 } });
    renderPage();
    await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
    await user.click(screen.getByTestId('reflect-visibility-supervisors_only'));
    await user.type(screen.getByTestId('reflect-input-note'), 'private note');
    await user.type(screen.getByTestId('reflect-period-start'), '2026-06-01');
    await user.type(screen.getByTestId('reflect-period-end'), '2026-06-07');
    const effortButtons = screen.getAllByRole('button', { name: '2' });
    await user.click(effortButtons[0]);
    await user.click(screen.getByRole('button', { name: /Submit reflection/i }));
    await waitFor(() => expect(postMock).toHaveBeenCalled());
    expect(postMock.mock.calls[0][1].team_visibility).toBe('supervisors_only');
    // 3.24: the summary route receives the same flag so it can render the chip.
    await waitFor(() => expect(screen.getByTestId('summary')).toBeInTheDocument());
    const state = JSON.parse(screen.getByTestId('summary').dataset.state);
    expect(state.teamVisibility).toBe('supervisors_only');
  });

  it('passes teamVisibility=team to summary state for team submissions', async () => {
    const user = userEvent.setup();
    postMock.mockResolvedValue({ data: { id: 103 } });
    renderPage();
    await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
    await user.type(screen.getByTestId('reflect-input-note'), 'team note');
    await user.type(screen.getByTestId('reflect-period-start'), '2026-06-01');
    await user.type(screen.getByTestId('reflect-period-end'), '2026-06-07');
    const effortButtons = screen.getAllByRole('button', { name: '2' });
    await user.click(effortButtons[0]);
    await user.click(screen.getByRole('button', { name: /Submit reflection/i }));
    await waitFor(() => expect(screen.getByTestId('summary')).toBeInTheDocument());
    const state = JSON.parse(screen.getByTestId('summary').dataset.state);
    expect(state.teamVisibility).toBe('team');
  });

  it('passes teamVisibility=team when template does not support privacy', async () => {
    const user = userEvent.setup();
    getMock.mockResolvedValue({
      data: { ...templatePayload, supports_privacy: false },
    });
    postMock.mockResolvedValue({ data: { id: 104 } });
    renderPage();
    await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
    await user.type(screen.getByTestId('reflect-input-note'), 'no toggle');
    await user.type(screen.getByTestId('reflect-period-start'), '2026-06-01');
    await user.type(screen.getByTestId('reflect-period-end'), '2026-06-07');
    const effortButtons = screen.getAllByRole('button', { name: '2' });
    await user.click(effortButtons[0]);
    await user.click(screen.getByRole('button', { name: /Submit reflection/i }));
    await waitFor(() => expect(screen.getByTestId('summary')).toBeInTheDocument());
    const state = JSON.parse(screen.getByTestId('summary').dataset.state);
    expect(state.teamVisibility).toBe('team');
  });

  it('shows the supervisors-only helper text only when selected', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
    expect(screen.queryByTestId('reflect-visibility-helper')).toBeNull();
    await user.click(screen.getByTestId('reflect-visibility-supervisors_only'));
    expect(screen.getByTestId('reflect-visibility-helper')).toBeInTheDocument();
    await user.click(screen.getByTestId('reflect-visibility-team'));
    expect(screen.queryByTestId('reflect-visibility-helper')).toBeNull();
  });

  it('hides the privacy toggle when the template does not support it', async () => {
    getMock.mockResolvedValue({
      data: { ...templatePayload, supports_privacy: false },
    });
    renderPage();
    await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
    expect(screen.queryByTestId('reflect-visibility')).toBeNull();
  });

  it('omits team_visibility from payload when the template does not support it', async () => {
    const user = userEvent.setup();
    getMock.mockResolvedValue({
      data: { ...templatePayload, supports_privacy: false },
    });
    postMock.mockResolvedValue({ data: { id: 103 } });
    renderPage();
    await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
    await user.type(screen.getByTestId('reflect-input-note'), 'no flag');
    await user.type(screen.getByTestId('reflect-period-start'), '2026-06-01');
    await user.type(screen.getByTestId('reflect-period-end'), '2026-06-07');
    const effortButtons = screen.getAllByRole('button', { name: '2' });
    await user.click(effortButtons[0]);
    await user.click(screen.getByRole('button', { name: /Submit reflection/i }));
    await waitFor(() => expect(postMock).toHaveBeenCalled());
    expect(postMock.mock.calls[0][1]).not.toHaveProperty('team_visibility');
  });

  it('passes program and role query params to template endpoint', async () => {
    renderPage('?program=prog-b&role=kitchen_staff');
    await waitFor(() => expect(getMock).toHaveBeenCalled());
    expect(getMock.mock.calls[0][1].params).toMatchObject({
      program: 'prog-b',
      role: 'kitchen_staff',
    });
  });

  it('renders all six field types', async () => {
    getMock.mockResolvedValue({ data: { ...allFieldsTemplate } });
    renderPage();
    await waitFor(() => expect(screen.getByText('All fields')).toBeInTheDocument());
    expect(screen.getByText('Text field?')).toBeInTheDocument();
    expect(screen.getByText('Textarea field?')).toBeInTheDocument();
    expect(screen.getByText('List field?')).toBeInTheDocument();
    expect(screen.getByText('Ratings?')).toBeInTheDocument();
    expect(screen.getByText('Single choice?')).toBeInTheDocument();
    expect(screen.getByText('Multi choice?')).toBeInTheDocument();
    expect(screen.getByText('Option A')).toBeInTheDocument();
    expect(screen.getByText('Option X')).toBeInTheDocument();
    expect(screen.getByRole('radio')).toBeInTheDocument();
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
  });

  it('renders day-off quick action and submits after toggling off', async () => {
    const user = userEvent.setup();
    getMock.mockResolvedValue({
      data: {
        ...templatePayload,
        schema: {
          fields: [
            {
              key: 'day_off',
              type: 'yes_no',
              required: true,
              prompts: { en: 'Are you on camp today?' },
            },
            { key: 'note', type: 'text', required: true, prompts: { en: 'Note?' } },
          ],
        },
      },
    });
    postMock.mockResolvedValue({ data: { id: 200, answers: { note: 'filled', day_off: 'no' } } });
    renderPage('?program=prog-a&template=9&period_start=2026-06-01&period_end=2026-06-01');
    await waitFor(() => expect(screen.getByTestId('reflect-day-off-toggle')).toBeInTheDocument());

    await user.click(screen.getByTestId('reflect-day-off-toggle'));
    expect(screen.queryByTestId('reflect-input-note')).not.toBeInTheDocument();

    await user.click(screen.getByTestId('reflect-day-off-toggle'));
    expect(screen.getByTestId('reflect-input-note')).toBeInTheDocument();

    await user.type(screen.getByTestId('reflect-input-note'), 'filled');
    await user.click(screen.getByRole('button', { name: /Submit reflection/i }));
    await waitFor(() => expect(postMock).toHaveBeenCalled());
    expect(postMock.mock.calls[0][1].answers).toEqual({ note: 'filled', day_off: 'no' });
  });

  it('save-and-resume: draft persists in localStorage and reloads on mount', async () => {
    const user = userEvent.setup();
    getMock.mockResolvedValue({ data: { ...templatePayload } });

    const { unmount } = renderPage();
    await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());

    await user.type(screen.getByTestId('reflect-period-start'), '2026-07-01');
    await user.type(screen.getByTestId('reflect-period-end'), '2026-07-07');
    const input = screen.getByTestId('reflect-input-note');
    await user.type(input, 'draft content');

    await waitFor(() => {
      const keys = Object.keys(localStorage);
      expect(keys.some((k) => k.startsWith('reflectionDraft:'))).toBe(true);
    });

    const draftKey = Object.keys(localStorage).find((k) => k.startsWith('reflectionDraft:'));
    const stored = JSON.parse(localStorage.getItem(draftKey));
    expect(stored.answers.note).toContain('draft content');

    unmount();

    getMock.mockResolvedValue({ data: { ...templatePayload } });
    renderPage();
    await waitFor(() => expect(screen.getByText('Note?')).toBeInTheDocument());
  });
});
