import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ReflectionField from '../ReflectionField';

function renderField(field, answer, onChange = vi.fn(), opts = {}) {
  return render(
    <ReflectionField
      field={field}
      language="en"
      answer={answer}
      onChange={onChange}
      {...opts}
    />,
  );
}

describe('ReflectionField', () => {
  it('renders text field with prompt and input', () => {
    renderField({ key: 'note', type: 'text', prompts: { en: 'Your note' } }, '');
    expect(screen.getByText('Your note')).toBeInTheDocument();
    expect(screen.getByTestId('reflect-input-note')).toBeInTheDocument();
  });

  it('calls onChange for text input', async () => {
    const onChange = vi.fn();
    renderField({ key: 'note', type: 'text', prompts: { en: 'Note' } }, '', onChange);
    await userEvent.type(screen.getByTestId('reflect-input-note'), 'hello');
    expect(onChange).toHaveBeenCalled();
  });

  it('renders textarea as a Wysiwyg editor wrapper', () => {
    renderField(
      { key: 'bio', type: 'textarea', prompts: { en: 'Bio' }, max_length: 200 },
      'hello',
    );
    expect(screen.getByText('Bio')).toBeInTheDocument();
    expect(screen.getByTestId('reflect-input-bio')).toBeInTheDocument();
    expect(screen.getByTestId('mock-wysiwyg')).toBeInTheDocument();
  });

  it('renders text_list with add/remove buttons', () => {
    renderField(
      { key: 'wins', type: 'text_list', prompts: { en: 'Wins' }, min_items: 1, max_items: 3 },
      ['win 1'],
    );
    expect(screen.getByText('+ Add line')).toBeInTheDocument();
  });

  it('renders single_choice as radio buttons', () => {
    renderField(
      {
        key: 'mood',
        type: 'single_choice',
        prompts: { en: 'Mood?' },
        options: [
          { key: 'good', labels: { en: 'Good' } },
          { key: 'bad', labels: { en: 'Bad' } },
        ],
      },
      '',
    );
    expect(screen.getByText('Good')).toBeInTheDocument();
    expect(screen.getByText('Bad')).toBeInTheDocument();
    expect(screen.getAllByRole('radio').length).toBe(2);
  });

  it('single_choice uses legacy option.value when key is absent', async () => {
    const onChange = vi.fn();
    renderField(
      {
        key: 'flag',
        type: 'single_choice',
        prompts: { en: 'Flag?' },
        options: [
          { value: 'no', labels: { en: 'No' } },
          { value: 'yes', labels: { en: 'Yes' } },
        ],
      },
      '',
      onChange,
    );
    const radios = screen.getAllByRole('radio');
    await userEvent.click(radios[1]);
    expect(onChange).toHaveBeenCalledWith('yes');
  });

  it('renders multiple_choice as checkboxes', () => {
    renderField(
      {
        key: 'topics',
        type: 'multiple_choice',
        prompts: { en: 'Topics?' },
        options: [
          { key: 'a', labels: { en: 'Alpha' } },
          { key: 'b', labels: { en: 'Beta' } },
        ],
      },
      [],
    );
    expect(screen.getAllByRole('checkbox').length).toBe(2);
  });

  it('renders yes_no as a styled checkbox with the prompt as its label', () => {
    renderField({ key: 'ok', type: 'yes_no', prompts: { en: 'OK?' } }, null);
    const cb = screen.getByTestId('reflect-input-ok');
    expect(cb).toHaveAttribute('type', 'checkbox');
    expect(cb).not.toBeChecked();
    expect(screen.getByLabelText(/OK\?/i)).toBe(cb);
  });

  it('yes_no checkbox toggles the answer between yes and no', async () => {
    const onChange = vi.fn();
    renderField({ key: 'ok', type: 'yes_no', prompts: { en: 'OK?' } }, 'no', onChange);
    await userEvent.click(screen.getByTestId('reflect-input-ok'));
    expect(onChange).toHaveBeenLastCalledWith('yes');
  });

  it('yes_no readonly view shows a faux checkbox without an input', () => {
    renderField(
      { key: 'ok', type: 'yes_no', prompts: { en: 'OK?' } },
      'yes',
      vi.fn(),
      { readonly: true },
    );
    const view = screen.getByTestId('reflect-input-ok');
    expect(view.tagName).toBe('DIV');
    expect(view.className).toMatch(/bg-blue-600/);
  });

  it('renders rating_group with category buttons', () => {
    renderField(
      {
        key: 'r',
        type: 'rating_group',
        scale_labels: { en: ['Low', 'Mid', 'High'] },
        categories: [{ key: 'effort', labels: { en: 'Effort' } }],
      },
      {},
    );
    expect(screen.getByText('Effort')).toBeInTheDocument();
    expect(screen.getByText('Low')).toBeInTheDocument();
    expect(screen.getByText('Mid')).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('renders single_rating as a row of buttons', () => {
    renderField(
      {
        key: 'sr',
        type: 'single_rating',
        prompts: { en: 'Overall?' },
        scale_labels: { en: ['1', '2', '3', '4', '5'] },
      },
      null,
    );
    expect(screen.getByText('Overall?')).toBeInTheDocument();
    expect(screen.getAllByRole('button').length).toBe(5);
  });

  it('uses BunkLog traffic-light styling for a 1–5 single_rating', () => {
    renderField(
      {
        key: 'sr',
        type: 'single_rating',
        prompts: { en: 'Overall?' },
        scale: [1, 5],
      },
      3,
    );
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBe(5);
    expect(buttons[2].className).toContain('bg-[#e5e825]');
    expect(buttons[2].className).toContain('flex-1');
    expect(screen.getByText('Poor')).toBeInTheDocument();
    expect(screen.getByText('Excellent')).toBeInTheDocument();
  });

  it('renders an info tooltip when field.hint is provided', () => {
    renderField(
      {
        key: 'note',
        type: 'text',
        prompts: { en: 'Note' },
        hint: { en: 'Write at least one sentence.' },
      },
      '',
    );
    expect(screen.getByRole('button', { name: /info/i })).toBeInTheDocument();
  });

  it('renders section_header as heading without answer input', () => {
    renderField({ key: 'sec', type: 'section_header', prompts: { en: 'My Section' } }, undefined);
    expect(screen.getByRole('heading', { name: 'My Section' })).toBeInTheDocument();
  });

  it('renders instructions as styled text block', () => {
    renderField({ key: 'inst', type: 'instructions', prompts: { en: 'Read this.' } }, undefined);
    expect(screen.getByText('Read this.')).toBeInTheDocument();
  });

  it('renders date field', () => {
    renderField({ key: 'dt', type: 'date', prompts: { en: 'Date?' } }, '');
    expect(screen.getByTestId('reflect-input-dt')).toHaveAttribute('type', 'date');
  });

  it('renders number field', () => {
    renderField({ key: 'num', type: 'number', prompts: { en: 'Count?' } }, '');
    expect(screen.getByTestId('reflect-input-num')).toHaveAttribute('type', 'number');
  });

  it('disables inputs when readonly=true', () => {
    renderField(
      { key: 'note', type: 'text', prompts: { en: 'Note' } },
      '',
      vi.fn(),
      { readonly: true },
    );
    expect(screen.getByTestId('reflect-input-note')).toBeDisabled();
  });

  it('shows error message below field', () => {
    renderField(
      { key: 'note', type: 'text', prompts: { en: 'Note' } },
      '',
      vi.fn(),
      { error: 'This field is required.' },
    );
    expect(screen.getByText('This field is required.')).toBeInTheDocument();
  });

  it('uses fallback language when primary language prompt missing', () => {
    renderField(
      { key: 'note', type: 'text', prompts: { es: 'Nota' } },
      '',
      vi.fn(),
      { language: 'en' },
    );
    // Falls back to first available language value
    expect(screen.getByText('Nota')).toBeInTheDocument();
  });
});
