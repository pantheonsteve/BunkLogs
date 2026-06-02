import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';

/** Mirror of Router.jsx LegacyLtTemplatesRedirect for bookmark preservation. */
function LegacyLtTemplatesRedirect() {
  const location = useLocation();
  const target = location.pathname.replace(/^\/leadership-team\/templates/, '/admin/templates');
  return <Navigate to={`${target}${location.search}${location.hash}`} replace />;
}

describe('template route redirects', () => {
  it('redirects /leadership-team/templates to /admin/templates', async () => {
    render(
      <MemoryRouter initialEntries={['/leadership-team/templates']}>
        <Routes>
          <Route path="/leadership-team/templates/*" element={<LegacyLtTemplatesRedirect />} />
          <Route path="/admin/templates" element={<div data-testid="admin-templates" />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId('admin-templates')).toBeInTheDocument();
  });

  it('redirects nested LT template paths preserving suffix', async () => {
    render(
      <MemoryRouter initialEntries={['/leadership-team/templates/7/responses?tab=aggregate']}>
        <Routes>
          <Route path="/leadership-team/templates/*" element={<LegacyLtTemplatesRedirect />} />
          <Route
            path="/admin/templates/:id/responses"
            element={<div data-testid="admin-responses" />}
          />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId('admin-responses')).toBeInTheDocument();
  });
});
