import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

vi.mock('../../../partials/Header', () => ({ default: () => null }));
vi.mock('../../../partials/Sidebar', () => ({ default: () => null }));

import AdminHub from '../AdminHub';

function renderHub() {
  return render(
    <MemoryRouter initialEntries={['/admin']}>
      <Routes>
        <Route path="/admin" element={<AdminHub />} />
        <Route path="/admin/memberships" element={<div data-testid="memberships">Memberships</div>} />
        <Route path="/admin/templates" element={<div data-testid="templates">Templates</div>} />
        <Route path="/admin/groups" element={<div data-testid="groups">Groups</div>} />
        <Route path="/admin/field-keys" element={<div data-testid="field-keys">Field keys</div>} />
        <Route path="/dashboards" element={<div data-testid="dashboards">Dashboards</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('AdminHub', () => {
  it('renders the five admin cards', () => {
    renderHub();
    expect(screen.getByTestId('admin-hub-card-memberships')).toBeInTheDocument();
    expect(screen.getByTestId('admin-hub-card-templates')).toBeInTheDocument();
    expect(screen.getByTestId('admin-hub-card-groups')).toBeInTheDocument();
    expect(screen.getByTestId('admin-hub-card-dashboards')).toBeInTheDocument();
    expect(screen.getByTestId('admin-hub-card-field-keys')).toBeInTheDocument();
  });

  it('the field-keys card links to /admin/field-keys (no longer deferred)', () => {
    renderHub();
    const card = screen.getByTestId('admin-hub-card-field-keys');
    expect(card.tagName.toLowerCase()).toBe('a');
    expect(card).toHaveAttribute('href', '/admin/field-keys');
    expect(card).not.toHaveAttribute('aria-disabled');
    expect(screen.queryByText('Coming soon')).not.toBeInTheDocument();
  });

  it('linkable cards point at the right routes', () => {
    renderHub();
    expect(screen.getByTestId('admin-hub-card-memberships')).toHaveAttribute('href', '/admin/memberships');
    expect(screen.getByTestId('admin-hub-card-templates')).toHaveAttribute('href', '/admin/templates');
    expect(screen.getByTestId('admin-hub-card-groups')).toHaveAttribute('href', '/admin/groups');
    expect(screen.getByTestId('admin-hub-card-dashboards')).toHaveAttribute('href', '/admin/home');
    expect(screen.getByTestId('admin-hub-card-field-keys')).toHaveAttribute('href', '/admin/field-keys');
  });
});
