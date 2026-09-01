import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import ConfirmDialog from '../ConfirmDialog';

describe('ConfirmDialog', () => {
  it('confirms immediately when no typed confirmation is required', async () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        title="Archive Grade 3?"
        confirmLabel="Archive Grade 3"
        onConfirm={onConfirm}
        onClose={() => {}}
      />,
    );

    await userEvent.click(screen.getByTestId('confirm-dialog-confirm'));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('keeps confirm disabled until the required name is typed exactly', async () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        title="Delete program?"
        requireTypedConfirmation="TBE 2026-27"
        onConfirm={onConfirm}
        onClose={() => {}}
      />,
    );

    const confirm = screen.getByTestId('confirm-dialog-confirm');
    expect(confirm).toBeDisabled();

    await userEvent.type(screen.getByTestId('confirm-dialog-typed'), 'TBE 2026');
    expect(confirm).toBeDisabled();

    await userEvent.type(screen.getByTestId('confirm-dialog-typed'), '-27');
    expect(confirm).toBeEnabled();

    await userEvent.click(confirm);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('states consequences and reassurance so the confirmation is proportional', () => {
    render(
      <ConfirmDialog
        title="Archive Madrichim?"
        reassurance="Nothing is deleted. Existing logs stay readable in Reports."
        consequences={['hide it from active lists', 'end current assignments']}
        onConfirm={() => {}}
        onClose={() => {}}
      />,
    );

    expect(screen.getByTestId('confirm-dialog-reassurance')).toHaveTextContent(
      /nothing is deleted/i,
    );
    expect(screen.getByText('hide it from active lists')).toBeInTheDocument();
    expect(screen.getByText('end current assignments')).toBeInTheDocument();
  });

  it('offers the softer alternative when one is supplied', async () => {
    const onAlternative = vi.fn();
    render(
      <ConfirmDialog
        title="Remove 3 students?"
        alternativeLabel="Set end date instead"
        onAlternative={onAlternative}
        onConfirm={() => {}}
        onClose={() => {}}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /set end date instead/i }));
    expect(onAlternative).toHaveBeenCalledTimes(1);
  });

  it('does not dismiss on Escape while a write is in flight', async () => {
    const onClose = vi.fn();
    render(<ConfirmDialog title="Working" busy onConfirm={() => {}} onClose={onClose} />);

    await userEvent.keyboard('{Escape}');
    expect(onClose).not.toHaveBeenCalled();
  });
});
