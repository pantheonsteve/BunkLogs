import { describe, it, expect, vi, beforeEach } from 'vitest';

const initMock = vi.fn();
const setUserMock = vi.fn();
const clearUserMock = vi.fn();
const addActionMock = vi.fn();

vi.mock('@datadog/browser-rum', () => ({
  datadogRum: {
    init: initMock,
    setUser: setUserMock,
    clearUser: clearUserMock,
    addAction: addActionMock,
    setGlobalContextProperty: vi.fn(),
    removeGlobalContextProperty: vi.fn(),
  },
}));

vi.mock('@datadog/browser-rum-react', () => ({
  reactPlugin: vi.fn(() => ({})),
}));

describe('datadog helpers', () => {
  beforeEach(() => {
    vi.resetModules();
    initMock.mockClear();
    setUserMock.mockClear();
    clearUserMock.mockClear();
    addActionMock.mockClear();
  });

  it('does not initialize without credentials', async () => {
    const { initDatadogRum, isDatadogRumEnabled } = await import('../datadog');
    initDatadogRum();
    expect(initMock).not.toHaveBeenCalled();
    expect(isDatadogRumEnabled()).toBe(false);
  });

  it('sets user context when RUM is enabled', async () => {
    vi.stubEnv('VITE_DATADOG_APPLICATION_ID', 'app-id');
    vi.stubEnv('VITE_DATADOG_CLIENT_TOKEN', 'client-token');
    vi.stubEnv('VITE_DATADOG_FORCE_ENABLE', 'true');
    vi.stubEnv('PROD', '');

    const { initDatadogRum, setDatadogUser } = await import('../datadog');
    initDatadogRum();
    setDatadogUser({
      id: 42,
      email: 'counselor@example.com',
      name: 'Test Counselor',
      role: 'Counselor',
    });

    expect(initMock).toHaveBeenCalledTimes(1);
    expect(setUserMock).toHaveBeenCalledWith({
      id: '42',
      email: 'counselor@example.com',
      name: 'Test Counselor',
    });
  });

  it('tracks login and reflection submission actions', async () => {
    vi.stubEnv('VITE_DATADOG_APPLICATION_ID', 'app-id');
    vi.stubEnv('VITE_DATADOG_CLIENT_TOKEN', 'client-token');
    vi.stubEnv('VITE_DATADOG_FORCE_ENABLE', 'true');
    vi.stubEnv('PROD', '');

    const { initDatadogRum, trackUserLogin, trackApiSuccess } = await import('../datadog');
    initDatadogRum();

    trackUserLogin({ user: { email: 'a@example.com' } });
    trackApiSuccess(
      { method: 'post', url: '/api/v1/reflections/', data: {} },
      { data: { id: 9, template: 3, program_slug: 'summer-2026' } },
    );

    expect(addActionMock).toHaveBeenCalledWith('user_login', { method: 'password' });
    expect(addActionMock).toHaveBeenCalledWith('reflection_submitted', {
      reflectionId: 9,
      templateId: 3,
      programSlug: 'summer-2026',
    });
  });
});
