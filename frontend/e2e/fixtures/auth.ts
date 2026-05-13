import { expect, type APIRequestContext, type Page } from '@playwright/test';
import { type RbacUser, RBAC_USERS, type UserKey } from './users';

const API_BASE = process.env.PLAYWRIGHT_API_BASE_URL ?? 'http://localhost:8000';
const ORG_SLUG = process.env.PLAYWRIGHT_ORG_SLUG ?? 'clc';

/**
 * Sign in via the JWT token endpoint, then bootstrap the SPA at /dashboard so
 * AuthContext picks up the tokens from localStorage. Returns the user record.
 *
 * Mirrors the flow in frontend/src/pages/Signin.jsx (POST /api/auth/token/),
 * but bypasses the form to keep the test fast and resilient against UI churn.
 */
export async function loginAs(page: Page, key: UserKey): Promise<RbacUser> {
  const user = RBAC_USERS[key];

  // Hit the SPA root once so localStorage / origin cookies are scoped correctly.
  await page.goto('/signin');

  const response = await page.request.post(`${API_BASE}/api/auth/token/`, {
    data: { email: user.email, password: user.password },
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok()) {
    throw new Error(
      `Login failed for ${user.email}: ${response.status()} ${await response.text()}. ` +
        'Did you run `make seed-rbac`?',
    );
  }
  const body = (await response.json()) as {
    access: string;
    refresh: string;
    user?: Record<string, unknown>;
  };

  // Mirror what AuthContext.login does on a real password sign-in. We also
  // stash the freshly-minted access token on a window global because the
  // SPA's axios interceptor (frontend/src/api.js) can refresh the token on
  // 401 and rewrite localStorage out from under us — `authedApi` reads from
  // the global so it never observes a half-rotated token.
  await page.evaluate(
    ({ access, refresh, userData }) => {
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      if (userData) {
        localStorage.setItem('user', JSON.stringify(userData));
      }
      (window as unknown as { __RBAC_TEST_TOKEN__?: string }).__RBAC_TEST_TOKEN__ = access;
    },
    { access: body.access, refresh: body.refresh, userData: body.user ?? null },
  );

  await page.goto('/dashboard');
  // The dashboard load may have triggered a refresh that rotated localStorage;
  // re-stamp the window global so authedApi sees the correct token regardless.
  await page.evaluate((access) => {
    (window as unknown as { __RBAC_TEST_TOKEN__?: string }).__RBAC_TEST_TOKEN__ = access;
  }, body.access);
  return user;
}

/** Clear all auth state so the next login starts clean. */
export async function logout(page: Page): Promise<void> {
  await page.evaluate(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    delete (window as unknown as { __RBAC_TEST_TOKEN__?: string }).__RBAC_TEST_TOKEN__;
  });
}

/**
 * Wait briefly for the sidebar to render, then return its text content. Used
 * by sidebar visibility specs to assert which links are present per role.
 */
export async function readSidebarText(page: Page): Promise<string> {
  const sidebar = page.locator('#sidebar');
  await expect(sidebar).toBeVisible();
  return (await sidebar.innerText()).trim();
}

/**
 * Build an authenticated API client mirroring the SPA's axios interceptors:
 * Authorization: Bearer <jwt>, X-Organization-Slug: clc. Read the access
 * token from the page's localStorage so callers don't need to thread it.
 */
export async function authedApi(
  page: Page,
  request: APIRequestContext,
): Promise<{
  get: (path: string) => Promise<ReturnType<APIRequestContext['get']>>;
  post: (
    path: string,
    body?: unknown,
  ) => Promise<ReturnType<APIRequestContext['post']>>;
  baseUrl: string;
}> {
  const token = await page.evaluate(
    () =>
      (window as unknown as { __RBAC_TEST_TOKEN__?: string }).__RBAC_TEST_TOKEN__ ??
      localStorage.getItem('access_token'),
  );
  if (!token) {
    throw new Error('authedApi: page has no access_token; call loginAs first.');
  }
  const headers = {
    Authorization: `Bearer ${token}`,
    'X-Organization-Slug': ORG_SLUG,
    'Content-Type': 'application/json',
  };
  return {
    baseUrl: API_BASE,
    get: (path: string) => request.get(`${API_BASE}${path}`, { headers }),
    post: (path: string, body?: unknown) =>
      request.post(`${API_BASE}${path}`, { headers, data: body ?? {} }),
  };
}
