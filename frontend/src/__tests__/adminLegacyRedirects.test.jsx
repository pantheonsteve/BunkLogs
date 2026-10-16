/**
 * Bookmark-preserving redirects for admin routes that moved.
 *
 * Asserted against the real route config rather than a copy of it, so a
 * redirect that gets dropped from `routeConfig.jsx` fails here instead
 * of silently 404-ing someone's bookmark.
 */
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { LegacyAdminTemplateResponsesRedirect } from '../routes/guards';
import { routeConfig } from '../routes/routeConfig';

const adminChildren = routeConfig.find((r) => r.path === '/admin').children;

function redirectTarget(path) {
  const route = adminChildren.find((r) => r.path === path);
  return route?.element?.props?.to;
}

describe('legacy admin redirects', () => {
  it.each([
    ['hub', '/admin/home'],
    ['dashboard', '/admin/home'],
    // Memberships folded into People, Assignments into Groups.
    ['memberships', '/admin/people'],
    ['assignments', '/admin/groups'],
    ['reflections', '/dashboards/reflections?tab=completion'],
  ])('redirects /admin/%s to %s', (path, target) => {
    expect(redirectTarget(path)).toBe(target);
  });

  it('sends /admin/templates/:id/responses to the reflections dashboard with the query', async () => {
    function Landed() {
      const location = useLocation();
      return <div data-testid="responses">{`${location.pathname}${location.search}`}</div>;
    }
    render(
      <MemoryRouter initialEntries={['/admin/templates/5/responses?date=x']}>
        <Routes>
          <Route path="/admin/templates/:id/responses" element={<LegacyAdminTemplateResponsesRedirect />} />
          <Route path="/dashboards/reflections/:templateId" element={<Landed />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByTestId('responses')).toHaveTextContent('/dashboards/reflections/5?date=x');
  });

  it('replaces history so Back does not bounce off the redirect', () => {
    const route = adminChildren.find((r) => r.path === 'assignments');
    expect(route.element.props.replace).toBe(true);
  });
});
