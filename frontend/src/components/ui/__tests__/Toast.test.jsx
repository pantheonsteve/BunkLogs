import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, renderHook, act, screen } from '@testing-library/react';

import Toast, { useToast } from '../Toast';

describe('Toast component (3.31)', () => {
  it('renders nothing when message is empty', () => {
    const { container } = render(<Toast message="" />);
    expect(container.firstChild).toBeNull();
  });

  it('renders the pill when message is non-empty', () => {
    render(<Toast message="Saved!" data-testid="my-toast" />);
    const node = screen.getByTestId('my-toast');
    expect(node).toHaveTextContent('Saved!');
    expect(node).toHaveAttribute('role', 'status');
    expect(node.className).toContain('fixed');
    expect(node.className).toContain('rounded-full');
  });
});

describe('useToast hook (3.31)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts with an empty toast and stores a message on showToast', () => {
    const { result } = renderHook(() => useToast());
    expect(result.current.toast).toBe('');
    act(() => result.current.showToast('Hello'));
    expect(result.current.toast).toBe('Hello');
  });

  it('auto-clears after the default 4000 ms timeout', () => {
    const { result } = renderHook(() => useToast());
    act(() => result.current.showToast('Bye'));
    expect(result.current.toast).toBe('Bye');
    act(() => {
      vi.advanceTimersByTime(4000);
    });
    expect(result.current.toast).toBe('');
  });

  it('honors a custom duration', () => {
    const { result } = renderHook(() => useToast(1000));
    act(() => result.current.showToast('Quick'));
    act(() => {
      vi.advanceTimersByTime(999);
    });
    expect(result.current.toast).toBe('Quick');
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current.toast).toBe('');
  });

  it('clearToast cancels the pending timeout', () => {
    const { result } = renderHook(() => useToast());
    act(() => result.current.showToast('Cancel me'));
    act(() => result.current.clearToast());
    expect(result.current.toast).toBe('');
  });

  it('subsequent showToast resets the timer', () => {
    const { result } = renderHook(() => useToast(2000));
    act(() => result.current.showToast('A'));
    act(() => {
      vi.advanceTimersByTime(1500);
    });
    act(() => result.current.showToast('B'));
    act(() => {
      vi.advanceTimersByTime(1500);
    });
    expect(result.current.toast).toBe('B');
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(result.current.toast).toBe('');
  });
});
