import { useCallback } from 'react';
import { useSnackBase } from '@snackbase/react';
import { CONTROL_PLANE_AUTH_STORAGE_KEY } from '@/lib/snackbase/constants';

/**
 * Read the persisted control-plane token straight out of storage.
 *
 * `SnackBaseClient`'s constructor kicks off `authManager.initialize()` without awaiting it,
 * so `authManager.token` is null for the first tick after a full page load while the async
 * hydrate resolves. Anything that renders in that window — the cold-start probe, every
 * Studio query — would otherwise send a request with no Authorization header, and the
 * platform gateway answers those with 401 `Authorization Bearer token required`.
 *
 * Client-side navigation never hits this because hydration finished long before; it only
 * shows up on refresh or when a Studio URL is opened directly.
 */
function persistedControlPlaneToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(CONTROL_PLANE_AUTH_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { token?: unknown };
    return typeof parsed.token === 'string' && parsed.token ? parsed.token : null;
  } catch {
    return null;
  }
}

/**
 * Bridge control-plane session token to InstanceClientProvider (F4.4).
 *
 * The AuthManager is authoritative once hydrated; storage is only consulted to cover the
 * hydration window described above.
 */
export function useControlPlaneAccessToken(): () => string | null {
  const client = useSnackBase();

  return useCallback(
    () => client.internalAuthManager.token ?? persistedControlPlaneToken(),
    [client],
  );
}
