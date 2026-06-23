import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../api/admin', () => ({
  getAdminSettings: vi.fn(),
  patchAdminSettings: vi.fn(),
  testAdminMaintenanceNotifications: vi.fn(),
  listAdminPrograms: vi.fn(),
  createAdminProgram: vi.fn(),
  patchAdminProgram: vi.fn(),
  endAdminProgram: vi.fn(),
}));

import {
  getAdminSettings,
  listAdminPrograms,
  endAdminProgram,
  patchAdminSettings,
  testAdminMaintenanceNotifications,
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

function renderSettings(initialEntries = ['/admin/settings']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AdminSettings />
    </MemoryRouter>,
  );
}

describe('AdminSettings — End Program flow (7_13 PR2)', () => {
  it('requires the typed slug + a reason before submitting', async () => {
    endAdminProgram.mockResolvedValue({ summary: { memberships_deactivated: 2, orders_closed: 1, maintenance_tickets_closed: 0, ended_at: '2026-05-22' } });
    renderSettings();
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

describe('AdminSettings — Notifications tab', () => {
  it('loads legacy digest email and saves recipient toggles', async () => {
    getAdminSettings.mockResolvedValue({
      ...SETTINGS,
      settings: {
        ...SETTINGS.settings,
        maintenance_digest_email: 'legacy@camp.test',
        maintenance_digest_time: '06:00',
      },
    });
    patchAdminSettings.mockResolvedValue({
      settings: {
        maintenance_notification_recipients: [
          { email: 'legacy@camp.test', instant: true, digest: true },
        ],
        maintenance_digest_time: '07:00',
      },
    });

    renderSettings();
    await screen.findByTestId('settings-tab-notifications');
    fireEvent.click(screen.getByTestId('settings-tab-notifications'));

    expect(await screen.findByTestId('recipient-row-0')).toBeInTheDocument();
    const emailInput = screen.getByPlaceholderText('facilities@camp.com');
    expect(emailInput).toHaveValue('legacy@camp.test');

    fireEvent.click(screen.getByTestId('recipient-instant-0'));
    fireEvent.change(screen.getByLabelText(/Daily digest send time/i), {
      target: { value: '07:00' },
    });
    fireEvent.click(screen.getByTestId('settings-notifications-save'));

    await waitFor(() =>
      expect(patchAdminSettings).toHaveBeenCalledWith({
        settings: {
          maintenance_notification_recipients: [
            { email: 'legacy@camp.test', instant: true, digest: true },
          ],
          maintenance_digest_time: '07:00',
        },
      }),
    );
  });

  it('sends a test notification email', async () => {
    testAdminMaintenanceNotifications.mockResolvedValue({
      detail: 'Test email sent to legacy@camp.test.',
    });
    getAdminSettings.mockResolvedValue({
      ...SETTINGS,
      settings: {
        ...SETTINGS.settings,
        maintenance_notification_recipients: [
          { email: 'legacy@camp.test', instant: true, digest: true },
        ],
      },
    });

    renderSettings();
    await screen.findByTestId('settings-tab-notifications');
    fireEvent.click(screen.getByTestId('settings-tab-notifications'));
    await screen.findByTestId('settings-notifications-test');
    fireEvent.click(screen.getByTestId('settings-notifications-test'));

    await waitFor(() =>
      expect(testAdminMaintenanceNotifications).toHaveBeenCalledWith('legacy@camp.test'),
    );
    expect(await screen.findByTestId('notifications-test-success')).toHaveTextContent(
      'Test email sent to legacy@camp.test.',
    );
  });
});
