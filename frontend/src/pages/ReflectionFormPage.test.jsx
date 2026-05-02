import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import ReflectionFormPage from './ReflectionFormPage';

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

function renderPage(search = '') {
  return render(
    <MemoryRouter initialEntries={[`/reflect${search}`]}>
      <Routes>
        <Route path="/reflect" element={<ReflectionFormPage />} />
        <Route path="/reflect/summary" element={<div data-testid="summary">Summary</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ReflectionFormPage', () => {
  beforeEach(() => {
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

  it('passes program and role query params to template endpoint', async () => {
    renderPage('?program=prog-b&role=kitchen_staff');
    await waitFor(() => expect(getMock).toHaveBeenCalled());
    expect(getMock.mock.calls[0][1].params).toMatchObject({
      program: 'prog-b',
      role: 'kitchen_staff',
    });
  });
});
