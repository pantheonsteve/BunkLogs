import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '../../../auth/AuthContext';
import AdminViewingBanner from '../AdminViewingBanner';

describe('AdminViewingBanner', () => {
  it('renders nothing for non-admin viewers', () => {
    useAuth.mockReturnValue({
      user: {
        is_staff: false,
        organizations: [{ slug: 'clc', capability: 'participant', roles: ['counselor'] }],
      },
    });
    const { container } = render(<AdminViewingBanner roleLabel="Counselor" />);
    expect(container.firstChild).toBeNull();
  });

  it('renders for admin-capability members', () => {
    useAuth.mockReturnValue({
      user: {
        organizations: [{ slug: 'clc', capability: 'admin', roles: ['admin'] }],
      },
    });
    render(<AdminViewingBanner roleLabel="Maintenance" />);
    expect(screen.getByTestId('admin-viewing-banner')).toBeInTheDocument();
    expect(screen.getByText(/Maintenance/i)).toBeInTheDocument();
  });

  it('renders for Super Admins (is_staff)', () => {
    useAuth.mockReturnValue({
      user: {
        is_staff: true,
        organizations: [{ slug: 'clc', capability: 'supervisor', roles: ['unit_head'] }],
      },
    });
    render(<AdminViewingBanner roleLabel="Unit Head" />);
    expect(screen.getByTestId('admin-viewing-banner')).toBeInTheDocument();
  });
});
