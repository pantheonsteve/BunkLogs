/**
 * OrgBrandingProvider / useOrgBranding tests (TBE Frontend Readiness).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

const fetchBrandingMock = vi.fn();
vi.mock('../../api/organization', () => ({
  fetchOrganizationBranding: (...args) => fetchBrandingMock(...args),
}));

const resolveOrganizationSlugMock = vi.fn(() => null);
vi.mock('../../utils/orgSlug', () => ({
  resolveOrganizationSlug: () => resolveOrganizationSlugMock(),
}));

import { OrgBrandingProvider, useOrgBranding, brandingFromSlug } from '../OrgBrandingContext';

function Probe() {
  const branding = useOrgBranding();
  return (
    <div>
      <span data-testid="slug">{String(branding.slug)}</span>
      <span data-testid="displayName">{branding.displayName}</span>
      <span data-testid="productName">{branding.productName}</span>
      <span data-testid="isClc">{String(branding.isClc)}</span>
      <span data-testid="loading">{String(branding.loading)}</span>
      <span data-testid="logoUrl">{branding.logoUrl || ''}</span>
      <span data-testid="heroUrl">{branding.heroUrl || ''}</span>
    </div>
  );
}

beforeEach(() => {
  fetchBrandingMock.mockReset();
  resolveOrganizationSlugMock.mockReset();
  resolveOrganizationSlugMock.mockReturnValue(null);
  document.title = '';
});

describe('brandingFromSlug', () => {
  it('returns CLC shape for null and clc slugs', () => {
    expect(brandingFromSlug(null, { loading: true }).isClc).toBe(true);
    expect(brandingFromSlug('clc', { loading: true }).isClc).toBe(true);
  });

  it('returns non-CLC placeholder for other tenants', () => {
    const tbe = brandingFromSlug('tbe', { loading: true });
    expect(tbe.isClc).toBe(false);
    expect(tbe.slug).toBe('tbe');
    expect(tbe.loading).toBe(true);
    expect(tbe.logoUrl).toBeNull();
  });
});

describe('OrgBrandingProvider', () => {
  it('defaults to the CLC shape on an unresolved host before the fetch resolves', () => {
    fetchBrandingMock.mockReturnValue(new Promise(() => {}));
    render(
      <OrgBrandingProvider>
        <Probe />
      </OrgBrandingProvider>,
    );

    expect(screen.getByTestId('displayName')).toHaveTextContent('Crane Lake');
    expect(screen.getByTestId('isClc')).toHaveTextContent('true');
    expect(screen.getByTestId('loading')).toHaveTextContent('true');
  });

  it('starts non-CLC on a tenant subdomain before the fetch resolves', () => {
    resolveOrganizationSlugMock.mockReturnValue('tbe');
    fetchBrandingMock.mockReturnValue(new Promise(() => {}));
    render(
      <OrgBrandingProvider>
        <Probe />
      </OrgBrandingProvider>,
    );

    expect(screen.getByTestId('slug')).toHaveTextContent('tbe');
    expect(screen.getByTestId('isClc')).toHaveTextContent('false');
    expect(screen.getByTestId('loading')).toHaveTextContent('true');
    expect(screen.getByTestId('logoUrl')).toHaveTextContent('');
  });

  it('renders TBE branding and sets document.title once resolved', async () => {
    resolveOrganizationSlugMock.mockReturnValue('tbe');
    fetchBrandingMock.mockResolvedValue({
      slug: 'tbe',
      name: 'Temple Beth-El',
      branding: {
        display_name: 'Temple Beth-El',
        product_name: 'BunkLogs',
        logo_url: 'https://cdn.example/tbe/logo.png?v=1',
        hero_url: 'https://cdn.example/tbe/hero.jpg?v=1',
      },
    });
    render(
      <OrgBrandingProvider>
        <Probe />
      </OrgBrandingProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('slug')).toHaveTextContent('tbe');
      expect(document.title).toBe('BunkLogs');
    });
    expect(screen.getByTestId('displayName')).toHaveTextContent('Temple Beth-El');
    expect(screen.getByTestId('isClc')).toHaveTextContent('false');
    expect(screen.getByTestId('loading')).toHaveTextContent('false');
    expect(screen.getByTestId('logoUrl')).toHaveTextContent('https://cdn.example/tbe/logo.png?v=1');
    expect(screen.getByTestId('heroUrl')).toHaveTextContent('https://cdn.example/tbe/hero.jpg?v=1');
  });

  it('keeps the CLC default when the fetch fails on an unresolved host', async () => {
    fetchBrandingMock.mockRejectedValue(new Error('network error'));
    render(
      <OrgBrandingProvider>
        <Probe />
      </OrgBrandingProvider>,
    );

    await waitFor(() => expect(document.title).toBe('CLC Bunk Logs'));
    expect(screen.getByTestId('displayName')).toHaveTextContent('Crane Lake');
    expect(screen.getByTestId('isClc')).toHaveTextContent('true');
  });

  it('keeps the tenant placeholder when the fetch fails on a non-CLC host', async () => {
    resolveOrganizationSlugMock.mockReturnValue('tbe');
    fetchBrandingMock.mockRejectedValue(new Error('network error'));
    render(
      <OrgBrandingProvider>
        <Probe />
      </OrgBrandingProvider>,
    );

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    expect(screen.getByTestId('isClc')).toHaveTextContent('false');
    expect(screen.getByTestId('slug')).toHaveTextContent('tbe');
    expect(document.title).toBe('BunkLogs');
  });

  it('useOrgBranding falls back to hostname-derived state outside a provider', () => {
    resolveOrganizationSlugMock.mockReturnValue('tbe');
    render(<Probe />);
    expect(screen.getByTestId('slug')).toHaveTextContent('tbe');
    expect(screen.getByTestId('isClc')).toHaveTextContent('false');
  });
});
