import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';

vi.mock('../../../api/admin', () => ({
  getAdminSettings: vi.fn(),
  patchAdminSettings: vi.fn(),
  listAdminPrograms: vi.fn(),
  createAdminProgram: vi.fn(),
  patchAdminProgram: vi.fn(),
  endAdminProgram: vi.fn(),
}));

import {
  getAdminSettings,
  listAdminPrograms,
  endAdminProgram,
} from '../../../api/admin';
import AdminSettings from '../Settings';

const SETTINGS = {
  organization_id: 1,
  name: 'Test Org',
  slug: 'test-org',
  settings: { supported_languages: ['en'], rollover_hour: 6, tag_vocabulary: ['vip'] },
  supported_languages: ['en'],
  rollover_hour: 6,
  tag_vocabulary: ['vip'],
};

const PROGRAM = {
  id: 7,
  name: 'Test Org Summer',
  slug: 'test-summer',
  program_type: 'summer_camp',
  start_date: '2026-06-01',
  end_date: '2026-08-31',
  is_active: true,
};

beforeEach(() => {
  vi.clearAllMocks();
  getAdminSettings.mockResolvedValue(SETTINGS);
  listAdminPrograms.mockResolvedValue({ results: [PROGRAM] });
});

describe('AdminSettings — End Program flow (7_13 PR2)', () => {
  it('requires the typed slug + a reason before submitting', async () => {
    endAdminProgram.mockResolvedValue({ summary: { memberships_deactivated: 2, orders_closed: 1, maintenance_tickets_closed: 0, ended_at: '2026-05-22' } });
    render(<AdminSettings />);
    await screen.findByTestId('settings-tab-programs');
    fireEvent.click(screen.getByTestId('settings-tab-programs'));
    await screen.findByTestId(`program-row-${PROGRAM.id}`);
    fireEvent.click(screen.getByTestId(`program-end-${PROGRAM.id}`));

    expect(await screen.findByTestId('end-program-modal')).toBeInTheDocument();
    const confirmBtn = screen.getByTestId('end-program-confirm');
    expect(confirmBtn).toBeDisabled();

    // Type wrong value -> still disabled.
    const inputs = screen.getAllByRole('textbox');
    fireEvent.change(inputs[0], { target: { value: 'wrong' } });
    fireEvent.change(inputs[1], { target: { value: 'A reason' } });
    expect(confirmBtn).toBeDisabled();

    fireEvent.change(inputs[0], { target: { value: PROGRAM.slug } });
    await waitFor(() => expect(confirmBtn).not.toBeDisabled());

    fireEvent.click(confirmBtn);
    await waitFor(() =>
      expect(endAdminProgram).toHaveBeenCalledWith(PROGRAM.id, 'A reason'),
    );
    expect(await screen.findByTestId('end-program-summary')).toBeInTheDocument();
  });
});
