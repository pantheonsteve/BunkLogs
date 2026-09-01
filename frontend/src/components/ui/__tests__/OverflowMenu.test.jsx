import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import OverflowMenu, { OverflowMenuItem } from '../OverflowMenu';

function renderMenu(onArchive = vi.fn()) {
  render(
    <OverflowMenu>
      <OverflowMenuItem>Rename…</OverflowMenuItem>
      <OverflowMenuItem danger onClick={onArchive}>
        Archive class…
      </OverflowMenuItem>
    </OverflowMenu>,
  );
  return onArchive;
}

describe('OverflowMenu', () => {
  it('keeps destructive actions out of sight until opened', async () => {
    renderMenu();
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();

    await userEvent.click(screen.getByTestId('overflow-menu-trigger'));
    expect(screen.getByRole('menu')).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /archive class/i })).toBeInTheDocument();
  });

  it('fires the item action and closes', async () => {
    const onArchive = renderMenu();
    await userEvent.click(screen.getByTestId('overflow-menu-trigger'));
    await userEvent.click(screen.getByRole('menuitem', { name: /archive class/i }));

    expect(onArchive).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  it('closes on Escape', async () => {
    renderMenu();
    await userEvent.click(screen.getByTestId('overflow-menu-trigger'));
    await userEvent.keyboard('{Escape}');
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });
});
