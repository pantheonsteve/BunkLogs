import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../api/admin', () => ({
  fetchAdminDashboard: vi.fn(),
}));

import { fetchAdminDashboard } from '../../../api/admin';
import AdminDashboard from '../Dashboard';

beforeEach(() => {
  fetchAdminDashboard.mockReset();
});

const SAMPLE_PAYLOAD = {
  today: '2026-07-15',
  org: {
    id: 1,
    name: 'Acme Camp',
    slug: 'acme',
    active_programs: [
      { id: 11, name: 'Acme Summer 2026', program_type: 'summer_camp', start_date: '2026-06-15', end_date: '2026-08-20' },
    ],
  },
  org_snapshot: {
    active_people: 87,
    memberships_by_role: [
      { role: 'counselor', count: 32 },
      { role: 'camper', count: 50 },
    ],
    open_camper_care_orders: 4,
    open_maintenance_tickets: 2,
    active_flags: 1,
  },
  attention_required: [
    { key: 'stale_maintenance_tickets', label: 'Stale Maintenance tickets', count: 3, threshold_days: 3, deep_link: '/admin/operations/maintenance?filter=stale' },
    { key: 'stale_camper_care_orders', label: 'Stale Camper Care orders', count: 0, threshold_days: 3, deep_link: '/admin/operations/orders?filter=stale' },
    { key: 'unresolved_flags', label: 'Unresolved Camper Care flags', count: 2, threshold_days: 7, deep_link: '/admin/operations/flags?filter=stale' },
    { key: 'pending_template_review', label: 'Pending template review', count: 1, threshold_days: 14, deep_link: '/admin/templates?filter=pending_review' },
    { key: 'digest_delivery_failures', label: 'Digest delivery failures', count: 0, threshold_days: 3, deep_link: '/admin/settings?tab=notifications' },
    { key: 'translation_pipeline_failures', label: 'Translation pipeline failures', count: 0, threshold_days: 1, deep_link: '/admin/operations/translations' },
  ],
  recent_activity: [
    {
      id: 'ev-1', event_type: 'state_changed', content_type: 'order',
      content_id: 'abc', created_at: '2026-07-15T11:00:00Z',
      actor: 'Ada Min', is_admin_override: false,
      deep_link: '/admin/operations/orders/abc',
      summary: 'Order: new -> in_progress',
    },
  ],
};

function renderDashboard() {
  return render(
    <MemoryRouter>
      <AdminDashboard />
    </MemoryRouter>,
  );
}

describe('Admin Dashboard (Story 54)', () => {
  it('renders snapshot, attention, and activity sections', async () => {
    fetchAdminDashboard.mockResolvedValue(SAMPLE_PAYLOAD);
    renderDashboard();
    await waitFor(() => expect(fetchAdminDashboard).toHaveBeenCalled());
    expect(await screen.findByTestId('admin-snapshot')).toBeInTheDocument();
    expect(screen.getByTestId('admin-attention')).toBeInTheDocument();
    expect(screen.getByTestId('admin-activity')).toBeInTheDocument();
    expect(screen.getByText('Acme Camp')).toBeInTheDocument();
  });

  it('shows all six attention cards', async () => {
    fetchAdminDashboard.mockResolvedValue(SAMPLE_PAYLOAD);
    renderDashboard();
    for (const key of [
      'stale_maintenance_tickets',
      'stale_camper_care_orders',
      'unresolved_flags',
      'pending_template_review',
      'digest_delivery_failures',
      'translation_pipeline_failures',
    ]) {
      expect(await screen.findByTestId(`admin-attention-${key}`)).toBeInTheDocument();
    }
  });

  it('surfaces a retry button on error', async () => {
    fetchAdminDashboard.mockRejectedValue(new Error('boom'));
    renderDashboard();
    expect(await screen.findByTestId('admin-dashboard-error')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });
});
