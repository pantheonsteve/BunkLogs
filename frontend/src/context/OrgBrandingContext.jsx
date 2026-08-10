/**
 * Org-aware branding (TBE Frontend Readiness).
 *
 * Fetches the current tenant's display name once on app bootstrap so
 * sign-in/sign-up/password-reset pages and the app shell can show the
 * right org without each page re-fetching. Mounted above `AuthProvider`
 * in App.jsx since the auth pages render before login resolves.
 *
 * Crane Lake safety: `isClc` (and the CLC-shaped default below) is
 * deliberately NOT sourced from the backend `branding` payload for the
 * `clc` org -- it's the literal pre-existing copy. That way Crane Lake's
 * sign-in page is byte-for-byte unchanged even if `setup_crane_lake`
 * hasn't been re-run yet in a given environment to seed
 * `settings.branding`. Backend-sourced text only drives *other* orgs
 * (e.g. `tbe`), which have no legacy hardcoded copy to preserve.
 *
 * Uploaded logo/hero URLs from the API take precedence over bundled CLC
 * assets when present (admin can override CLC images without a deploy).
 */
import React, { createContext, useContext, useEffect, useState } from 'react';
import { fetchOrganizationBranding } from '../api/organization';

const OrgBrandingContext = createContext(null);

const CLC_BRANDING = Object.freeze({
  slug: 'clc',
  displayName: 'Crane Lake',
  productName: 'CLC Bunk Logs',
  isClc: true,
  logoUrl: null,
  heroUrl: null,
});

function normalizeBranding(data) {
  const slug = data?.slug ?? null;
  const logoUrl = data?.branding?.logo_url || null;
  const heroUrl = data?.branding?.hero_url || null;
  // Unresolved (e.g. admin.bunklogs.net, local dev with no tenant
  // override) or the clc tenant itself both keep the legacy CLC look.
  if (slug === null || slug === 'clc') {
    return { ...CLC_BRANDING, slug, logoUrl, heroUrl, loading: false };
  }
  return {
    slug,
    displayName: data?.branding?.display_name || data?.name || slug,
    productName: data?.branding?.product_name || 'BunkLogs',
    isClc: false,
    logoUrl,
    heroUrl,
    loading: false,
  };
}

export function OrgBrandingProvider({ children }) {
  const [branding, setBranding] = useState({ ...CLC_BRANDING, loading: true });

  useEffect(() => {
    let cancelled = false;
    fetchOrganizationBranding()
      .then((data) => {
        if (cancelled) return;
        setBranding(normalizeBranding(data));
      })
      .catch(() => {
        if (cancelled) return;
        // Network/API failure -- keep the CLC-shaped default so nothing
        // ever renders blank or wrong.
        setBranding({ ...CLC_BRANDING, loading: false });
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
  return useContext(OrgBrandingContext) || { ...CLC_BRANDING, loading: true };
}
