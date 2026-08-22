import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useControlPlaneAccessToken } from './useControlPlaneAccessToken';
import { CONTROL_PLANE_AUTH_STORAGE_KEY } from '@/lib/snackbase/constants';

const authManager = { token: null as string | null };

vi.mock('@snackbase/react', () => ({
  useSnackBase: () => ({ internalAuthManager: authManager }),
}));

describe('useControlPlaneAccessToken', () => {
  beforeEach(() => {
    authManager.token = null;
    window.localStorage.clear();
  });

  it('returns the hydrated AuthManager token when available', () => {
    authManager.token = 'live-token';
    window.localStorage.setItem(
      CONTROL_PLANE_AUTH_STORAGE_KEY,
      JSON.stringify({ token: 'stale-token' }),
    );
    const { result } = renderHook(() => useControlPlaneAccessToken());
    expect(result.current()).toBe('live-token');
  });

  it('falls back to the persisted token while the AuthManager is still hydrating', () => {
    // SnackBaseClient starts authManager.initialize() without awaiting it, so on a full
    // page load the token is null for a tick. Requests firing in that window previously
    // reached the platform gateway with no Authorization header and got a 401.
    authManager.token = null;
    window.localStorage.setItem(
      CONTROL_PLANE_AUTH_STORAGE_KEY,
      JSON.stringify({ token: 'persisted-token', user: { id: 'u1' } }),
    );
    const { result } = renderHook(() => useControlPlaneAccessToken());
    expect(result.current()).toBe('persisted-token');
  });

  it('returns null when there is no session anywhere', () => {
    const { result } = renderHook(() => useControlPlaneAccessToken());
    expect(result.current()).toBeNull();
  });

  it('returns null on corrupt or tokenless stored state instead of throwing', () => {
    window.localStorage.setItem(CONTROL_PLANE_AUTH_STORAGE_KEY, 'not-json');
    const { result } = renderHook(() => useControlPlaneAccessToken());
    expect(result.current()).toBeNull();

    window.localStorage.setItem(CONTROL_PLANE_AUTH_STORAGE_KEY, JSON.stringify({ user: {} }));
    expect(result.current()).toBeNull();
  });
});
