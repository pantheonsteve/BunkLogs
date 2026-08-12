import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Navigate, Route, Routes } from 'react-router-dom';

/**
 * Bookmark-preserving redirects for the retired AdminHub and Story 54
 * dashboard pages. Mirrors the entries in `routes/routeConfig.jsx`.
 */
function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/home" element={<div data-testid="admin-home" />} />
        <Route path="/admin/hub" element={<Navigate to="/admin/home" replace />} />
        <Route path="/admin/dashboard" element={<Navigate to="/admin/home" replace />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('legacy admin home redirects', () => {
  it('redirects /admin/hub to /admin/home', async () => {
    renderAt('/admin/hub');
    expect(await screen.findByTestId('admin-home')).toBeInTheDocument();
  });

  it('redirects /admin/dashboard to /admin/home', async () => {
    renderAt('/admin/dashboard');
    expect(await screen.findByTestId('admin-home')).toBeInTheDocument();
  });
});
