/**
 * Shared org-aware chrome for auth pages + the app shell (TBE Frontend
 * Readiness). Crane Lake keeps its existing photo logo/hero exactly as
 * before; any other tenant (no image assets yet) gets a plain text
 * mark instead. See `context/OrgBrandingContext.jsx` for the `isClc`
 * fallback rules.
 */
import { NavLink } from 'react-router-dom';
import { useOrgBranding } from '../context/OrgBrandingContext';
import CampLogo from '../images/clc-logo.jpeg';
import AuthImage from '../images/crane_lake/DSC_1985.webp';

/** Top-left mark: CLC photo logo, or the org's display name as text. */
export function OrgLogo({ to = '/', className = 'shrink-0 mr-2 sm:mr-3' }) {
  const { isClc, displayName } = useOrgBranding();
  return (
    <NavLink end to={to} className="block">
      {isClc ? (
        <img className={className} width="70" height="35" viewBox="0 0 36 36" src={CampLogo} />
      ) : (
        <span className="text-lg font-semibold text-gray-800 dark:text-gray-100">{displayName}</span>
      )}
    </NavLink>
  );
}

/** Right-side auth page hero: CLC photo, or a plain panel (no asset yet for other orgs). */
export function OrgHeroPanel({ highPriority = false }) {
  const { isClc } = useOrgBranding();
  return (
    <div className="hidden md:block absolute top-0 bottom-0 right-0 md:w-1/2" aria-hidden="true">
      {isClc ? (
        <img
          className="object-cover object-center w-full h-full"
          src={AuthImage}
          width="760"
          height="1024"
          alt="Authentication"
          decoding="async"
          {...(highPriority ? { fetchPriority: 'high' } : {})}
        />
      ) : (
        <div className="w-full h-full bg-gradient-to-br from-violet-500 to-violet-700" />
      )}
    </div>
  );
}
