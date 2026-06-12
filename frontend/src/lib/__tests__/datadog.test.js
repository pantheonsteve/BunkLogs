import { describe, it, expect, vi, beforeEach } from 'vitest';

const initRumMock = vi.fn();
const initLogsMock = vi.fn();
const setUserMock = vi.fn();
const clearUserMock = vi.fn();
const addActionMock = vi.fn();
const startViewMock = vi.fn();
const getInternalContextMock = vi.fn(() => ({ session_id: 'sess-1' }));
const logsLoggerMock = {
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
};

vi.mock('@datadog/browser-rum', () => ({
  datadogRum: {
    init: initRumMock,
    setUser: setUserMock,
    clearUser: clearUserMock,
    addAction: addActionMock,
    startView: startViewMock,
    getInternalContext: getInternalContextMock,
    setGlobalContextProperty: vi.fn(),
    removeGlobalContextProperty: vi.fn(),
  },
}));

vi.mock('@datadog/browser-logs', () => ({
  datadogLogs: {
    init: initLogsMock,
    logger: logsLoggerMock,
  },
}));

vi.mock('@datadog/browser-rum-react', () => ({
  reactPlugin: vi.fn(() => ({})),
}));

describe('datadog helpers', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
    initRumMock.mockClear();
    initLogsMock.mockClear();
    setUserMock.mockClear();
    clearUserMock.mockClear();
    addActionMock.mockClear();
    startViewMock.mockClear();
    logsLoggerMock.info.mockClear();
  });

  it('does not initialize without credentials', async () => {
    vi.stubEnv('VITE_DATADOG_APPLICATION_ID', '');
    vi.stubEnv('VITE_DATADOG_CLIENT_TOKEN', '');
    vi.stubEnv('VITE_DATADOG_FORCE_ENABLE', 'false');

    const { initDatadogRum, isDatadogRumEnabled, isDatadogLogsEnabled } = await import('../datadog');
    initDatadogRum();
    expect(initRumMock).not.toHaveBeenCalled();
    expect(initLogsMock).not.toHaveBeenCalled();
    expect(isDatadogRumEnabled()).toBe(false);
    expect(isDatadogLogsEnabled()).toBe(false);
  });

  it('initializes RUM and Logs with matching config when enabled', async () => {
    vi.stubEnv('VITE_DATADOG_APPLICATION_ID', 'app-id');
    vi.stubEnv('VITE_DATADOG_CLIENT_TOKEN', 'client-token');
    vi.stubEnv('VITE_DATADOG_FORCE_ENABLE', 'true');
    vi.stubEnv('VITE_DATADOG_ENV', 'prod');
    vi.stubEnv('VITE_DATADOG_SERVICE', 'bunklogs-frontend');
    vi.stubEnv('VITE_DATADOG_VERSION', '1.2.3');
    vi.stubEnv('PROD', '');

    const { initDatadogRum, isDatadogRumEnabled, isDatadogLogsEnabled } = await import('../datadog');
    initDatadogRum();

    expect(initRumMock).toHaveBeenCalledTimes(1);
    expect(initLogsMock).toHaveBeenCalledTimes(1);
    expect(isDatadogRumEnabled()).toBe(true);
    expect(isDatadogLogsEnabled()).toBe(true);

    const logsConfig = initLogsMock.mock.calls[0][0];
    expect(logsConfig.env).toBe('prod');
    expect(logsConfig.service).toBe('bunklogs-frontend');
    expect(logsConfig.version).toBe('1.2.3');
    expect(logsConfig.forwardErrorsToLogs).toBe(true);
    expect(logsConfig.forwardConsoleLogs).toEqual(['error', 'warn']);
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

  it('writes structured logs when Logs SDK is initialized', async () => {
    vi.stubEnv('VITE_DATADOG_APPLICATION_ID', 'app-id');
    vi.stubEnv('VITE_DATADOG_CLIENT_TOKEN', 'client-token');
    vi.stubEnv('VITE_DATADOG_FORCE_ENABLE', 'true');
    vi.stubEnv('PROD', '');

    const { initDatadogRum, logToDatadog } = await import('../datadog');
    initDatadogRum();
    logToDatadog('info', 'reflection saved', { reflectionId: 1 });

    expect(logsLoggerMock.info).toHaveBeenCalledWith('reflection saved', { reflectionId: 1 });
  });
});
