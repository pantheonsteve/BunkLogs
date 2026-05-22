import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '../../../auth/AuthContext';
import AdminViewingBanner from '../AdminViewingBanner';

describe('AdminViewingBanner', () => {
  it('renders nothing for non-admin viewers', () => {
    useAuth.mockReturnValue({ user: { role: 'counselor', is_staff: false } });
    const { container } = render(<AdminViewingBanner roleLabel="Counselor" />);
    expect(container.firstChild).toBeNull();
  });

  it('renders for the legacy admin role', () => {
    useAuth.mockReturnValue({ user: { role: 'Admin' } });
    render(<AdminViewingBanner roleLabel="Maintenance" />);
    expect(screen.getByTestId('admin-viewing-banner')).toBeInTheDocument();
    expect(screen.getByText(/Maintenance/i)).toBeInTheDocument();
  });

  it('renders for Super Admins (is_staff)', () => {
    useAuth.mockReturnValue({ user: { role: 'unit_head', is_staff: true } });
    render(<AdminViewingBanner roleLabel="Unit Head" />);
    expect(screen.getByTestId('admin-viewing-banner')).toBeInTheDocument();
  });
});
