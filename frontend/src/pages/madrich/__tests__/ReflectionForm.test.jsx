/**
 * Madrich reflection form tests — Step 7_14, Stories 62 & 64.
 *
 * Asserts the 3-2-1 contract is enforced client-side (matches the
 * backend schema validator), that the audience disclosure renders,
 * and that no day-off shortcut sneaks into the UI per Story 62 c3.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import MadrichReflectionForm from '../ReflectionForm';

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

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'tbe', user: { id: 7 } }),
}));

// Wysiwyg pulls in heavy quill bits; not used by any field in the
// 3-2-1 template so stub it out.
vi.mock('../../../components/form/Wysiwyg', () => ({
  default: ({ value }) => <textarea data-testid="wysiwyg" defaultValue={value || ''} />,
}));

const TEMPLATE_SCHEMA = {
  fields: [
    {
      key: 'wins',
      type: 'text_list',
      required: true,
      min_items: 3,
      max_items: 3,
      prompts: { en: 'Three wins from this week' },
    },
    {
      key: 'improvements',
      type: 'text_list',
      required: true,
      min_items: 2,
      max_items: 2,
      prompts: { en: 'Two things to improve next week' },
    },
    {
      key: 'question_or_concern',
      type: 'text',
      required: true,
      prompts: { en: 'One question or concern' },
    },
    {
      key: 'ratings',
      type: 'rating_group',
      required: true,
      scale: [1, 4],
      categories: [
        { key: 'reliability_punctuality', labels: { en: 'Reliability' } },
        { key: 'initiative', labels: { en: 'Initiative' } },
        { key: 'communication', labels: { en: 'Communication' } },
        { key: 'problem_solving', labels: { en: 'Problem Solving' } },
        { key: 'interpersonal', labels: { en: 'Interpersonal' } },
      ],
      prompts: { en: 'Rate yourself' },
    },
  ],
};

function renderForm() {
  return render(
    <MemoryRouter initialEntries={["/madrich/reflection/new"]}>
      <Routes>
        <Route path="/madrich/reflection/new" element={<MadrichReflectionForm />} />
        <Route path="/madrich" element={<div data-testid="dashboard-stub" />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  getMock.mockReset();
  postMock.mockReset();
  patchMock.mockReset();
  getMock.mockResolvedValue({ data: { id: 12, schema: TEMPLATE_SCHEMA, language: 'en' } });
});

describe('MadrichReflectionForm', () => {
  it('renders the audience disclosure and no day-off toggle', async () => {
    renderForm();
    await waitFor(() => screen.getByTestId('md-audience-disclosure'));
    expect(screen.getByTestId('md-audience-disclosure')).toHaveTextContent(/Director/);
    expect(screen.getByTestId('md-audience-disclosure')).toHaveTextContent(/Temple Beth-El/);
    expect(screen.queryByText(/Day off/i)).toBeNull();
  });

  it('seeds exactly 3 win inputs and 2 improvement inputs', async () => {
    renderForm();
    await waitFor(() => screen.getByText('Three wins from this week'));
    const winsLabel = screen.getByText('Three wins from this week');
    const winsContainer = winsLabel.closest('div').parentElement;
    expect(within(winsContainer).getAllByRole('textbox')).toHaveLength(3);

    const improvementsLabel = screen.getByText('Two things to improve next week');
    const improvementsContainer = improvementsLabel.closest('div').parentElement;
    expect(within(improvementsContainer).getAllByRole('textbox')).toHaveLength(2);
  });

  it('blocks submission when the 3-2-1 contract is unmet', async () => {
    renderForm();
    await waitFor(() => screen.getByTestId('md-submit-button'));

    // Leave wins/improvements/question empty, only fill 1 rating.
    const ratingButtons = screen.getAllByRole('button', { name: /^[1-4]$/ });
    fireEvent.click(ratingButtons[0]);

    fireEvent.click(screen.getByTestId('md-submit-button'));
    // No POST should fire — client validation catches the missing pieces.
    expect(postMock).not.toHaveBeenCalled();
  });

  it('submits when all 3-2-1 fields and 5 ratings are present', async () => {
    postMock.mockResolvedValue({ data: { id: 555 } });
    renderForm();
    await waitFor(() => screen.getByText('Three wins from this week'));

    const winsContainer = screen.getByText('Three wins from this week').closest('div').parentElement;
    const winInputs = within(winsContainer).getAllByRole('textbox');
    winInputs.forEach((input, i) => fireEvent.change(input, { target: { value: `Win #${i + 1}` } }));

    const improvementsContainer = screen.getByText('Two things to improve next week').closest('div').parentElement;
    const improvementInputs = within(improvementsContainer).getAllByRole('textbox');
    improvementInputs.forEach((input, i) =>
      fireEvent.change(input, { target: { value: `Improve #${i + 1}` } }),
    );

    const questionWrap = screen.getByText('One question or concern').closest('div');
    const questionInput = within(questionWrap).getByRole('textbox');
    fireEvent.change(questionInput, { target: { value: 'How do I run an icebreaker?' } });

    // Pick a rating for every one of the 5 categories.
    ['Reliability', 'Initiative', 'Communication', 'Problem Solving', 'Interpersonal'].forEach(
      (label) => {
        const catLabel = screen.getByText(label);
        const catWrap = catLabel.closest('div');
        const buttons = within(catWrap).getAllByRole('button', { name: /^[1-4]$/ });
        fireEvent.click(buttons[2]);
      },
    );

    fireEvent.click(screen.getByTestId('md-submit-button'));

    await waitFor(() => expect(postMock).toHaveBeenCalledTimes(1));
    const [path, body] = postMock.mock.calls[0];
    expect(path).toBe('/api/v1/madrich/reflection/');
    expect(body.language).toBe('en');
    expect(body.client_submission_id).toEqual(expect.any(String));
    expect(body.answers.wins).toEqual(['Win #1', 'Win #2', 'Win #3']);
    expect(body.answers.improvements).toEqual(['Improve #1', 'Improve #2']);
    expect(body.answers.question_or_concern).toMatch(/icebreaker/);
    expect(Object.keys(body.answers.ratings)).toEqual([
      'reliability_punctuality',
      'initiative',
      'communication',
      'problem_solving',
      'interpersonal',
    ]);

    await waitFor(() => screen.getByTestId('dashboard-stub'));
  });

  it('surfaces backend validation errors inline', async () => {
    postMock.mockRejectedValue({ response: { data: { detail: 'You already submitted this week.' } } });
    renderForm();
    await waitFor(() => screen.getByText('Three wins from this week'));

    const winsContainer = screen.getByText('Three wins from this week').closest('div').parentElement;
    const winInputs = within(winsContainer).getAllByRole('textbox');
    winInputs.forEach((input, i) => fireEvent.change(input, { target: { value: `Win ${i}` } }));
    const improvementsContainer = screen.getByText('Two things to improve next week').closest('div').parentElement;
    const improvementInputs = within(improvementsContainer).getAllByRole('textbox');
    improvementInputs.forEach((input, i) =>
      fireEvent.change(input, { target: { value: `Improve ${i}` } }),
    );
    const questionWrap = screen.getByText('One question or concern').closest('div');
    fireEvent.change(within(questionWrap).getByRole('textbox'), { target: { value: 'q' } });
    ['Reliability', 'Initiative', 'Communication', 'Problem Solving', 'Interpersonal'].forEach(
      (label) => {
        const catWrap = screen.getByText(label).closest('div');
        const buttons = within(catWrap).getAllByRole('button', { name: /^[1-4]$/ });
        fireEvent.click(buttons[0]);
      },
    );

    fireEvent.click(screen.getByTestId('md-submit-button'));
    await waitFor(() => expect(screen.getByTestId('md-submit-error')).toHaveTextContent(/already submitted/));
  });
});
