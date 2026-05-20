import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

vi.mock('../../api', () => ({
  default: { post: vi.fn() },
}));

import api from '../../api';
import useOrderStateMachine, {
  ORDER_STATES,
  isWithinCorrectionWindow,
} from '../useOrderStateMachine';

beforeEach(() => {
  api.post.mockReset();
});

describe('isWithinCorrectionWindow', () => {
  it('returns true within 5 minutes', () => {
    const now = new Date('2026-06-01T12:05:00Z');
    expect(
      isWithinCorrectionWindow('2026-06-01T12:00:00Z', { now }),
    ).toBe(true);
  });

  it('returns true exactly at the boundary', () => {
    const now = new Date('2026-06-01T12:05:00Z');
    expect(
      isWithinCorrectionWindow('2026-06-01T12:00:00Z', { now }),
    ).toBe(true);
  });

  it('returns false past 5 minutes', () => {
    const now = new Date('2026-06-01T12:05:01Z');
    expect(
      isWithinCorrectionWindow('2026-06-01T12:00:00Z', { now }),
    ).toBe(false);
  });

  it('returns false for null', () => {
    expect(isWithinCorrectionWindow(null)).toBe(false);
    expect(isWithinCorrectionWindow(undefined)).toBe(false);
  });
});

describe('useOrderStateMachine', () => {
  it('exposes available transitions derived from status', () => {
    const { result } = renderHook(() =>
      useOrderStateMachine({ contentType: 'order', status: ORDER_STATES.NEW }),
    );
    expect(result.current.availableTransitions).toEqual(
      [
        ORDER_STATES.FULFILLED,
        ORDER_STATES.IN_PROGRESS,
        ORDER_STATES.UNABLE_TO_FULFILL,
      ].sort(),
    );
  });

  it('prefers explicit availableTransitions when provided', () => {
    const { result } = renderHook(() =>
      useOrderStateMachine({
        contentType: 'order',
        status: ORDER_STATES.NEW,
        availableTransitions: ['fulfilled'],
      }),
    );
    expect(result.current.availableTransitions).toEqual(['fulfilled']);
  });

  it('returns empty transitions for unknown status', () => {
    const { result } = renderHook(() =>
      useOrderStateMachine({ contentType: 'order', status: 'mystery' }),
    );
    expect(result.current.availableTransitions).toEqual([]);
  });

  it('posts to the order transition endpoint', async () => {
    api.post.mockResolvedValue({ data: { content: { status: 'in_progress' }, activity: [] } });
    const { result } = renderHook(() =>
      useOrderStateMachine({
        contentType: 'order',
        contentId: '4f7d',
        status: ORDER_STATES.NEW,
      }),
    );
    await act(async () => {
      await result.current.transitionTo(ORDER_STATES.IN_PROGRESS, { note: 'go' });
    });
    expect(api.post).toHaveBeenCalledWith('/api/v1/orders/4f7d/transition/', {
      to_state: 'in_progress',
      note: 'go',
      reason: '',
    });
  });

  it('posts to the maintenance transition endpoint', async () => {
    api.post.mockResolvedValue({ data: {} });
    const { result } = renderHook(() =>
      useOrderStateMachine({
        contentType: 'maintenance_ticket',
        contentId: 'tk-1',
        status: ORDER_STATES.IN_PROGRESS,
      }),
    );
    await act(async () => {
      await result.current.transitionTo(ORDER_STATES.UNABLE_TO_FULFILL, {
        reason: 'specialty contractor required',
      });
    });
    expect(api.post).toHaveBeenCalledWith(
      '/api/v1/maintenance/tk-1/transition/',
      {
        to_state: 'unable_to_fulfill',
        note: '',
        reason: 'specialty contractor required',
      },
    );
  });

  it('posts to the correct-last endpoint', async () => {
    api.post.mockResolvedValue({ data: {} });
    const { result } = renderHook(() =>
      useOrderStateMachine({ contentType: 'order', contentId: 'o-1' }),
    );
    await act(async () => {
      await result.current.correctLast();
    });
    expect(api.post).toHaveBeenCalledWith(
      '/api/v1/orders/o-1/correct-last/',
      {},
    );
  });

  it('rejects transitionTo without contentId', async () => {
    const { result } = renderHook(() =>
      useOrderStateMachine({ contentType: 'order' }),
    );
    await expect(result.current.transitionTo('in_progress')).rejects.toThrow(
      /contentId required/,
    );
  });

  it('posts bulk transitions', async () => {
    api.post.mockResolvedValue({ data: { transitioned: [] } });
    const { result } = renderHook(() =>
      useOrderStateMachine({ contentType: 'order' }),
    );
    await act(async () => {
      await result.current.bulkTransition(['a', 'b', 'c'], 'fulfilled', {
        note: 'walked over together',
      });
    });
    expect(api.post).toHaveBeenCalledWith('/api/v1/orders/bulk-transition/', {
      ids: ['a', 'b', 'c'],
      to_state: 'fulfilled',
      note: 'walked over together',
      reason: '',
    });
  });
});
