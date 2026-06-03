import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

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

function renderHome() {
  return render(
    <MemoryRouter>
      <AdminHome />
    </MemoryRouter>,
  );
}

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
});
