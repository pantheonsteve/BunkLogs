/**
 * Sidebar RBAC spec.
 *
 * Asserts that the navigation links rendered by frontend/src/partials/Sidebar.jsx
 * match the role each user signed in as. Today the sidebar still gates on the
 * legacy User.role string (Counselor, Admin, Unit Head, Camper Care, Leadership);
 * the seed command sets that field to mirror Membership.role so this spec
 * doubles as a regression guard if/when those branches migrate to capability.
 *
 * We assert on hrefs (not link text) because some link labels overlap as
 * substrings — e.g. "Bunk Logs" is the admin-only link to /admin-bunk-logs,
 * but Camper Care has a "My Bunk Logs" button that would falsely match a
 * naive `toContain('Bunk Logs')` check.
 */
import { test, expect, type Page } from '@playwright/test';
import { loginAs, readSidebarText } from './fixtures/auth';

const HREFS = {
  // Self-reflection form, shown to REFLECTION_FORM_ROLES (Counselor, Admin,
  // Unit Head, Camper Care).
  reflect: '/reflect',
  // Counselor "My Reflections" routes to /counselor-dashboard.
  counselorDashboard: '/counselor-dashboard',
  // Admin-only blocks.
  adminBunkLogs: '/admin-bunk-logs',
  adminStaffReflections: '/admin-dashboard',
  adminMemberships: '/admin/memberships',
  // First child of the admin "Tests" submenu — used as a sentinel for the
  // submenu's existence (the submenu trigger is a button, not a link).
  adminTemplates: '/admin/templates',
  ltUnitHealth: '/team/dashboard',
  wellnessDashboard: '/wellness/dashboard',
  orders: '/orders',
};

async function hasLink(page: Page, href: string): Promise<boolean> {
  return (await page.locator(`#sidebar a[href="${href}"]`).count()) > 0;
}

test.describe('Sidebar RBAC', () => {
  test('participant counselor sees self-reflection links, not admin tools', async ({ page }) => {
    await loginAs(page, 'counselor');
    await readSidebarText(page);

    expect(await hasLink(page, HREFS.counselorDashboard)).toBe(true);
    expect(await hasLink(page, HREFS.reflect)).toBe(true);
    expect(await hasLink(page, HREFS.adminMemberships)).toBe(false);
    expect(await hasLink(page, HREFS.adminTemplates)).toBe(false);
    expect(await hasLink(page, HREFS.adminBunkLogs)).toBe(false);
    expect(await hasLink(page, HREFS.ltUnitHealth)).toBe(false);
    expect(await hasLink(page, HREFS.wellnessDashboard)).toBe(false);
  });

  test('unit head sees the participant links (no admin tools)', async ({ page }) => {
    await loginAs(page, 'unit_head');
    await readSidebarText(page);

    expect(await hasLink(page, HREFS.orders)).toBe(true);
    expect(await hasLink(page, HREFS.adminMemberships)).toBe(false);
    expect(await hasLink(page, HREFS.adminTemplates)).toBe(false);
    expect(await hasLink(page, HREFS.adminBunkLogs)).toBe(false);
  });

  test('leadership sees Unit health (LT) link', async ({ page }) => {
    await loginAs(page, 'leadership');
    await readSidebarText(page);

    expect(await hasLink(page, HREFS.ltUnitHealth)).toBe(true);
    expect(await hasLink(page, HREFS.adminMemberships)).toBe(false);
    expect(await hasLink(page, HREFS.adminTemplates)).toBe(false);
  });

  test('camper_care sees Wellness team and not the admin Bunk Logs link', async ({ page }) => {
    await loginAs(page, 'camper_care');
    await readSidebarText(page);

    expect(await hasLink(page, HREFS.wellnessDashboard)).toBe(true);
    expect(await hasLink(page, HREFS.adminMemberships)).toBe(false);
    expect(await hasLink(page, HREFS.adminBunkLogs)).toBe(false);
  });

  test('admin sees Bunk Logs, Staff Reflections, Memberships, and the Tests submenu', async ({
    page,
  }) => {
    await loginAs(page, 'admin');
    await readSidebarText(page);

    expect(await hasLink(page, HREFS.adminBunkLogs)).toBe(true);
    expect(await hasLink(page, HREFS.adminStaffReflections)).toBe(true);
    expect(await hasLink(page, HREFS.adminMemberships)).toBe(true);
    // Tests submenu (collapsed at first render — assert the child link exists
    // in the DOM regardless of the open/closed state of the submenu).
    expect(await hasLink(page, HREFS.adminTemplates)).toBe(true);
    // Admin also has the LT + Wellness shortcuts via the union role list.
    expect(await hasLink(page, HREFS.ltUnitHealth)).toBe(true);
    expect(await hasLink(page, HREFS.wellnessDashboard)).toBe(true);
  });

  test('superuser sees the Tests submenu via is_superuser fallback', async ({ page }) => {
    await loginAs(page, 'superuser');
    await readSidebarText(page);

    // Superuser User.role='Admin' so the admin branches fire; the key
    // assertion is that the is_staff/is_superuser fallback also keeps the
    // Tests submenu mounted.
    expect(await hasLink(page, HREFS.adminTemplates)).toBe(true);
  });

  test('user without a Person/Membership still gets the base Orders link only', async ({
    page,
  }) => {
    await loginAs(page, 'no_membership');
    await readSidebarText(page);

    expect(await hasLink(page, HREFS.orders)).toBe(true);
    expect(await hasLink(page, HREFS.counselorDashboard)).toBe(false);
    expect(await hasLink(page, HREFS.adminMemberships)).toBe(false);
    expect(await hasLink(page, HREFS.adminTemplates)).toBe(false);
    expect(await hasLink(page, HREFS.ltUnitHealth)).toBe(false);
    expect(await hasLink(page, HREFS.wellnessDashboard)).toBe(false);
  });
});
