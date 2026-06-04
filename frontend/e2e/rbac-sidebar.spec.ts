/**
 * Sidebar RBAC spec (3.32-aware).
 *
 * Asserts that the navigation links rendered by frontend/src/partials/Sidebar.jsx
 * match the capability each user signs in as. 3.32 introduced section
 * groupings (My work / Supervise / Admin) and switched the gates to `hasCapability` +
 * `isSuperAdmin`. The seed command (`make seed-rbac`) maps
 * Membership.role to User.role so the legacy gate still works while
 * the capability helper is the actual source of truth.
 *
 * Assert on hrefs (not link text) wherever there's ambiguity — some
 * labels collide as substrings ("Bunk Logs" vs the CamperCare in-page
 * tab "My Bunk Logs", for example).
 */
import { test, expect, type Page } from '@playwright/test';
import { loginAs, readSidebarText } from './fixtures/auth';

const HREFS = {
  // My work
  home: '/dashboard',
  tasks: '/tasks',
  reflect: '/reflect',
  myReflections: '/my-reflections',
  counselorHome: '/counselor',
  unitHeadHome: '/unit-head',
  camperCareHome: '/camper-care',
  orders: '/orders',
  // Supervise
  groupsPerformance: '/groups/performance',
  concernsInbox: '/dashboards/concerns',
  // Dashboards (canonical paths — 3.27 renamed the legacy
  // /team/dashboard / /wellness/dashboard aliases away from the
  // sidebar).
  dashboardsHome: '/dashboards',
  dashboardsCoverage: '/dashboards/coverage',
  dashboardsAuthors: '/dashboards/authors',
  dashboardsLogs: '/dashboards/logs',
  dashboardsReflections: '/dashboards/reflections',
  dashboardsWellness: '/dashboards/wellness',
  // Admin
  adminHome: '/admin/home',
  adminDashboard: '/admin/dashboard',
  adminMemberships: '/admin/memberships',
  adminTemplates: '/admin/templates',
  adminGroups: '/admin/groups',
  adminFieldKeys: '/admin/field-keys',
  // Crane Lake legacy (retired from nav; routes kept for bookmarks)
  legacyBunkLogs: '/admin-bunk-logs',
  legacyStaffReflections: '/admin-dashboard',
};

async function hasLink(page: Page, href: string): Promise<boolean> {
  return (await page.locator(`#sidebar a[href="${href}"]`).count()) > 0;
}

async function countLinks(page: Page, href: string): Promise<number> {
  return await page.locator(`#sidebar a[href="${href}"]`).count();
}

test.describe('Sidebar RBAC — capability tiers (3.32)', () => {
  test('counselor (participant): My work only', async ({ page }) => {
    await loginAs(page, 'counselor');
    await readSidebarText(page);

    // My work entries — Home goes straight to the counselor workspace
    expect(await hasLink(page, HREFS.counselorHome)).toBe(true);
    expect(await countLinks(page, HREFS.counselorHome)).toBe(1);
    expect(await hasLink(page, HREFS.home)).toBe(false);
    expect(await hasLink(page, HREFS.tasks)).toBe(true);
    expect(await hasLink(page, HREFS.reflect)).toBe(false);
    expect(await hasLink(page, HREFS.myReflections)).toBe(true);
    expect(await hasLink(page, HREFS.orders)).toBe(false);
    expect(await hasLink(page, HREFS.dashboardsReflections)).toBe(false);

    // No Supervise / Dashboards / Admin / Legacy
    expect(await hasLink(page, HREFS.groupsPerformance)).toBe(false);
    expect(await hasLink(page, HREFS.concernsInbox)).toBe(false);
    expect(await hasLink(page, HREFS.dashboardsHome)).toBe(false);
    expect(await hasLink(page, HREFS.dashboardsLogs)).toBe(false);
    expect(await hasLink(page, HREFS.adminMemberships)).toBe(false);
    expect(await hasLink(page, HREFS.adminFieldKeys)).toBe(false);
    expect(await hasLink(page, HREFS.legacyBunkLogs)).toBe(false);
  });

  test('unit_head (supervisor): Supervise but no Dashboards / Admin', async ({ page }) => {
    await loginAs(page, 'unit_head');
    await readSidebarText(page);

    expect(await hasLink(page, HREFS.unitHeadHome)).toBe(true);
    expect(await countLinks(page, HREFS.unitHeadHome)).toBe(1);
    expect(await hasLink(page, HREFS.home)).toBe(false);
    expect(await hasLink(page, HREFS.orders)).toBe(false);
    expect(await hasLink(page, HREFS.groupsPerformance)).toBe(true);
    expect(await hasLink(page, HREFS.concernsInbox)).toBe(true);

    expect(await hasLink(page, HREFS.dashboardsHome)).toBe(false);
    expect(await hasLink(page, HREFS.adminMemberships)).toBe(false);
    expect(await hasLink(page, HREFS.legacyBunkLogs)).toBe(false);
    expect(await hasLink(page, HREFS.counselorHome)).toBe(false);
  });

  test('camper_care (supervisor): same Supervise gates as unit head + reflection forms', async ({
    page,
  }) => {
    await loginAs(page, 'camper_care');
    await readSidebarText(page);

    expect(await hasLink(page, HREFS.groupsPerformance)).toBe(true);
    expect(await hasLink(page, HREFS.concernsInbox)).toBe(true);
    expect(await hasLink(page, HREFS.reflect)).toBe(true);
    expect(await hasLink(page, HREFS.myReflections)).toBe(true);

    // Camper care does NOT get admin or dashboards.
    expect(await hasLink(page, HREFS.dashboardsHome)).toBe(false);
    expect(await hasLink(page, HREFS.adminMemberships)).toBe(false);
    expect(await hasLink(page, HREFS.legacyBunkLogs)).toBe(false);
  });

  test('leadership (program_lead): Supervise dashboard links but no Admin or Dashboards menu', async ({
    page,
  }) => {
    await loginAs(page, 'leadership');
    await readSidebarText(page);

    expect(await hasLink(page, HREFS.groupsPerformance)).toBe(true);
    expect(await hasLink(page, HREFS.dashboardsLogs)).toBe(true);
    expect(await hasLink(page, HREFS.dashboardsReflections)).toBe(true);
    expect(await hasLink(page, HREFS.dashboardsAuthors)).toBe(true);
    expect(await hasLink(page, HREFS.dashboardsHome)).toBe(false);
    expect(await hasLink(page, HREFS.dashboardsWellness)).toBe(false);

    expect(await hasLink(page, HREFS.adminMemberships)).toBe(false);
    expect(await hasLink(page, HREFS.legacyBunkLogs)).toBe(false);
  });

  test('admin: curated IA without Crane Lake legacy links', async ({ page }) => {
    await loginAs(page, 'admin');
    await readSidebarText(page);

    expect(await hasLink(page, HREFS.groupsPerformance)).toBe(true);
    expect(await hasLink(page, HREFS.adminHome)).toBe(true);
    expect(await hasLink(page, HREFS.adminDashboard)).toBe(true);
    expect(await hasLink(page, HREFS.dashboardsHome)).toBe(false);
    expect(await hasLink(page, HREFS.adminMemberships)).toBe(true);
    expect(await hasLink(page, HREFS.adminTemplates)).toBe(true);
    expect(await hasLink(page, HREFS.adminGroups)).toBe(true);
    expect(await hasLink(page, HREFS.adminFieldKeys)).toBe(true);
    expect(await hasLink(page, HREFS.legacyBunkLogs)).toBe(false);
    expect(await hasLink(page, HREFS.legacyStaffReflections)).toBe(false);
  });

  test('admin: /dashboards/logs and /dashboards/reflections appear exactly once (no duplicates)', async ({
    page,
  }) => {
    await loginAs(page, 'admin');
    await readSidebarText(page);
    expect(await countLinks(page, HREFS.dashboardsLogs)).toBe(1);
    expect(await countLinks(page, HREFS.dashboardsReflections)).toBe(1);
    expect(await hasLink(page, HREFS.dashboardsWellness)).toBe(false);
  });

  test('admin: Concerns inbox lives only in Supervise, not duplicated elsewhere', async ({
    page,
  }) => {
    await loginAs(page, 'admin');
    await readSidebarText(page);
    expect(await countLinks(page, HREFS.concernsInbox)).toBe(1);
  });

  test('superuser (is_staff fallback): admin sections render even without a Membership', async ({
    page,
  }) => {
    await loginAs(page, 'superuser');
    await readSidebarText(page);

    expect(await hasLink(page, HREFS.adminTemplates)).toBe(true);
    expect(await hasLink(page, HREFS.adminFieldKeys)).toBe(true);
    expect(await hasLink(page, HREFS.legacyBunkLogs)).toBe(false);
  });

  test('no_membership: only the everyone-visible items (Home) render', async ({
    page,
  }) => {
    await loginAs(page, 'no_membership');
    await readSidebarText(page);

    expect(await hasLink(page, HREFS.home)).toBe(true);
    expect(await hasLink(page, HREFS.tasks)).toBe(true);
    expect(await hasLink(page, HREFS.orders)).toBe(false);

    expect(await hasLink(page, HREFS.groupsPerformance)).toBe(false);
    expect(await hasLink(page, HREFS.dashboardsHome)).toBe(false);
    expect(await hasLink(page, HREFS.adminMemberships)).toBe(false);
    expect(await hasLink(page, HREFS.legacyBunkLogs)).toBe(false);
    expect(await hasLink(page, HREFS.counselorHome)).toBe(false);
  });
});
