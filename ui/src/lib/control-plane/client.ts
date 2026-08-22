import { SnackBaseClient } from '@snackbase/sdk';
import { loadConfig } from '@/lib/config';

let memoizedClient: SnackBaseClient | null = null;

/**
 * Singleton control-plane client for platform mode.
 * Auth tokens are managed by the SDK AuthManager / interceptors.
 */
export function getControlPlaneClient(): SnackBaseClient {
  if (!memoizedClient) {
    const { snackbaseUrl } = loadConfig();
    memoizedClient = new SnackBaseClient({
      baseUrl: snackbaseUrl,
    });
  }
  return memoizedClient;
}

/** @internal Test-only reset */
export function resetControlPlaneClientForTests(): void {
  memoizedClient = null;
}

/** Stable export for SnackBaseProvider */
export const controlPlaneClient = getControlPlaneClient();
