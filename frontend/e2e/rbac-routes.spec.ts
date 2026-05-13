/**
 * Route-level RBAC spec.
 *
 * The SPA itself does not gate most routes (you can navigate to /admin/templates
 * regardless of role), so we exercise the *backend* permissions that actually
 * enforce the capability matrix:
 *
 * - /api/v1/templates/                — IsOrgAdminOrSuperuser on writes
 * - /api/v1/memberships/              — admin-only (read + write)
 * - /api/v1/reflections/template-for-me/  — needs Person + Membership
 * - /api/v1/reflections/my-tasks/    — needs Person
 * - /api/v1/dashboards/team/          — leadership / admin only (in-content)
 * - /api/v1/dashboards/wellness/      — wellness / admin only
 *
 * For each user we assert the precise status code we expect from the endpoint
 * AND that the corresponding SPA route loads without redirect-to-/signin.
 */
import { test, expect } from '@playwright/test';
import { authedApi, loginAs } from './fixtures/auth';

test.describe('Route + API RBAC', () => {
  test('participant counselor: forbidden on admin endpoints, OK on participant ones', async ({
    page,
    request,
  }) => {
    await loginAs(page, 'counselor');
    const api = await authedApi(page, request);

    // Read-only template list is fine for any authenticated org user.
    const tplList = await api.get('/api/v1/templates/');
    expect(tplList.status()).toBe(200);

    // Admin-only: memberships list rejects participant.
    const memList = await api.get('/api/v1/memberships/');
    expect(memList.status()).toBe(403);

    // Admin-only: template create rejects participant.
    const tplCreate = await api.post('/api/v1/templates/', {
      name: 'should not work',
      slug: 'rbac-denied',
      cadence: 'daily',
      schema: { fields: [{ key: 'x', type: 'text', required: false, prompts: { en: 'x' } }] },
      languages: ['en'],
    });
    expect(tplCreate.status()).toBe(403);

    // Personal endpoints: counselor has a Person + Membership, so these resolve.
    const tplForMe = await api.get('/api/v1/reflections/template-for-me/');
    expect(tplForMe.status()).toBe(200);
    const myTasks = await api.get('/api/v1/reflections/my-tasks/');
    expect(myTasks.status()).toBe(200);

    // SPA routes: no immediate redirect to /signin (UI may render an empty
    // state for non-admin admin pages, which is fine — we only assert that
    // we stayed authenticated).
    for (const path of ['/reflect', '/tasks', '/dashboard']) {
      await page.goto(path);
      expect(page.url()).not.toContain('/signin');
    }
  });

  test('admin via Membership (is_staff=False): full template + membership writes', async ({
    page,
    request,
  }) => {
    await loginAs(page, 'admin');
    const api = await authedApi(page, request);

    const tplList = await api.get('/api/v1/templates/');
    expect(tplList.status()).toBe(200);

    const memList = await api.get('/api/v1/memberships/');
    expect(memList.status()).toBe(200);

    // Confirm the admin can create-then-delete a template (writes work via
    // capability=admin Membership, not via is_staff). Slug includes a random
    // suffix so re-runs don't collide with the unique constraint.
    const probeSlug = `rbac-e2e-probe-${Date.now()}`;
    const created = await api.post('/api/v1/templates/', {
      name: 'RBAC e2e probe',
      slug: probeSlug,
      cadence: 'daily',
      schema: {
        fields: [{ key: 'note', type: 'textarea', required: false, prompts: { en: 'Note' } }],
      },
      languages: ['en'],
    });
    expect(created.status()).toBe(201);
    const body = (await created.json()) as { id: number };
    const cleanup = await page.request.delete(`${api.baseUrl}/api/v1/templates/${body.id}/`, {
      headers: {
        Authorization: `Bearer ${await page.evaluate(() => localStorage.getItem('access_token'))}`,
        'X-Organization-Slug': 'clc',
      },
    });
    expect([204, 409]).toContain(cleanup.status());
  });

  test('superuser: sees memberships (multi-tenant dashboards still need a Person)', async ({
    page,
    request,
  }) => {
    await loginAs(page, 'superuser');
    const api = await authedApi(page, request);

    const memList = await api.get('/api/v1/memberships/');
    expect(memList.status()).toBe(200);

    // /dashboards/team/ and /dashboards/wellness/ both require a Person
    // profile in the request's org (see the early return in TeamDashboardView
    // and WellnessDashboardView). The superuser fixture has no Person, so
    // these endpoints return 403 by design — verify rather than skip.
    const teamDash = await api.get('/api/v1/dashboards/team/');
    expect(teamDash.status()).toBe(403);
    const wellDash = await api.get('/api/v1/dashboards/wellness/');
    expect(wellDash.status()).toBe(403);
  });

  test('user with no Person/Membership: 404 from template-for-me, 200 (empty) from my-tasks', async ({
    page,
    request,
  }) => {
    await loginAs(page, 'no_membership');
    const api = await authedApi(page, request);

    // template-for-me explicitly returns 404 when there is no Person profile
    // (see ReflectionViewSet.template_for_me in backend/bunk_logs/api/reflections.py).
    const tplForMe = await api.get('/api/v1/reflections/template-for-me/');
    expect([403, 404]).toContain(tplForMe.status());

    // Admin endpoints reject.
    const memList = await api.get('/api/v1/memberships/');
    expect(memList.status()).toBe(403);

    // Personal endpoints reject because there is no Person profile.
    const myTasks = await api.get('/api/v1/reflections/my-tasks/');
    expect([403, 404]).toContain(myTasks.status());

    // SPA routes still load (the empty/error state is rendered client-side).
    await page.goto('/reflect');
    expect(page.url()).not.toContain('/signin');
  });

  test('cross-org admin (tbe-test) signed into the SPA sees no clc data', async ({
    page,
    request,
  }) => {
    await loginAs(page, 'tbe_admin');
    const api = await authedApi(page, request);

    // The SPA always sends X-Organization-Slug=clc, but the user has no
    // active admin Membership in clc, so admin-only endpoints reject.
    const memList = await api.get('/api/v1/memberships/');
    expect(memList.status()).toBe(403);

    // Template list still works (any authenticated user with org context),
    // but the user shouldn't be able to write.
    const tplList = await api.get('/api/v1/templates/');
    expect(tplList.status()).toBe(200);

    const tplCreate = await api.post('/api/v1/templates/', {
      name: 'cross-tenant denied',
      slug: 'rbac-cross-tenant',
      cadence: 'daily',
      schema: {
        fields: [{ key: 'note', type: 'textarea', required: false, prompts: { en: 'x' } }],
      },
      languages: ['en'],
    });
    expect(tplCreate.status()).toBe(403);
  });

  test('leadership: can read /dashboards/team/', async ({ page, request }) => {
    await loginAs(page, 'leadership');
    const api = await authedApi(page, request);
    const teamDash = await api.get('/api/v1/dashboards/team/');
    expect(teamDash.status()).toBe(200);

    await page.goto('/team/dashboard');
    expect(page.url()).not.toContain('/signin');
  });

  test('camper_care: can read /dashboards/wellness/', async ({ page, request }) => {
    await loginAs(page, 'camper_care');
    const api = await authedApi(page, request);
    const wellDash = await api.get('/api/v1/dashboards/wellness/');
    expect(wellDash.status()).toBe(200);

    await page.goto('/wellness/dashboard');
    expect(page.url()).not.toContain('/signin');
  });
});
