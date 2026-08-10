/**
 * Signin org branding tests (TBE Frontend Readiness).
 *
 * Asserts the CLC photo logo/hero/heading render for the default (clc)
 * org, and that a non-clc org renders text-only branding with no CLC
 * image assets in the DOM.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Signin from '../Signin';

vi.mock('../../images/clc-logo.jpeg', () => ({ default: 'logo.jpg' }));
vi.mock('../../images/crane_lake/DSC_1985.webp', () => ({ default: 'hero.webp' }));

const mockUseAuth = vi.fn();
vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

const mockUseOrgBranding = vi.fn();
vi.mock('../../context/OrgBrandingContext', () => ({
  useOrgBranding: () => mockUseOrgBranding(),
}));

vi.mock('../../socialaccount/ProviderList', () => ({
  default: () => null,
}));
vi.mock('../../components/SocialLoginButton', () => ({
  default: () => null,
}));

function renderSignin() {
  return render(
    <MemoryRouter initialEntries={['/signin']}>
      <Signin />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mockUseAuth.mockReset();
  mockUseAuth.mockReturnValue({ login: vi.fn() });
  mockUseOrgBranding.mockReset();
});

describe('Signin — org-aware branding', () => {
  it('renders the CLC logo, hero photo, and heading for the clc org', () => {
    mockUseOrgBranding.mockReturnValue({
      slug: 'clc',
      displayName: 'Crane Lake',
      productName: 'CLC Bunk Logs',
      isClc: true,
      logoUrl: null,
      heroUrl: null,
      loading: false,
    });
    renderSignin();

    expect(screen.getByText('CLC Bunk Logs')).toBeInTheDocument();
    expect(screen.getByAltText('Crane Lake')).toHaveAttribute('src', 'logo.jpg');
    expect(document.querySelector('img[src="hero.webp"]')).toBeTruthy();
  });

  it('renders text-only branding for a non-clc org with no CLC image assets', () => {
    mockUseOrgBranding.mockReturnValue({
      slug: 'tbe',
      displayName: 'Temple Beth-El',
      productName: 'BunkLogs',
      isClc: false,
      logoUrl: null,
      heroUrl: null,
      loading: false,
    });
    renderSignin();

    // Both the top-left mark and the page heading render displayName as text.
    expect(screen.getAllByText('Temple Beth-El').length).toBeGreaterThan(0);
    expect(screen.queryByText('CLC Bunk Logs')).not.toBeInTheDocument();
    const images = screen.queryAllByRole('img', { hidden: true });
    expect(images.some((img) => img.getAttribute('src') === 'logo.jpg')).toBe(false);
    expect(images.some((img) => img.getAttribute('src') === 'hero.webp')).toBe(false);
  });

  it('renders uploaded logo and hero for a non-clc org', () => {
    mockUseOrgBranding.mockReturnValue({
      slug: 'tbe',
      displayName: 'Temple Beth-El',
      productName: 'BunkLogs',
      isClc: false,
      logoUrl: 'https://cdn.example/tbe/logo.png',
      heroUrl: 'https://cdn.example/tbe/hero.jpg',
      loading: false,
    });
    renderSignin();

    expect(screen.getByAltText('Temple Beth-El')).toHaveAttribute(
      'src',
      'https://cdn.example/tbe/logo.png',
    );
    // Hero panel uses Tailwind `hidden md:block`; query the DOM directly.
    expect(
      document.querySelector('img[src="https://cdn.example/tbe/hero.jpg"]'),
    ).toBeTruthy();
    expect(screen.getAllByText('Temple Beth-El').length).toBe(1);
  });
});
