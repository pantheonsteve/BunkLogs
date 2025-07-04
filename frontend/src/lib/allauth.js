import { getCSRFToken } from './django'

// Enhanced CSRF token fetcher that can work synchronously
async function getCSRFTokenAsync() {
  console.log('=== getCSRFTokenAsync START ===');
  
  // First try the standard method
  const cookieToken = getCSRFToken();
  console.log('Cookie token from getCSRFToken():', cookieToken ? 'YES (' + cookieToken.substring(0, 8) + '...)' : 'NO');
  
  if (cookieToken) {
    console.log('Using cookie token');
    return cookieToken;
  }

  // If no cookie token, fetch from server
  try {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const fetchUrl = `${apiUrl}/api/get-csrf-token/`;
    console.log('Fetching CSRF token from:', fetchUrl);
    
    const response = await fetch(fetchUrl, {
      credentials: 'include'
    });
    
    console.log('CSRF fetch response status:', response.status);
    console.log('CSRF fetch response headers:', [...response.headers.entries()]);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log('CSRF fetch response data:', data);
    
    if (data.csrfToken) {
      console.log('CSRF token fetched for allauth:', data.csrfToken.substring(0, 6) + '...');
      return data.csrfToken;
    } else {
      throw new Error('No csrfToken in response');
    }
  } catch (error) {
    console.error('Failed to fetch CSRF token for allauth:', error);
    console.log('Falling back to getCSRFToken()');
    return getCSRFToken(); // Fallback to original method
  }
}

export const Client = Object.freeze({
  APP: 'app',
  BROWSER: 'browser'
})

export const settings = {
  client: Client.BROWSER,
  baseUrl: `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/_allauth/browser/v1`,
  withCredentials: true
}

const ACCEPT_JSON = {
  accept: 'application/json'
}

export const AuthProcess = Object.freeze({
  LOGIN: 'login',
  CONNECT: 'connect'
})

export const Flows = Object.freeze({
  LOGIN: 'login',
  LOGIN_BY_CODE: 'login_by_code',
  MFA_AUTHENTICATE: 'mfa_authenticate',
  MFA_REAUTHENTICATE: 'mfa_reauthenticate',
  MFA_TRUST: 'mfa_trust',
  MFA_WEBAUTHN_SIGNUP: 'mfa_signup_webauthn',
  PASSWORD_RESET_BY_CODE: 'password_reset_by_code',
  PROVIDER_REDIRECT: 'provider_redirect',
  PROVIDER_SIGNUP: 'provider_signup',
  REAUTHENTICATE: 'reauthenticate',
  SIGNUP: 'signup',
  VERIFY_EMAIL: 'verify_email',
})

export const URLs = Object.freeze({
  // Meta
  CONFIG: '/config',

  // Account management
  CHANGE_PASSWORD: '/account/password/change',
  EMAIL: '/account/email',
  PROVIDERS: '/account/providers',

  // Account management: 2FA
  AUTHENTICATORS: '/account/authenticators',
  RECOVERY_CODES: '/account/authenticators/recovery-codes',
  TOTP_AUTHENTICATOR: '/account/authenticators/totp',

  // Auth: Basics
  LOGIN: '/auth/login',
  REQUEST_LOGIN_CODE: '/auth/code/request',
  CONFIRM_LOGIN_CODE: '/auth/code/confirm',
  SESSION: '/auth/session',
  REAUTHENTICATE: '/auth/reauthenticate',
  REQUEST_PASSWORD_RESET: '/auth/password/request',
  RESET_PASSWORD: '/auth/password/reset',
  SIGNUP: '/auth/signup',
  VERIFY_EMAIL: '/auth/email/verify',

  // Auth: 2FA
  MFA_AUTHENTICATE: '/auth/2fa/authenticate',
  MFA_REAUTHENTICATE: '/auth/2fa/reauthenticate',
  MFA_TRUST: '/auth/2fa/trust',

  // Auth: Social
  PROVIDER_SIGNUP: '/auth/provider/signup',
  REDIRECT_TO_PROVIDER: '/auth/provider/redirect',
  PROVIDER_TOKEN: '/auth/provider/token',

  // Auth: Sessions
  SESSIONS: '/auth/sessions',

  // Auth: WebAuthn
  REAUTHENTICATE_WEBAUTHN: '/auth/webauthn/reauthenticate',
  AUTHENTICATE_WEBAUTHN: '/auth/webauthn/authenticate',
  LOGIN_WEBAUTHN: '/auth/webauthn/login',
  SIGNUP_WEBAUTHN: '/auth/webauthn/signup',
  WEBAUTHN_AUTHENTICATOR: '/account/authenticators/webauthn'
})

export const AuthenticatorType = Object.freeze({
  TOTP: 'totp',
  RECOVERY_CODES: 'recovery_codes',
  WEBAUTHN: 'webauthn'
})

function postForm (action, data) {
  const f = document.createElement('form')
  f.method = 'POST'
  f.action = settings.baseUrl + action

  for (const key in data) {
    const d = document.createElement('input')
    d.type = 'hidden'
    d.name = key
    d.value = data[key]
    f.appendChild(d)
  }
  document.body.appendChild(f)
  f.submit()
}

const tokenStorage = window.sessionStorage

export function getSessionToken () {
  return tokenStorage.getItem('sessionToken')
}

async function request (method, path, data, headers) {
  const options = {
    method,
    headers: {
      ...ACCEPT_JSON,
      ...headers
    }
  }
  if (settings.withCredentials) {
    options.credentials = 'include'
  }
  // Don't pass along authentication related headers to the config endpoint.
  if (path !== URLs.CONFIG) {
    if (settings.client === Client.BROWSER) {
      const csrfToken = getCSRFToken();
      if (csrfToken) {
        options.headers['x-csrftoken'] = csrfToken;
      } else {
        console.warn('No CSRF token available for allauth request');
      }
    } else if (settings.client === Client.APP) {
      // IMPORTANT!: Do NOT use `Client.APP` in a browser context, as you will
      // be vulnerable to CSRF attacks. This logic is only here for
      // development/demonstration/testing purposes...
      options.headers['User-Agent'] = 'django-allauth example app'
      const sessionToken = getSessionToken()
      if (sessionToken) {
        options.headers['X-Session-Token'] = sessionToken
      }
    }
  }

  if (typeof data !== 'undefined') {
    options.body = JSON.stringify(data)
    options.headers['Content-Type'] = 'application/json'
  }
  
  const requestUrl = settings.baseUrl + path;
  
  console.log('=== ALLAUTH REQUEST ===');
  console.log('Method:', method);
  console.log('URL:', requestUrl);
  console.log('Options:', options);
  console.log('Data:', data);
  
  const resp = await fetch(requestUrl, options)
  console.log('Response status:', resp.status);
  console.log('Response headers:', [...resp.headers.entries()]);
  
  const msg = await resp.json()
  console.log('Response data:', msg);
  
  if (msg.status === 410) {
    tokenStorage.removeItem('sessionToken')
  }
  if (msg.meta?.session_token) {
    tokenStorage.setItem('sessionToken', msg.meta.session_token)
  }
  if ([401, 410].includes(msg.status) || (msg.status === 200 && msg.meta?.is_authenticated)) {
    const event = new CustomEvent('allauth.auth.change', { detail: msg })
    document.dispatchEvent(event)
  }
  return msg
}

export async function login (data) {
  return await request('POST', URLs.LOGIN, data)
}

export async function reauthenticate (data) {
  return await request('POST', URLs.REAUTHENTICATE, data)
}

export async function logout () {
  return await request('DELETE', URLs.SESSION)
}

export async function signUp (data) {
  return await request('POST', URLs.SIGNUP, data)
}

export async function signUpByPasskey (data) {
  return await request('POST', URLs.SIGNUP_WEBAUTHN, data)
}

export async function providerSignup (data) {
  return await request('POST', URLs.PROVIDER_SIGNUP, data)
}

export async function getProviderAccounts () {
  return await request('GET', URLs.PROVIDERS)
}

export async function disconnectProviderAccount (providerId, accountUid) {
  return await request('DELETE', URLs.PROVIDERS, { provider: providerId, account: accountUid })
}

export async function requestPasswordReset (email) {
  return await request('POST', URLs.REQUEST_PASSWORD_RESET, { email })
}

export async function requestLoginCode (email) {
  return await request('POST', URLs.REQUEST_LOGIN_CODE, { email })
}

export async function confirmLoginCode (code) {
  return await request('POST', URLs.CONFIRM_LOGIN_CODE, { code })
}

export async function getEmailVerification (key) {
  return await request('GET', URLs.VERIFY_EMAIL, undefined, { 'X-Email-Verification-Key': key })
}

export async function getEmailAddresses () {
  return await request('GET', URLs.EMAIL)
}
export async function getSessions () {
  return await request('GET', URLs.SESSIONS)
}

export async function endSessions (ids) {
  return await request('DELETE', URLs.SESSIONS, { sessions: ids })
}

export async function getAuthenticators () {
  return await request('GET', URLs.AUTHENTICATORS)
}

export async function getTOTPAuthenticator () {
  return await request('GET', URLs.TOTP_AUTHENTICATOR)
}

export async function mfaAuthenticate (code) {
  return await request('POST', URLs.MFA_AUTHENTICATE, { code })
}

export async function mfaReauthenticate (code) {
  return await request('POST', URLs.MFA_REAUTHENTICATE, { code })
}

export async function mfaTrust (trust) {
  return await request('POST', URLs.MFA_TRUST, { trust })
}

export async function activateTOTPAuthenticator (code) {
  return await request('POST', URLs.TOTP_AUTHENTICATOR, { code })
}

export async function deactivateTOTPAuthenticator () {
  return await request('DELETE', URLs.TOTP_AUTHENTICATOR)
}

export async function getRecoveryCodes () {
  return await request('GET', URLs.RECOVERY_CODES)
}

export async function generateRecoveryCodes () {
  return await request('POST', URLs.RECOVERY_CODES)
}

export async function getConfig () {
  return await request('GET', URLs.CONFIG)
}

export async function addEmail (email) {
  return await request('POST', URLs.EMAIL, { email })
}

export async function deleteEmail (email) {
  return await request('DELETE', URLs.EMAIL, { email })
}

export async function markEmailAsPrimary (email) {
  return await request('PATCH', URLs.EMAIL, { email, primary: true })
}

export async function requestEmailVerification (email) {
  return await request('PUT', URLs.EMAIL, { email })
}

export async function verifyEmail (key) {
  return await request('POST', URLs.VERIFY_EMAIL, { key })
}

export async function getPasswordReset (key) {
  // Ensure we have a CSRF token before making the request
  const csrfToken = getCSRFToken();
  if (!csrfToken) {
    // Try to get CSRF token synchronously
    await getCSRFTokenAsync();
  }
  return await request('GET', URLs.RESET_PASSWORD, undefined, { 'X-Password-Reset-Key': key })
}

export async function resetPassword (data) {
  // Ensure we have a CSRF token before making the request
  const csrfToken = getCSRFToken();
  if (!csrfToken) {
    // Try to get CSRF token synchronously
    await getCSRFTokenAsync();
  }
  return await request('POST', URLs.RESET_PASSWORD, data)
}

export async function changePassword (data) {
  return await request('POST', URLs.CHANGE_PASSWORD, data)
}

export async function getAuth () {
  return await request('GET', URLs.SESSION)
}

export async function authenticateByToken (providerId, token, process = AuthProcess.LOGIN) {
  return await request('POST', URLs.PROVIDER_TOKEN, {
    provider: providerId,
    token,
    process
  }
  )
}

export async function redirectToProvider (providerId, callbackURL, process = AuthProcess.LOGIN) {
  console.log('=== redirectToProvider START ===');
  console.log('Provider ID:', providerId);
  console.log('Callback URL:', callbackURL);
  console.log('Process:', process);
  console.log('Settings baseUrl:', settings.baseUrl);
  console.log('Full form action will be:', settings.baseUrl + URLs.REDIRECT_TO_PROVIDER);
  
  // Get CSRF token asynchronously
  const csrfToken = await getCSRFTokenAsync();
  console.log('Got CSRF token:', csrfToken ? 'YES (' + csrfToken.substring(0, 8) + '...)' : 'NO');
  
  if (!csrfToken) {
    console.error('No CSRF token available for provider redirect');
    throw new Error('CSRF token is required for social login');
  }
  
  // Create form manually since we need to wait for the async CSRF token
  const f = document.createElement('form')
  f.method = 'POST'
  f.action = settings.baseUrl + URLs.REDIRECT_TO_PROVIDER

  const fullCallbackUrl = window.location.protocol + '//' + window.location.host + callbackURL;
  const data = {
    provider: providerId,
    process,
    callback_url: fullCallbackUrl,
    csrfmiddlewaretoken: csrfToken
  }

  console.log('=== FORM SUBMISSION DATA ===');
  console.log('Form action:', f.action);
  console.log('Form method:', f.method);
  console.log('Form data:');
  for (const [key, value] of Object.entries(data)) {
    console.log(`  ${key}: ${value}`);
  }
  
  // Add form inputs
  for (const key in data) {
    const d = document.createElement('input')
    d.type = 'hidden'
    d.name = key
    d.value = data[key]
    f.appendChild(d)
  }
  
  // Log form HTML for debugging
  console.log('Generated form HTML:', f.outerHTML);
  
  // Add form to document and submit
  document.body.appendChild(f)
  console.log('Form appended to body, submitting...');
  
  // Add a delay to see if we can catch any immediate redirects
  setTimeout(() => {
    console.log('About to submit form...');
    f.submit();
    console.log('Form submitted!');
  }, 100);
  
  console.log('=== redirectToProvider END ===');
}

export async function getWebAuthnCreateOptions (passwordless) {
  let url = URLs.WEBAUTHN_AUTHENTICATOR
  if (passwordless) {
    url += '?passwordless'
  }
  return await request('GET', url)
}

export async function getWebAuthnCreateOptionsAtSignup () {
  return await request('GET', URLs.SIGNUP_WEBAUTHN)
}

export async function addWebAuthnCredential (name, credential) {
  return await request('POST', URLs.WEBAUTHN_AUTHENTICATOR, {
    name,
    credential
  })
}

export async function signupWebAuthnCredential (name, credential) {
  return await request('PUT', URLs.SIGNUP_WEBAUTHN, {
    name,
    credential
  })
}

export async function deleteWebAuthnCredential (ids) {
  return await request('DELETE', URLs.WEBAUTHN_AUTHENTICATOR, { authenticators: ids })
}

export async function updateWebAuthnCredential (id, data) {
  return await request('PUT', URLs.WEBAUTHN_AUTHENTICATOR, { id, ...data })
}

export async function getWebAuthnRequestOptionsForReauthentication () {
  return await request('GET', URLs.REAUTHENTICATE_WEBAUTHN)
}

export async function reauthenticateUsingWebAuthn (credential) {
  return await request('POST', URLs.REAUTHENTICATE_WEBAUTHN, { credential })
}

export async function authenticateUsingWebAuthn (credential) {
  return await request('POST', URLs.AUTHENTICATE_WEBAUTHN, { credential })
}

export async function loginUsingWebAuthn (credential) {
  return await request('POST', URLs.LOGIN_WEBAUTHN, { credential })
}

export async function getWebAuthnRequestOptionsForLogin () {
  return await request('GET', URLs.LOGIN_WEBAUTHN)
}

export async function getWebAuthnRequestOptionsForAuthentication () {
  return await request('GET', URLs.AUTHENTICATE_WEBAUTHN)
}

export function setup (client, baseUrl, withCredentials) {
  settings.client = client
  settings.baseUrl = baseUrl
  settings.withCredentials = withCredentials
  
  // Log settings after they've been updated
  console.log('allauth.js: settings.baseUrl', settings.baseUrl)
  console.log('allauth.js: settings.client', settings.client)
  console.log('allauth.js: settings.withCredentials', settings.withCredentials)
}