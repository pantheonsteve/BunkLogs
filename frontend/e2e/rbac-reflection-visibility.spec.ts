/**
 * Reflection submission + cross-user visibility + i18n spec.
 *
 * Covers the visibility paths in
 * backend/bunk_logs/core/permissions/visibility.py:
 *   - Author of a reflection always sees their own.
 *   - WELLNESS_ROLES (health_center / special_diets) see reflections whose
 *     template.role is in that set.
 *   - Counselors do NOT see camper-care reflections (no wellness path, not
 *     the author, not in the camper-care assignment-group hierarchy).
 *
 * Note (3.21): camper_care moved off the wellness shortcut and onto the
 * unit-scoped supervisor capability. The "camper_care sees the wellness
 * reflection that counselor cannot" assertion below now passes via the
 * author path (the seeded camper-care reflection is authored by the
 * camper-care fixture user), not the WELLNESS_ROLES shortcut.
 *
 * Plus the i18n contract in ReflectionViewSet.template_for_me: requesting
 * ?language=es returns Spanish prompts and labels for templates that declare
 * Spanish coverage.
 */
import { test, expect } from '@playwright/test';
import { authedApi, loginAs } from './fixtures/auth';

test.describe('Reflection visibility + i18n', () => {
  test('counselor: template-for-me returns a usable schema and seed reflection is listed', async ({
    page,
    request,
  }) => {
    await loginAs(page, 'counselor');
    const api = await authedApi(page, request);

    // The counselor user has multiple counselor templates active in the org;
    // template-for-me may resolve to any of them. We just assert the contract.
    const tplResp = await api.get('/api/v1/reflections/template-for-me/');
    expect(tplResp.status()).toBe(200);
    const tpl = (await tplResp.json()) as {
      id: number;
      role: string;
      schema: { fields: unknown[] };
      program_slug: string;
    };
    expect(tpl.role).toBe('counselor');
    expect(tpl.program_slug).toBe('summer-2026');
    expect(tpl.schema.fields.length).toBeGreaterThan(0);

    // The seed's counselor self-reflection should appear in the list.
    const list = await api.get('/api/v1/reflections/?program=summer-2026');
    expect(list.status()).toBe(200);
    const body = (await list.json()) as { results?: unknown[] } | unknown[];
    const items = Array.isArray(body) ? body : (body.results ?? []);
    expect(items.length).toBeGreaterThan(0);
  });

  test('kitchen_staff: template-for-me?language=es returns Spanish prompts', async ({
    page,
    request,
  }) => {
    await loginAs(page, 'kitchen');
    const api = await authedApi(page, request);

    const resp = await api.get(
      '/api/v1/reflections/template-for-me/?program=summer-2026&language=es',
    );
    expect(resp.status()).toBe(200);
    const tpl = (await resp.json()) as {
      slug: string;
      schema: {
        fields: Array<{
          key: string;
          type: string;
          prompts?: Record<string, string>;
          scale_labels?: Record<string, string[]>;
          categories?: Array<{ key: string; labels?: Record<string, string> }>;
        }>;
      };
    };
    expect(tpl.slug).toBe('clc-2026-kitchen-daily');

    // Find the textarea field and assert the Spanish prompt is present.
    const textarea = tpl.schema.fields.find((f) => f.type === 'textarea');
    expect(textarea?.prompts?.es).toBeTruthy();
    expect(textarea?.prompts?.en).toBeFalsy();

    // Find the rating_group and assert Spanish scale + category labels.
    const ratingGroup = tpl.schema.fields.find((f) => f.type === 'rating_group');
    expect(ratingGroup?.scale_labels?.es?.length ?? 0).toBeGreaterThan(0);
    expect(ratingGroup?.categories?.[0]?.labels?.es).toBeTruthy();
  });

  test('camper_care sees the wellness reflection that counselor cannot', async ({
    page,
    request,
  }) => {
    // 1. Counselor's view: template filter on the wellness slug returns nothing.
    await loginAs(page, 'counselor');
    let api = await authedApi(page, request);
    let resp = await api.get('/api/v1/reflections/?program=summer-2026');
    expect(resp.status()).toBe(200);
    let body = (await resp.json()) as { results?: unknown[] } | unknown[];
    let items = Array.isArray(body) ? body : (body.results ?? []);
    const counselorWellnessHits = (items as Array<{ template_meta?: { slug?: string } }>).filter(
      (r) => r.template_meta?.slug === 'clc-2026-camper-care-daily',
    );
    expect(counselorWellnessHits).toHaveLength(0);

    // 2. Camper-care's view: same query DOES include the wellness reflection.
    await loginAs(page, 'camper_care');
    api = await authedApi(page, request);
    resp = await api.get('/api/v1/reflections/?program=summer-2026');
    expect(resp.status()).toBe(200);
    body = (await resp.json()) as { results?: unknown[] } | unknown[];
    items = Array.isArray(body) ? body : (body.results ?? []);
    const wellnessHits = (items as Array<{ template_meta?: { slug?: string } }>).filter(
      (r) => r.template_meta?.slug === 'clc-2026-camper-care-daily',
    );
    expect(wellnessHits.length).toBeGreaterThan(0);
  });

  test('unit_head sees descendant-bunk reflections via supervisor coverage', async ({
    page,
    request,
  }) => {
    await loginAs(page, 'unit_head');
    const api = await authedApi(page, request);

    const resp = await api.get('/api/v1/reflections/supervisor-coverage/');
    expect(resp.status()).toBe(200);
    const body = (await resp.json()) as { groups: Array<{ name: string }> };
    // The seed gives this user authorship of the parent unit; the coverage
    // endpoint should list the bunk(s) below it.
    expect(body.groups.length).toBeGreaterThan(0);
  });
});
