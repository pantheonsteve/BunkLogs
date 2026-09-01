/**
 * Setup owns program CRUD now that Memberships is gone.
 *
 * The thing worth protecting is that deleting a program can't be reached
 * by a stray click: it lives in the row's overflow menu and still demands
 * the typed confirmation.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../../api/admin', async () => {
  const actual = await vi.importActual('../../../../api/admin');
  return { ...actual, listAdminPrograms: vi.fn(), endAdminProgram: vi.fn() };
});

import { listAdminPrograms, endAdminProgram } from '../../../../api/admin';
import AdminSetupPage from '../SetupPage';

const PROGRAMS = [
  { id: 1, name: 'Crane Lake Summer 2026', slug: 'clc-2026', program_type: 'summer_camp', start_date: '2026-06-20', is_active: true },
  { id: 2, name: 'Crane Lake Summer 2025', slug: 'clc-2025', program_type: 'summer_camp', start_date: '2025-06-20', is_active: false },
];

beforeEach(() => {
  vi.clearAllMocks();
  listAdminPrograms.mockResolvedValue({ results: PROGRAMS });
  endAdminProgram.mockResolvedValue({ summary: {} });
});

function renderSetup() {
  return render(<MemoryRouter><AdminSetupPage /></MemoryRouter>);
}

describe('AdminSetupPage', () => {
  it('lists active programs and hides ended ones behind the filter', async () => {
    renderSetup();
    expect(await screen.findByTestId('program-row-1')).toHaveTextContent('Crane Lake Summer 2026');
    expect(screen.queryByTestId('program-row-2')).toBeNull();

    fireEvent.click(screen.getByTestId('program-filter-ended'));
    expect(await screen.findByTestId('program-row-2')).toHaveTextContent('Crane Lake Summer 2025');
  });

  it('keeps deletion in the overflow menu behind typed confirmation', async () => {
    renderSetup();
    await screen.findByTestId('program-row-1');

    expect(screen.queryByTestId('program-delete-1')).toBeNull();
    fireEvent.click(screen.getByTestId('program-actions-1'));
    fireEvent.click(screen.getByTestId('program-delete-1'));

    const modal = await screen.findByTestId('end-program-modal');
    const confirm = within(modal).getByTestId('end-program-confirm');
    expect(confirm).toBeDisabled();

    fireEvent.change(within(modal).getByLabelText(/Type to confirm/), {
      target: { value: 'clc-2026' },
    });
    fireEvent.change(within(modal).getByLabelText(/Reason/), {
      target: { value: 'Season is over.' },
    });
    expect(confirm).not.toBeDisabled();
  });

  it('will not offer to delete a program that already ended', async () => {
    renderSetup();
    await screen.findByTestId('program-row-1');
    fireEvent.click(screen.getByTestId('program-filter-ended'));

    fireEvent.click(await screen.findByTestId('program-actions-2'));
    expect(screen.getByTestId('program-delete-2')).toBeDisabled();
  });
});
