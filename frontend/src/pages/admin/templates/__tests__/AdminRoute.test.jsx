import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom';
import isSuperAdmin from '../../../../utils/auth/isSuperAdmin';
import { hasCapability } from '../../../../utils/auth/capability';

const orgUser = (capability, roles = []) => ({
  organizations: [{ slug: 'clc', capability, roles }],
});

// Minimal re-implementation of AdminRoute that matches the production check in
// frontend/src/routes/guards.jsx -- both share the canonical helpers.
function AdminRoute({ user, loading, isAuthenticated, children }) {
  if (loading) return <div>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/signin" replace />;
  const isAdmin = isSuperAdmin(user) || hasCapability(user, 'admin');
  if (!isAdmin) return <Navigate to="/" replace state={{ toast: 'Admin access required' }} />;
  return children;
}

// Mirrors LeadershipTemplatesRoute in routes/guards.jsx.
function LeadershipTemplatesRoute({ user, loading, isAuthenticated, children }) {
  if (loading) return <div>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/signin" replace />;
  const canAccess =
    isSuperAdmin(user)
    || hasCapability(user, ['program_lead', 'admin']);
  if (!canAccess) return <Navigate to="/" replace state={{ toast: 'Admin access required' }} />;
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

  it('renders children for admin-capability user', () => {
    renderWithRoute(orgUser('admin', ['admin']));
    expect(screen.getByTestId('admin-content')).toBeInTheDocument();
  });

  it('redirects to / for non-admin authenticated user', () => {
    renderWithRoute(orgUser('participant', ['counselor']));
    expect(screen.getByTestId('home')).toBeInTheDocument();
    expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
  });

  it('redirects to /signin for unauthenticated user', () => {
    renderWithRoute(null, false);
    expect(screen.getByTestId('signin')).toBeInTheDocument();
    expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
  });
});

function renderTemplatesRoute(user, authenticated = true) {
  return render(
    <MemoryRouter initialEntries={['/admin/templates']}>
      <Routes>
        <Route
          path="/admin/templates"
          element={
            <LeadershipTemplatesRoute user={user} loading={false} isAuthenticated={authenticated}>
              <div data-testid="templates-content">Templates area</div>
            </LeadershipTemplatesRoute>
          }
        />
        <Route path="/" element={<div data-testid="home">Home</div>} />
        <Route path="/signin" element={<div data-testid="signin">Signin</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LeadershipTemplatesRoute permission gate', () => {
  it('renders children for program_lead capability', () => {
    renderTemplatesRoute(orgUser('program_lead', ['leadership_team']));
    expect(screen.getByTestId('templates-content')).toBeInTheDocument();
  });

  it('renders children for admin-capability user', () => {
    renderTemplatesRoute(orgUser('admin', ['admin']));
    expect(screen.getByTestId('templates-content')).toBeInTheDocument();
  });

  it('renders children for is_staff user', () => {
    renderTemplatesRoute({ is_staff: true });
    expect(screen.getByTestId('templates-content')).toBeInTheDocument();
  });

  it('redirects to / for non-admin, non-leadership authenticated user', () => {
    renderTemplatesRoute(orgUser('participant', ['counselor']));
    expect(screen.getByTestId('home')).toBeInTheDocument();
    expect(screen.queryByTestId('templates-content')).not.toBeInTheDocument();
  });

  it('redirects to /signin for unauthenticated user', () => {
    renderTemplatesRoute(null, false);
    expect(screen.getByTestId('signin')).toBeInTheDocument();
    expect(screen.queryByTestId('templates-content')).not.toBeInTheDocument();
  });
});
