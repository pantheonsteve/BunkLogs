import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

vi.mock('../../api', () => ({
  default: { get: vi.fn() },
}));

import api from '../../api';
import useAuditTrail, { AUDIT_BASE_PATH } from '../useAuditTrail';

beforeEach(() => {
  api.get.mockReset();
});

describe('useAuditTrail', () => {
  it('fetches by-content events when contentType + contentId are set', async () => {
    api.get.mockResolvedValue({ data: [{ id: '1', event_type: 'created' }] });
    const { result } = renderHook(() =>
      useAuditTrail({ contentType: 'order', contentId: 'abc-123' }),
    );
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(api.get).toHaveBeenCalledWith(AUDIT_BASE_PATH, {
      params: { content_type: 'order', content_id: 'abc-123' },
    });
    expect(result.current.events).toHaveLength(1);
  });

  it('does not fetch when by-content params are incomplete', async () => {
    api.get.mockResolvedValue({ data: [] });
    const { result } = renderHook(() =>
      useAuditTrail({ contentType: 'order' }),
    );
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(api.get).not.toHaveBeenCalled();
    expect(result.current.events).toEqual([]);
  });

  it('fetches by-actor events with membership_id', async () => {
    api.get.mockResolvedValue({ data: { results: [{ id: '2' }] } });
    const { result } = renderHook(() =>
      useAuditTrail({ mode: 'by-actor', membershipId: 42 }),
    );
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(api.get).toHaveBeenCalledWith(`${AUDIT_BASE_PATH}by-actor/`, {
      params: { membership_id: 42 },
    });
    expect(result.current.events).toEqual([{ id: '2' }]);
  });

  it('fetches admin overrides with optional since filter', async () => {
    api.get.mockResolvedValue({ data: [] });
    renderHook(() =>
      useAuditTrail({ mode: 'admin-overrides', since: '2026-05-01' }),
    );
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(api.get).toHaveBeenCalledWith(`${AUDIT_BASE_PATH}admin-overrides/`, {
      params: { since: '2026-05-01' },
    });
  });

  it('surfaces fetch errors', async () => {
    const failure = new Error('boom');
    api.get.mockRejectedValue(failure);
    const { result } = renderHook(() =>
      useAuditTrail({ contentType: 'order', contentId: 'abc' }),
    );
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBe(failure);
    expect(result.current.events).toEqual([]);
  });

  it('refetch re-issues the request', async () => {
    api.get.mockResolvedValue({ data: [] });
    const { result } = renderHook(() =>
      useAuditTrail({ contentType: 'order', contentId: 'abc' }),
    );
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    api.get.mockClear();
    api.get.mockResolvedValue({ data: [{ id: '7' }] });
    await act(async () => {
      await result.current.refetch();
    });
    expect(api.get).toHaveBeenCalledWith(AUDIT_BASE_PATH, {
      params: { content_type: 'order', content_id: 'abc' },
    });
    expect(result.current.events).toEqual([{ id: '7' }]);
  });
});
