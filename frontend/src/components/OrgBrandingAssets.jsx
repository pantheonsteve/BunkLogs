/**
 * Shared org-aware chrome for auth pages + the app shell (TBE Frontend
 * Readiness). Uploaded org logo/hero URLs from the branding API take
 * precedence; Crane Lake falls back to bundled assets; other tenants
 * fall back to text / gradient when no images are configured.
 */
import { NavLink } from 'react-router-dom';
import { useOrgBranding } from '../context/OrgBrandingContext';
import CampLogo from '../images/clc-logo.jpeg';
import AuthImage from '../images/crane_lake/DSC_1985.webp';

/** Bounds the logo mark to the space available in its container. */
const SIDEBAR_LOGO_BOX =
  'flex w-full max-w-full items-center justify-center overflow-hidden h-8 lg:sidebar-expanded:h-10 2xl:h-10';
const SIDEBAR_LOGO_IMAGE = 'max-h-full max-w-full w-auto h-auto object-contain object-center';
const SIDEBAR_LOGO_TEXT =
  'max-w-full truncate text-center text-[10px] font-semibold leading-tight text-gray-800 dark:text-gray-100 lg:sidebar-expanded:text-base 2xl:text-base';

/**
 * Top-left mark: uploaded logo, CLC photo logo, or display name as text.
 *
 * @param {'default' | 'sidebar'} variant
 *   `sidebar` sizes the mark to fit the nav column (icon-only or expanded).
 */
export function OrgLogo({ to = '/', className = 'shrink-0 mr-2 sm:mr-3', variant = 'default' }) {
  const { isClc, displayName, logoUrl, loading } = useOrgBranding();

  if (variant === 'sidebar') {
    return (
      <NavLink end to={to} className="block w-full min-w-0 max-w-full" title={displayName}>
        <div className={SIDEBAR_LOGO_BOX}>
          {logoUrl ? (
            <img className={SIDEBAR_LOGO_IMAGE} src={logoUrl} alt={displayName} />
          ) : isClc ? (
            <img className={SIDEBAR_LOGO_IMAGE} src={CampLogo} alt="Crane Lake" />
          ) : loading ? (
            <span className={SIDEBAR_LOGO_TEXT} aria-hidden="true">&nbsp;</span>
          ) : (
            <span className={SIDEBAR_LOGO_TEXT}>{displayName}</span>
          )}
        </div>
      </NavLink>
    );
  }

  const logoClassName = isClc && !logoUrl
    ? className
    : `${className} max-h-9 w-auto object-contain`;

  return (
    <NavLink end to={to} className="block">
      {logoUrl ? (
        <img className={logoClassName} src={logoUrl} alt={displayName} width="140" height="36" />
      ) : isClc ? (
        <img className={className} width="70" height="35" viewBox="0 0 36 36" src={CampLogo} alt="Crane Lake" />
      ) : loading ? (
        <span className="inline-block h-9 w-[4.5rem]" aria-hidden="true" />
      ) : (
        <span className="text-lg font-semibold text-gray-800 dark:text-gray-100">{displayName}</span>
      )}
    </NavLink>
  );
}

/** Right-side auth page hero: uploaded image, CLC photo, or plain panel. */
export function OrgHeroPanel({ highPriority = false }) {
  const { isClc, heroUrl } = useOrgBranding();
  const heroSrc = heroUrl || (isClc ? AuthImage : null);

  return (
    <div className="hidden md:block absolute top-0 bottom-0 right-0 md:w-1/2" aria-hidden="true">
      {heroSrc ? (
        <img
          className="object-cover object-center w-full h-full"
          src={heroSrc}
          width="760"
          height="1024"
          alt=""
          decoding="async"
          {...(highPriority ? { fetchPriority: 'high' } : {})}
        />
      ) : (
        <div className="w-full h-full bg-gradient-to-br from-violet-500 to-violet-700" />
      )}
    </div>
  );
}
