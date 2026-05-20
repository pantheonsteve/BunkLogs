import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

vi.mock('../../api', () => ({
  default: { get: vi.fn() },
}));

import api from '../../api';
import useSupervision, {
  SUPERVISIONS_PATH,
  SUPERVISION_TARGET_TYPES,
} from '../useSupervision';

beforeEach(() => {
  api.get.mockReset();
});

describe('useSupervision', () => {
  it('auto-loads the supervisions list with no filters', async () => {
    api.get.mockResolvedValue({ data: [{ id: 1 }, { id: 2 }] });
    const { result } = renderHook(() => useSupervision());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(api.get).toHaveBeenCalledWith(SUPERVISIONS_PATH, { params: {} });
    expect(result.current.supervisions).toEqual([{ id: 1 }, { id: 2 }]);
    expect(result.current.error).toBeNull();
  });

  it('passes supervisorMembershipId through as supervisor_membership_id', async () => {
    api.get.mockResolvedValue({ data: { results: [{ id: 7 }] } });
    const { result } = renderHook(() =>
      useSupervision({ supervisorMembershipId: 42 }),
    );
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(api.get).toHaveBeenCalledWith(SUPERVISIONS_PATH, {
      params: { supervisor_membership_id: 42 },
    });
    expect(result.current.supervisions).toEqual([{ id: 7 }]);
  });

  it('passes target_type and is_active filters', async () => {
    api.get.mockResolvedValue({ data: [] });
    renderHook(() =>
      useSupervision({
        targetType: SUPERVISION_TARGET_TYPES.BUNK,
        isActive: true,
      }),
    );
    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(api.get).toHaveBeenCalledWith(SUPERVISIONS_PATH, {
      params: { target_type: 'bunk', is_active: 'true' },
    });
  });

  it('does not auto-load when autoLoad is false', async () => {
    api.get.mockResolvedValue({ data: [] });
    const { result } = renderHook(() => useSupervision({ autoLoad: false }));
    expect(result.current.isLoading).toBe(false);
    expect(api.get).not.toHaveBeenCalled();
    await act(async () => {
      await result.current.refetch();
    });
    expect(api.get).toHaveBeenCalledTimes(1);
  });

  it('surfaces fetch errors', async () => {
    const failure = new Error('boom');
    api.get.mockRejectedValue(failure);
    const { result } = renderHook(() => useSupervision());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBe(failure);
    expect(result.current.supervisions).toEqual([]);
  });

  it('refetch re-issues the request with current filters', async () => {
    api.get.mockResolvedValue({ data: [] });
    const { result } = renderHook(() =>
      useSupervision({ supervisorMembershipId: 9 }),
    );
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    api.get.mockClear();
    api.get.mockResolvedValue({ data: [{ id: 99 }] });
    await act(async () => {
      await result.current.refetch();
    });
    expect(api.get).toHaveBeenCalledWith(SUPERVISIONS_PATH, {
      params: { supervisor_membership_id: 9 },
    });
    expect(result.current.supervisions).toEqual([{ id: 99 }]);
  });
});
