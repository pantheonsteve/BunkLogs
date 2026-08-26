/**
 * Org-aware branding (TBE Frontend Readiness).
 *
 * Fetches the current tenant's display name once on app bootstrap so
 * sign-in/sign-up/password-reset pages and the app shell can show the
 * right org without each page re-fetching. Mounted above `AuthProvider`
 * in App.jsx since the auth pages render before login resolves.
 *
 * Initial state is derived synchronously from the SPA hostname (or dev
 * org override) so non-CLC tenants never flash bundled Crane Lake assets
 * while the branding API request is in flight.
 *
 * Crane Lake safety: `isClc` for the `clc` org (and unresolved hosts) is
 * deliberately NOT sourced from the backend `branding` payload -- it's the
 * literal pre-existing copy. Backend-sourced text only drives *other* orgs
 * (e.g. `tbe`), which have no legacy hardcoded copy to preserve.
 *
 * Uploaded logo/hero URLs from the API take precedence over bundled CLC
 * assets when present (admin can override CLC images without a deploy).
 *
 * The same payload carries the tenant's `terminology` (see
 * `utils/terminology.js`), consumed through `useTerm()`. Unlike display
 * name, terminology defaults are shared by every org including CLC, so
 * they hydrate from the API for all tenants.
 */
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { fetchOrganizationBranding } from '../api/organization';
import { resolveOrganizationSlug } from '../utils/orgSlug';
import { DEFAULT_TERMS, normalizeTerminology, resolveTerm } from '../utils/terminology';

const OrgBrandingContext = createContext(null);

const CLC_BRANDING = Object.freeze({
  slug: 'clc',
  displayName: 'Crane Lake',
  productName: 'CLC Bunk Logs',
  isClc: true,
  logoUrl: null,
  heroUrl: null,
  terminology: DEFAULT_TERMS,
});

/** Build branding state from a resolved tenant slug (sync, no network). */
export function brandingFromSlug(slug, { loading = false } = {}) {
  if (slug === null || slug === 'clc') {
    return { ...CLC_BRANDING, slug, loading };
  }
  return {
    slug,
    // Placeholder until the API returns display_name; avoids CLC flash on other tenants.
    displayName: slug,
    productName: 'BunkLogs',
    isClc: false,
    logoUrl: null,
    heroUrl: null,
    terminology: DEFAULT_TERMS,
    loading,
  };
}

function initialBranding() {
  return brandingFromSlug(resolveOrganizationSlug(), { loading: true });
}

function normalizeBranding(data) {
  const slug = data?.slug ?? null;
  const logoUrl = data?.branding?.logo_url || null;
  const heroUrl = data?.branding?.hero_url || null;
  const terminology = normalizeTerminology(data?.terminology);
  if (slug === null || slug === 'clc') {
    return { ...CLC_BRANDING, slug, logoUrl, heroUrl, terminology, loading: false };
  }
  return {
    slug,
    displayName: data?.branding?.display_name || data?.name || slug,
    productName: data?.branding?.product_name || 'BunkLogs',
    isClc: false,
    logoUrl,
    heroUrl,
    terminology,
    loading: false,
  };
}

export function OrgBrandingProvider({ children }) {
  const [branding, setBranding] = useState(initialBranding);

  useEffect(() => {
    let cancelled = false;
    fetchOrganizationBranding()
      .then((data) => {
        if (cancelled) return;
        setBranding(normalizeBranding(data));
      })
      .catch(() => {
        if (cancelled) return;
        // Keep hostname-derived tenant shape; only unresolved hosts fall back to CLC.
        setBranding(brandingFromSlug(resolveOrganizationSlug(), { loading: false }));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    document.title = branding.productName;
  }, [branding.productName]);

  return (
    <OrgBrandingContext.Provider value={branding}>
      {children}
    </OrgBrandingContext.Provider>
  );
}

export function useOrgBranding() {
  return useContext(OrgBrandingContext) || initialBranding();
}

/**
 * `term('cohort')` -> the current tenant's word for it.
 *
 * Options: `{ plural: true }` for the "other" form, `{ capitalize: true }`
 * when the noun opens a sentence or a heading.
 */
export function useTerm() {
  const { terminology } = useOrgBranding();
  return useCallback(
    (key, options) => resolveTerm(terminology, key, options),
    [terminology],
  );
}
