import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

const mockUseAuth = vi.fn();
vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

// Pin tenant resolution to "unscoped host" so the single-org fixtures below
// resolve regardless of any local VITE_DEV_ORGANIZATION_SLUG.
vi.mock('../../../utils/orgSlug', async (importOriginal) => ({
  ...(await importOriginal()),
  resolveOrganizationSlug: () => null,
}));

import AdminHome from '../AdminHome';

const EXPECTED_TILES = [
  { id: 'performance', href: '/groups/performance', title: 'Group Performance' },
  { id: 'logs', href: '/dashboards/logs', title: 'Bunk Logs' },
  { id: 'reflections', href: '/dashboards/reflections', title: 'Reflections' },
  { id: 'observations', href: '/observations', title: 'Observations' },
  { id: 'maintenance', href: '/maintenance', title: 'Maintenance Queue' },
  { id: 'camper-care-orders', href: '/camper-care/orders', title: 'Camper Care orders' },
  { id: 'coverage', href: '/dashboards/coverage', title: 'Coverage dashboard' },
  { id: 'concerns', href: '/dashboards/concerns', title: 'Concerns inbox' },
  { id: 'authors', href: '/dashboards/authors', title: 'Author attribution' },
];

function adminIn(programTypes) {
  return {
    organizations: [{
      slug: 'org',
      name: 'Org',
      capability: 'admin',
      roles: ['admin'],
      program_types: programTypes,
    }],
    membership_roles: ['admin'],
  };
}

function renderHome(user = adminIn(['summer_camp'])) {
  mockUseAuth.mockReturnValue({ user });
  return render(
    <MemoryRouter>
      <AdminHome />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mockUseAuth.mockReset();
});

describe('AdminHome', () => {
  it('renders nine tiles matching the top admin nav links', () => {
    renderHome();
    expect(screen.getByTestId('admin-home-grid')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Admin Home' })).toBeInTheDocument();
    for (const tile of EXPECTED_TILES) {
      expect(screen.getByTestId(`admin-home-card-${tile.id}`)).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: tile.title })).toBeInTheDocument();
    }
    expect(screen.getAllByRole('link')).toHaveLength(9);
  });

  it('each tile links to the same path as the sidebar nav', () => {
    renderHome();
    for (const { id, href } of EXPECTED_TILES) {
      expect(screen.getByTestId(`admin-home-card-${id}`)).toHaveAttribute('href', href);
    }
  });

  it('swaps camp tiles for the grade reflections tile at a religious school', () => {
    renderHome(adminIn(['religious_school']));

    expect(screen.getByTestId('admin-home-card-grade-reflections')).toHaveAttribute(
      'href', '/admin/reflections',
    );
    expect(screen.getByTestId('admin-home-card-reflections')).toBeInTheDocument();
    for (const id of ['performance', 'logs', 'observations', 'maintenance',
      'camper-care-orders', 'coverage', 'concerns', 'authors']) {
      expect(screen.queryByTestId(`admin-home-card-${id}`)).not.toBeInTheDocument();
    }
  });

  it('keeps every camp tile when the org shape is unknown', () => {
    renderHome({ organizations: [{ slug: 'org', capability: 'admin', roles: ['admin'] }] });
    expect(screen.getAllByRole('link')).toHaveLength(9);
    expect(screen.queryByTestId('admin-home-card-grade-reflections')).not.toBeInTheDocument();
  });
});
