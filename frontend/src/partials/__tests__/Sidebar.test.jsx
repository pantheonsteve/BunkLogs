/**
 * Sidebar capability-aware navigation tests (3.32).
 *
 * Each persona test stubs `useAuth()` with a representative user built
 * from the per-org auth payload (`user.organizations`) and asserts
 * which section headings and link hrefs appear.
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

// Defaults to the pre-existing Crane Lake look; TBE-readiness tests below
// override it to assert the text-only fallback for other orgs.
const mockUseOrgBranding = vi.fn();
vi.mock('../../context/OrgBrandingContext', () => ({
  useOrgBranding: () => mockUseOrgBranding(),
}));

import Sidebar from '../Sidebar';

/** User with the given capability + membership roles in a single org. */
function orgUser(capability, roles, extra = {}) {
  return {
    organizations: [{ slug: 'clc', name: 'Crane Lake', capability, roles }],
    membership_roles: roles,
    ...extra,
  };
}

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
  mockUseOrgBranding.mockReset();
  mockUseOrgBranding.mockReturnValue({
    slug: 'clc',
    displayName: 'Crane Lake',
    productName: 'CLC Bunk Logs',
    isClc: true,
    loading: false,
  });
  // Reset localStorage between tests because Sidebar.jsx persists the
  // expanded/collapsed flag there.
  localStorage.clear();
});

describe('Sidebar — section gating (3.32)', () => {
  it('participant (counselor) sees My work but no Help / Supervise / Admin', () => {
    renderWith(orgUser('participant', ['counselor']));

    expect(screen.queryByRole('link', { name: 'Help' })).not.toBeInTheDocument();
    // Multiple "My work" headings can render (mobile + desktop variants);
    // use getAllByText so it doesn't throw on duplicates.
    expect(screen.getAllByText('My work').length).toBeGreaterThan(0);
    expect(screen.queryByText('Supervise')).not.toBeInTheDocument();
    expect(screen.queryByText('Dashboards')).not.toBeInTheDocument();
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();
    expect(screen.queryByText('Crane Lake legacy')).not.toBeInTheDocument();

    const links = hrefs();
    expect(links).toContain('/counselor');
    expect(links.filter((h) => h === '/counselor')).toHaveLength(2);
    expect(links).not.toContain('/dashboard');
    expect(links).toContain('/tasks');
    expect(links).not.toContain('/reflect');
    expect(links).toContain('/my-reflections');
    expect(links).not.toContain('/dashboards/reflections');
    expect(links).not.toContain('/orders');
    expect(links).not.toContain('/admin');
    expect(links).not.toContain('/admin-bunk-logs');
  });

  it('participant (kitchen) sees My work without Counselor home or reflection forms', () => {
    renderWith(orgUser('participant', ['kitchen_staff']));

    const links = hrefs();
    expect(links).toContain('/kitchen-staff');
    expect(links).not.toContain('/dashboard');
    expect(links).toContain('/tasks');
    expect(links).not.toContain('/counselor');
    expect(links).not.toContain('/reflect');
    expect(links).not.toContain('/my-reflections');
    expect(screen.queryByText('Supervise')).not.toBeInTheDocument();
  });

  it('supervisor (unit_head) sees Supervise but not Dashboards or Admin', () => {
    renderWith(orgUser('supervisor', ['unit_head']));

    expect(screen.getAllByText('Supervise').length).toBeGreaterThan(0);
    expect(screen.queryByText('Dashboards')).not.toBeInTheDocument();
    expect(screen.queryByText('Admin')).not.toBeInTheDocument();

    const links = hrefs();
    expect(links).toContain('/unit-head');
    expect(links.filter((h) => h === '/unit-head')).toHaveLength(2);
    expect(links).not.toContain('/dashboard');
    expect(links).not.toContain('/groups/performance');
    expect(links).not.toContain('/reflect');
    expect(links).not.toContain('/dashboards/logs');
    expect(links).not.toContain('/dashboards/reflections');
    expect(links).toContain('/dashboards/concerns');
    expect(links).toContain('/unit-head/staff-reflections');
    expect(links).not.toContain('/counselor');
  });

  it('supervisor (camper_care) sees Supervise without personal reflection nav', () => {
    renderWith(orgUser('supervisor', ['camper_care']));

    expect(screen.getAllByText('Supervise').length).toBeGreaterThan(0);
    const links = hrefs();
    expect(links).toContain('/camper-care');
    expect(links.filter((h) => h === '/camper-care')).toHaveLength(2);
    expect(links).toContain('/camper-care/flags');
    expect(links).toContain('/camper-care/orders');
    expect(links).not.toContain('/dashboard');
    expect(links).toContain('/groups/performance');
    expect(links).toContain('/dashboards/concerns');
    expect(links).not.toContain('/dashboards/logs');
    expect(links).not.toContain('/tasks');
    expect(links).not.toContain('/reflect');
    expect(links).not.toContain('/my-reflections');
  });

  it('program_lead (leadership) sees Admin-style nav with Templates-only Admin submenu', () => {
    renderWith(orgUser('program_lead', ['leadership_team']), { path: '/leadership-team' });

    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/leadership-team');
    expect(screen.getByRole('link', { name: 'Help' })).toHaveAttribute('href', '/help');
    expect(screen.getAllByText('My work').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Supervise').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Admin').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Templates').length).toBeGreaterThan(0);
    expect(screen.queryByText('Dashboards')).not.toBeInTheDocument();
    expect(screen.queryByText('Leadership Team')).not.toBeInTheDocument();
    expect(screen.queryByText('Crane Lake legacy')).not.toBeInTheDocument();

    const links = hrefs();
    expect(links).toContain('/leadership-team');
    expect(links).toContain('/help');
    expect(links).toContain('/groups/performance');
    expect(links).toContain('/dashboards/logs');
    expect(links).toContain('/dashboards/reflections');
    expect(links).toContain('/observations');
    expect(links).toContain('/maintenance');
    expect(links).toContain('/camper-care/orders');
    expect(links).toContain('/dashboards/coverage');
    expect(links).toContain('/dashboards/concerns');
    expect(links).toContain('/dashboards/authors');
    expect(links).toContain('/admin/templates');
    expect(links).not.toContain('/admin/home');
    expect(links).not.toContain('/admin/dashboard');
    expect(links).not.toContain('/admin/people');
    expect(links).not.toContain('/admin/memberships');
    expect(links).not.toContain('/admin/groups');
    expect(links).not.toContain('/admin/catalog');
    expect(links).not.toContain('/admin/field-keys');
    expect(links).not.toContain('/admin/settings');
    expect(links).not.toContain('/tasks');
    expect(links).not.toContain('/reflect');
    expect(links).not.toContain('/my-reflections');
    expect(links).not.toContain('/dashboards');
    expect(links).not.toContain('/dashboards/wellness');
    expect(links.filter((h) => h === '/dashboards/logs')).toHaveLength(1);
    expect(links.filter((h) => h === '/dashboards/reflections')).toHaveLength(1);
  });

  it('admin sees the curated Admin IA, not the default My work nav', () => {
    renderWith(orgUser('admin', ['admin']), { path: '/admin/home' });

    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/admin/home');
    expect(screen.getByRole('link', { name: 'Help' })).toHaveAttribute('href', '/help');
    expect(screen.getByRole('link', { name: 'Bunk Logs' })).toHaveAttribute(
      'href',
      '/dashboards/logs',
    );
    expect(screen.getAllByRole('link', { name: 'Reflections' }).some(
      (el) => el.getAttribute('href') === '/dashboards/reflections',
    )).toBe(true);
    expect(screen.getAllByText('Admin').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Templates').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Supervise').length).toBeGreaterThan(0);
    expect(screen.queryByText('Dashboards')).not.toBeInTheDocument();
    expect(screen.queryByText('Crane Lake legacy')).not.toBeInTheDocument();

    const links = hrefs();
    expect(links).toContain('/admin/home');
    expect(links).toContain('/help');
    expect(links).not.toContain('/admin/dashboard');
    expect(links).toContain('/dashboards/logs');
    expect(links).toContain('/dashboards/reflections');
    expect(links).toContain('/admin/templates');
    expect(links).toContain('/dashboards/coverage');
    expect(links).toContain('/observations');
    expect(links).toContain('/maintenance');
    expect(links).toContain('/camper-care/orders');
    expect(links).toContain('/groups/performance');
    expect(links).toContain('/dashboards/concerns');
    expect(links).toContain('/dashboards/authors');
    expect(links).not.toContain('/orders');
    expect(links).not.toContain('/admin-bunk-logs');
    expect(links).not.toContain('/admin-dashboard');

    // Personal reflection flows + My tasks fold into the Admin dashboard,
    // not the nav. Leadership Team is the LT's own home, not the Admin IA.
    expect(links).not.toContain('/dashboard');
    expect(links).not.toContain('/tasks');
    expect(links).not.toContain('/reflect');
    expect(links).not.toContain('/my-reflections');
    expect(links).not.toContain('/leadership-team');
    expect(screen.queryByText('Leadership Team')).not.toBeInTheDocument();
  });

  it('super admin via is_staff alone sees Admin even without a role', () => {
    renderWith({ is_staff: true });

    expect(screen.getAllByText('Admin').length).toBeGreaterThan(0);
    expect(screen.queryByText('Dashboards')).not.toBeInTheDocument();
    expect(screen.queryByText('Crane Lake legacy')).not.toBeInTheDocument();
  });
});

describe('Sidebar — maintenance-only nav', () => {
  it('shows only Maintenance Queue for a maintenance member', () => {
    renderWith(orgUser('participant', ['maintenance']));

    const links = hrefs();
    expect(links).toContain('/maintenance');
    expect(links.filter((h) => h === '/maintenance')).toHaveLength(2);
    expect(links).not.toContain('/');
    // Everything else is hidden.
    expect(links).not.toContain('/dashboard');
    expect(links).not.toContain('/tasks');
    expect(links).not.toContain('/counselor');
    expect(links).not.toContain('/reflect');
    expect(links).not.toContain('/orders');
    expect(links).not.toContain('/observations');
    expect(links).not.toContain('/subject-notes');
    expect(screen.queryByText('Supervise')).not.toBeInTheDocument();
  });

  it('keeps the full Admin nav when the user also holds an admin membership', () => {
    renderWith(orgUser('admin', ['maintenance', 'admin']));
    const links = hrefs();
    expect(links).toContain('/admin/home');
    expect(links).not.toContain('/admin/dashboard');
    expect(screen.getAllByText('Admin').length).toBeGreaterThan(0);
  });
});

describe('Sidebar — de-duplication (3.32)', () => {
  it('renders /dashboards/logs and /dashboards/reflections exactly once for admins', () => {
    renderWith(orgUser('admin', ['admin']), { path: '/admin' });
    const links = hrefs();
    const logsMatches = links.filter((h) => h === '/dashboards/logs');
    const reflectionsMatches = links.filter((h) => h === '/dashboards/reflections');
    expect(logsMatches).toHaveLength(1);
    expect(reflectionsMatches).toHaveLength(1);
    expect(links).not.toContain('/dashboards/wellness');
  });

  it('moves Concerns inbox to Supervise only — not duplicated elsewhere', () => {
    renderWith(orgUser('admin', ['admin']));
    const links = hrefs();
    const concerns = links.filter((h) => h === '/dashboards/concerns');
    expect(concerns).toHaveLength(1);
  });

  it('moves Author attribution to Supervise only — not duplicated elsewhere', () => {
    renderWith(orgUser('admin', ['admin']));
    const links = hrefs();
    const authors = links.filter((h) => h === '/dashboards/authors');
    expect(authors).toHaveLength(1);
  });
});

describe('Sidebar — Admin submenu items (3.32)', () => {
  it('includes Field keys under Admin (added in 3.32)', () => {
    renderWith(orgUser('admin', ['admin']), { path: '/admin' });
    expect(hrefs()).toContain('/admin/field-keys');
  });

  it('includes Request catalog under Admin (Step 7_catalog)', () => {
    renderWith(orgUser('admin', ['admin']), { path: '/admin' });
    expect(hrefs()).toContain('/admin/catalog');
  });

  it('still includes People / Memberships / Groups / Templates and top-level Home', () => {
    renderWith(orgUser('admin', ['admin']), { path: '/admin/home' });
    const links = hrefs();
    expect(links).toEqual(
      expect.arrayContaining([
        '/admin/home',
        '/admin/people',
        '/admin/memberships',
        '/admin/groups',
        '/admin/templates',
      ]),
    );
    expect(links).not.toContain('/admin/dashboard');
  });

  it('renders Admin submenu after Supervise with no legacy links', () => {
    renderWith(orgUser('admin', ['admin']), { path: '/admin/home' });
    const links = hrefs();
    const homeIdx = links.indexOf('/admin/home');
    const performanceIdx = links.indexOf('/groups/performance');
    const logsIdx = links.indexOf('/dashboards/logs');
    const reflectionsIdx = links.indexOf('/dashboards/reflections');
    const authorsIdx = links.indexOf('/dashboards/authors');
    const peopleIdx = links.indexOf('/admin/people');
    const membershipsIdx = links.indexOf('/admin/memberships');
    const groupsIdx = links.indexOf('/admin/groups');
    const assignmentsIdx = links.indexOf('/admin/assignments');
    const templatesIdx = links.indexOf('/admin/templates');
    const fieldKeysIdx = links.indexOf('/admin/field-keys');
    const settingsIdx = links.indexOf('/admin/settings');
    expect(homeIdx).toBeGreaterThanOrEqual(0);
    expect(performanceIdx).toBeGreaterThan(homeIdx);
    expect(logsIdx).toBeGreaterThan(performanceIdx);
    expect(reflectionsIdx).toBeGreaterThan(logsIdx);
    expect(authorsIdx).toBeLessThan(peopleIdx);
    expect(membershipsIdx).toBeGreaterThan(peopleIdx);
    expect(groupsIdx).toBeGreaterThan(membershipsIdx);
    expect(assignmentsIdx).toBeGreaterThan(groupsIdx);
    expect(templatesIdx).toBeGreaterThan(assignmentsIdx);
    expect(fieldKeysIdx).toBeGreaterThan(templatesIdx);
    expect(settingsIdx).toBeGreaterThan(fieldKeysIdx);
    expect(links).not.toContain('/admin/dashboard');
    expect(links).not.toContain('/admin-bunk-logs');
    expect(links).not.toContain('/admin-dashboard');
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

describe('Sidebar — org-aware header (TBE Frontend Readiness)', () => {
  it('renders the CLC photo logo when the resolved org is clc', () => {
    renderWith(orgUser('admin', ['admin']));
    expect(screen.getByRole('img')).toHaveAttribute('src', 'logo.jpg');
    expect(screen.queryByText('Temple Beth-El')).not.toBeInTheDocument();
  });

  it('renders a text-only header for a non-clc org, with no logo image', () => {
    mockUseOrgBranding.mockReturnValue({
      slug: 'tbe',
      displayName: 'Temple Beth-El',
      productName: 'BunkLogs',
      isClc: false,
      loading: false,
    });
    renderWith(orgUser('admin', ['admin']));

    expect(screen.getByText('Temple Beth-El')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });
});
