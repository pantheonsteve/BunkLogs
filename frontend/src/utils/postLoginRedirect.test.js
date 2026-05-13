import { describe, expect, it } from 'vitest';
import { safeNextPath } from './postLoginRedirect';

describe('safeNextPath', () => {
  it('allows internal paths', () => {
    expect(safeNextPath('/reflect')).toBe('/reflect');
    expect(safeNextPath('/reflect?foo=1')).toBe('/reflect?foo=1');
  });

  it('rejects open redirects', () => {
    expect(safeNextPath('//evil.com')).toBe('/dashboard');
    expect(safeNextPath('https://evil.com')).toBe('/dashboard');
    expect(safeNextPath('/\\evil')).toBe('/dashboard');
  });

  it('defaults for empty', () => {
    expect(safeNextPath('')).toBe('/dashboard');
    expect(safeNextPath(null)).toBe('/dashboard');
  });
});
