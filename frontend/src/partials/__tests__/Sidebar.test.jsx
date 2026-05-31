/**
 * Sidebar capability-aware navigation tests (3.32).
 *
 * Each persona test stubs `useAuth()` with a representative user
 * (legacy User.role for now; capability.js maps role -> capability)
 * and asserts which section headings and link hrefs appear.
 *
 * We assert on hrefs rather than link text where possible so a
 * labels rewrite doesn't silently break coverage. Section headings
 * are asserted via `getByText` against the uppercase heading string.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Stub the logo import so the test runner doesn't try to decode JPEG.
vi.mock('../../../src/images/clc-logo.jpeg', () => ({ default: 'logo.jpg' }));

// Each test sets the mock return value before rendering.
const mockUseAuth = vi.fn();
vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

import Sidebar from '../Sidebar';

function renderWith(user, { path = '/dashboard' } = {}) {
  mockUseAuth.mockReturnValue({ user });
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Sidebar sidebarOpen={true} setSidebarOpen={() => {}} />
    </MemoryRouter>,
  );
}

function hrefs() {
  return screen
    .getAllByRole('link')
    .map((a) => a.getAttribute('href'))
    .filter(Boolean);
}

beforeEach(() => {
  mockUseAuth.mockReset();
  // Reset localStorage between tests because Sidebar.jsx persists the
  // expanded/collapsed flag there.
  localStorage.clear();
});

describe('Sidebar — section gating (3.32)', () => {
  it('participant (counselor) sees My work but no Supervise / Dashboards / Admin / Legacy', () => {
    renderWith({ role: 'Counselor' });

    // Multiple "My work" headings can render (mobile + desktop variants);
    // use getAllByText so it doesn't throw on duplicates.
    expect(screen.getAllByText('My work').length).toBeGreaterThan(0);
    expect(screen.queryByText('Supervise')).not.toBeInTheDocument();
    expect(screen.queryByText('Dashboards')).not.toBeInTheDocument();
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
    expect(screen.queryByText('Crane Lake legacy')).not.toBeInTheDocument();

    const links = hrefs();
    expect(links).toContain('/dashboard');
    expect(links).toContain('/tasks');
    expect(links).toContain('/counselor');
    expect(links).toContain('/reflect');
    expect(links).toContain('/my-reflections');
    expect(links).toContain('/orders');
    expect(links).not.toContain('/admin');
    expect(links).not.toContain('/admin-bunk-logs');
  });

  it('participant (kitchen) sees My work without Counselor home or reflection forms', () => {
    renderWith({ role: 'Kitchen Staff' });

    const links = hrefs();
    expect(links).toContain('/dashboard');
    expect(links).toContain('/tasks');
    expect(links).not.toContain('/counselor');
    expect(links).not.toContain('/reflect');
    expect(links).not.toContain('/my-reflections');
    expect(screen.queryByText('Supervise')).not.toBeInTheDocument();
  });

  it('supervisor (unit_head) sees Supervise but not Dashboards or Admin', () => {
    renderWith({ role: 'Unit Head' });

    expect(screen.getAllByText('Supervise').length).toBeGreaterThan(0);
    expect(screen.queryByText('Dashboards')).not.toBeInTheDocument();
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();

    const links = hrefs();
    expect(links).toContain('/supervisor/coverage');
    expect(links).toContain('/dashboards/concerns');
    // Supervisors don't get the role-specific Counselor-home link.
    expect(links).not.toContain('/counselor');
  });

  it('supervisor (camper_care) sees Supervise and reflection forms', () => {
    renderWith({ role: 'Camper Care' });

    expect(screen.getAllByText('Supervise').length).toBeGreaterThan(0);
    const links = hrefs();
    expect(links).toContain('/supervisor/coverage');
    expect(links).toContain('/dashboards/concerns');
    expect(links).toContain('/reflect');
    expect(links).toContain('/my-reflections');
  });

  it('program_lead (leadership) sees Dashboards and Supervise but not Admin', () => {
    renderWith({ role: 'Leadership' });

    expect(screen.getAllByText('Dashboards').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Supervise').length).toBeGreaterThan(0);
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
    expect(screen.queryByText('Crane Lake legacy')).not.toBeInTheDocument();
  });

  it('admin sees every section including Crane Lake legacy', () => {
    renderWith({ role: 'Admin' });

    expect(screen.getAllByText('My work').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Supervise').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Dashboards').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Admin').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Crane Lake legacy').length).toBeGreaterThan(0);
  });

  it('super admin via is_staff alone sees Admin + Dashboards even without a role', () => {
    renderWith({ is_staff: true });

    expect(screen.getAllByText('Admin').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Dashboards').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Crane Lake legacy').length).toBeGreaterThan(0);
  });
});

describe('Sidebar — maintenance-only nav', () => {
  it('shows only Maintenance Queue + Observations for a maintenance member', () => {
    renderWith({ role: 'Counselor', membership_roles: ['maintenance'] });

    const links = hrefs();
    expect(links).toContain('/maintenance');
    expect(links).toContain('/observations');
    // Everything else is hidden.
    expect(links).not.toContain('/dashboard');
    expect(links).not.toContain('/tasks');
    expect(links).not.toContain('/counselor');
    expect(links).not.toContain('/reflect');
    expect(links).not.toContain('/orders');
    expect(links).not.toContain('/subject-notes');
    expect(screen.queryByText('Supervise')).not.toBeInTheDocument();
  });

  it('orders Maintenance Queue before Observations', () => {
    renderWith({ role: 'Counselor', membership_roles: ['maintenance'] });
    const appLinks = hrefs().filter((h) => h === '/maintenance' || h === '/observations');
    expect(appLinks[0]).toBe('/maintenance');
    expect(appLinks[1]).toBe('/observations');
  });

  it('keeps full nav when the user also holds an admin membership', () => {
    renderWith({ role: 'Admin', membership_roles: ['maintenance', 'admin'] });
    const links = hrefs();
    expect(links).toContain('/dashboard');
    expect(screen.getAllByText('Admin').length).toBeGreaterThan(0);
  });
});

describe('Sidebar — de-duplication of Wellness / Unit head dashboard (3.32)', () => {
  it('renders /dashboards/team and /dashboards/wellness exactly once for admins', () => {
    renderWith({ role: 'Admin' }, { path: '/admin' });
    // SidebarLinkGroup mounts collapsed by default but keeps the
    // children in the DOM, so we can still query the hrefs.
    const links = hrefs();
    const teamMatches = links.filter((h) => h === '/dashboards/team');
    const wellnessMatches = links.filter((h) => h === '/dashboards/wellness');
    expect(teamMatches).toHaveLength(1);
    expect(wellnessMatches).toHaveLength(1);
  });

  it('moves Concerns inbox to Supervise only — not duplicated under Dashboards', () => {
    renderWith({ role: 'Admin' });
    const links = hrefs();
    const concerns = links.filter((h) => h === '/dashboards/concerns');
    expect(concerns).toHaveLength(1);
  });
});

describe('Sidebar — Admin submenu items (3.32)', () => {
  it('includes Field keys under Admin (added in 3.32)', () => {
    renderWith({ role: 'Admin' }, { path: '/admin' });
    expect(hrefs()).toContain('/admin/field-keys');
  });

  it('still includes Memberships / Templates / Groups / Admin home', () => {
    renderWith({ role: 'Admin' }, { path: '/admin' });
    const links = hrefs();
    expect(links).toEqual(
      expect.arrayContaining([
        '/admin',
        '/admin/memberships',
        '/admin/templates',
        '/admin/groups',
      ]),
    );
  });
});

describe('Sidebar — Crane Lake legacy section (3.32)', () => {
  it('keeps /admin-bunk-logs and /admin-dashboard reachable for admins', () => {
    renderWith({ role: 'Admin' });
    const links = hrefs();
    expect(links).toContain('/admin-bunk-logs');
    expect(links).toContain('/admin-dashboard');
  });

  it('does not render the legacy section for non-admins (counselor)', () => {
    renderWith({ role: 'Counselor' });
    const links = hrefs();
    expect(links).not.toContain('/admin-bunk-logs');
    expect(links).not.toContain('/admin-dashboard');
    expect(screen.queryByText('Crane Lake legacy')).not.toBeInTheDocument();
  });

  it('does not render the legacy section for supervisors', () => {
    renderWith({ role: 'Unit Head' });
    expect(screen.queryByText('Crane Lake legacy')).not.toBeInTheDocument();
  });
});

describe('Sidebar — unauthenticated chrome (3.32)', () => {
  it('renders the logo but no link sections when user is null', () => {
    renderWith(null);
    // Logo link to "/" should always render.
    const links = hrefs();
    expect(links).toContain('/');
    // No app sections.
    expect(screen.queryByText('My work')).not.toBeInTheDocument();
    expect(screen.queryByText('Supervise')).not.toBeInTheDocument();
    expect(screen.queryByText('Dashboards')).not.toBeInTheDocument();
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
  });
});
