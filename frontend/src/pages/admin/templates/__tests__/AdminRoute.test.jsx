import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import isSuperAdmin from '../../../../utils/auth/isSuperAdmin';

// Minimal re-implementation of AdminRoute that matches the production check in
// frontend/src/Router.jsx -- both share the canonical isSuperAdmin helper.
function AdminRoute({ user, loading, isAuthenticated, children }) {
  if (loading) return <div>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/signin" replace />;
  const isAdmin = isSuperAdmin(user) || user?.role === 'admin';
  if (!isAdmin) return <Navigate to="/" replace state={{ toast: 'Admin access required' }} />;
  return children;
}

function renderWithRoute(user, authenticated = true) {
  return render(
    <MemoryRouter initialEntries={['/admin/templates']}>
      <Routes>
        <Route
          path="/admin/templates"
          element={
            <AdminRoute user={user} loading={false} isAuthenticated={authenticated}>
              <div data-testid="admin-content">Admin area</div>
            </AdminRoute>
          }
        />
        <Route path="/" element={<div data-testid="home">Home</div>} />
        <Route path="/signin" element={<div data-testid="signin">Signin</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('AdminRoute permission gate', () => {
  it('renders children for is_staff user', () => {
    renderWithRoute({ is_staff: true });
    expect(screen.getByTestId('admin-content')).toBeInTheDocument();
  });

  it('renders children for is_superuser', () => {
    renderWithRoute({ is_superuser: true });
    expect(screen.getByTestId('admin-content')).toBeInTheDocument();
  });

  it('renders children for role=admin user', () => {
    renderWithRoute({ role: 'admin' });
    expect(screen.getByTestId('admin-content')).toBeInTheDocument();
  });

  it('redirects to / for non-admin authenticated user', () => {
    renderWithRoute({ role: 'counselor' });
    expect(screen.getByTestId('home')).toBeInTheDocument();
    expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
  });

  it('redirects to /signin for unauthenticated user', () => {
    renderWithRoute(null, false);
    expect(screen.getByTestId('signin')).toBeInTheDocument();
    expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
  });
});
