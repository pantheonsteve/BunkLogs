import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

vi.mock('../../partials/Sidebar', () => ({
  default: () => <aside data-testid="mock-sidebar" />,
}));
vi.mock('../../components/admin/AdminTopBar', () => ({
  default: () => <header data-testid="mock-topbar" />,
}));
vi.mock('../../api/admin', () => ({
  fetchAdminNavBadges: vi.fn().mockResolvedValue(null),
  listAdminPrograms: vi.fn().mockResolvedValue({ results: [] }),
}));

import AdminLayout from '../AdminLayout';

function renderAt(url) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<p data-testid="child-content">hello child</p>} />
          <Route
            path="people"
            element={<p data-testid="child-content">people child</p>}
          />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('AdminLayout (3.28)', () => {
  it('renders Sidebar + topbar + index child via Outlet', () => {
    renderAt('/admin');
    expect(screen.getByTestId('mock-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('mock-topbar')).toBeInTheDocument();
    expect(screen.getByTestId('child-content')).toHaveTextContent('hello child');
  });

  it('renders a nested child route via Outlet', () => {
    renderAt('/admin/people');
    expect(screen.getByTestId('mock-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('child-content')).toHaveTextContent('people child');
  });

  it('exposes the scroll container so children can rely on it', () => {
    renderAt('/admin');
    expect(screen.getByTestId('admin-layout-scroll')).toBeInTheDocument();
  });
});
