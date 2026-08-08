/**
 * OrgBrandingProvider / useOrgBranding tests (TBE Frontend Readiness).
 *
 * Covers the three shapes consumers rely on: the CLC-shaped default
 * before the fetch resolves, a resolved non-clc org (TBE) rendering
 * text-only branding, and a fetch failure falling back to the CLC
 * default rather than an empty/broken state.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

const fetchBrandingMock = vi.fn();
vi.mock('../../api/organization', () => ({
  fetchOrganizationBranding: (...args) => fetchBrandingMock(...args),
}));

import { OrgBrandingProvider, useOrgBranding } from '../OrgBrandingContext';

function Probe() {
  const branding = useOrgBranding();
  return (
    <div>
      <span data-testid="slug">{String(branding.slug)}</span>
      <span data-testid="displayName">{branding.displayName}</span>
      <span data-testid="productName">{branding.productName}</span>
      <span data-testid="isClc">{String(branding.isClc)}</span>
    </div>
  );
}

beforeEach(() => {
  fetchBrandingMock.mockReset();
  document.title = '';
});

describe('OrgBrandingProvider', () => {
  it('defaults to the CLC shape before the fetch resolves', () => {
    fetchBrandingMock.mockReturnValue(new Promise(() => {})); // never resolves
    render(
      <OrgBrandingProvider>
        <Probe />
      </OrgBrandingProvider>,
    );

    expect(screen.getByTestId('displayName')).toHaveTextContent('Crane Lake');
    expect(screen.getByTestId('isClc')).toHaveTextContent('true');
  });

  it('renders TBE branding and sets document.title once resolved', async () => {
    fetchBrandingMock.mockResolvedValue({
      slug: 'tbe',
      name: 'Temple Beth-El',
      branding: { display_name: 'Temple Beth-El', product_name: 'BunkLogs' },
    });
    render(
      <OrgBrandingProvider>
        <Probe />
      </OrgBrandingProvider>,
    );

    await waitFor(() => expect(screen.getByTestId('slug')).toHaveTextContent('tbe'));
    expect(screen.getByTestId('displayName')).toHaveTextContent('Temple Beth-El');
    expect(screen.getByTestId('isClc')).toHaveTextContent('false');
    expect(document.title).toBe('BunkLogs');
  });

  it('keeps the CLC default when the fetch fails', async () => {
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

  it('useOrgBranding falls back to the CLC default outside a provider', () => {
    render(<Probe />);
    expect(screen.getByTestId('displayName')).toHaveTextContent('Crane Lake');
    expect(screen.getByTestId('isClc')).toHaveTextContent('true');
  });
});
