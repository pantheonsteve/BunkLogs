const ORIGINAL_ACCESS = 'dev_impersonation_original_access_token';
const ORIGINAL_REFRESH = 'dev_impersonation_original_refresh_token';
const ORIGINAL_PROFILE = 'dev_impersonation_original_user_profile';
const ACTIVE_META = 'dev_impersonation_active';

export function isImpersonating() {
  try {
    return Boolean(localStorage.getItem(ACTIVE_META));
  } catch {
    return false;
  }
}

export function getImpersonationMeta() {
  try {
    const raw = localStorage.getItem(ACTIVE_META);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveOriginalSession() {
  if (isImpersonating()) return;
  try {
    const access = localStorage.getItem('access_token');
    const refresh = localStorage.getItem('refresh_token');
    const profile = localStorage.getItem('user_profile');
    if (access) localStorage.setItem(ORIGINAL_ACCESS, access);
    if (refresh) localStorage.setItem(ORIGINAL_REFRESH, refresh);
    if (profile) localStorage.setItem(ORIGINAL_PROFILE, profile);
  } catch (error) {
    console.warn('Could not save original session before impersonation:', error);
  }
}

export function markImpersonationActive(targetUser) {
  try {
    localStorage.setItem(
      ACTIVE_META,
      JSON.stringify({
        email: targetUser.email,
        name:
          `${targetUser.first_name || ''} ${targetUser.last_name || ''}`.trim()
          || targetUser.email,
        role: targetUser.role || '',
      }),
    );
  } catch (error) {
    console.warn('Could not mark impersonation active:', error);
  }
}

export function clearImpersonationState() {
  try {
    localStorage.removeItem(ACTIVE_META);
    localStorage.removeItem(ORIGINAL_ACCESS);
    localStorage.removeItem(ORIGINAL_REFRESH);
    localStorage.removeItem(ORIGINAL_PROFILE);
  } catch (error) {
    console.warn('Could not clear impersonation state:', error);
  }
}

export function getOriginalSession() {
  try {
    return {
      access_token: localStorage.getItem(ORIGINAL_ACCESS),
      refresh_token: localStorage.getItem(ORIGINAL_REFRESH),
      user_profile: localStorage.getItem(ORIGINAL_PROFILE),
    };
  } catch {
    return {
      access_token: null,
      refresh_token: null,
      user_profile: null,
    };
  }
}
