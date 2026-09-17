import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  bounceToIntendedOauthOrigin,
  clearOauthFrontendOrigin,
  isAllowedFrontendOrigin,
  rememberOauthFrontendOrigin,
} from '../oauthFrontendOrigin';

describe('isAllowedFrontendOrigin', () => {
  it('allows tenant SPAs and local Vite', () => {
    expect(isAllowedFrontendOrigin('https://tbe.bunklogs.net')).toBe(true);
    expect(isAllowedFrontendOrigin('https://clc.bunklogs.net')).toBe(true);
    expect(isAllowedFrontendOrigin('http://localhost:5173')).toBe(true);
  });

  it('rejects reserved hosts and open redirects', () => {
    expect(isAllowedFrontendOrigin('https://admin.bunklogs.net')).toBe(false);
    expect(isAllowedFrontendOrigin('https://evil.example.com')).toBe(false);
    expect(isAllowedFrontendOrigin('https://tbe.bunklogs.net/phish')).toBe(false);
  });
});

describe('bounceToIntendedOauthOrigin', () => {
  afterEach(() => {
    clearOauthFrontendOrigin();
    vi.unstubAllGlobals();
  });

  it('sends a multi-org user from CLC back to the TBE host they started on', () => {
    const replace = vi.fn();
    vi.stubGlobal('window', {
      location: {
        origin: 'https://clc.bunklogs.net',
        hostname: 'clc.bunklogs.net',
        protocol: 'https:',
        pathname: '/auth/callback',
        search: '',
        hash: '#access_token=tok&refresh_token=ref',
        replace,
      },
    });
    document.cookie = 'oauth_frontend_origin=https%3A%2F%2Ftbe.bunklogs.net; Path=/';

    expect(bounceToIntendedOauthOrigin()).toBe(true);
    expect(replace).toHaveBeenCalledWith(
      'https://tbe.bunklogs.net/auth/callback#access_token=tok&refresh_token=ref',
    );
  });

  it('stays put when the callback already landed on the starting tenant', () => {
    rememberOauthFrontendOrigin('https://tbe.bunklogs.net');
    const replace = vi.fn();
    vi.stubGlobal('window', {
      location: {
        origin: 'https://tbe.bunklogs.net',
        hostname: 'tbe.bunklogs.net',
        protocol: 'https:',
        pathname: '/auth/callback',
        search: '',
        hash: '#access_token=tok',
        replace,
      },
    });

    expect(bounceToIntendedOauthOrigin()).toBe(false);
    expect(replace).not.toHaveBeenCalled();
  });
});
