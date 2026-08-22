/**
 * Non-hook access to the active instance client (e.g. Zustand auth store).
 * Set by InstanceClientProvider; cleared on unmount.
 */

import type { SnackBaseClient } from '@snackbase/sdk';
import { InstanceClientProviderError } from './InstanceClientProvider';

let activeClient: SnackBaseClient | null = null;

export function setInstanceClient(client: SnackBaseClient | null): void {
  activeClient = client;
}

export function getInstanceClient(): SnackBaseClient {
  if (!activeClient) {
    throw new InstanceClientProviderError(
      'No instance client available. Ensure InstanceClientProvider is mounted.',
    );
  }
  return activeClient;
}

/** Test helper — bypasses provider requirement. */
export function setInstanceClientForTests(client: SnackBaseClient | null): void {
  activeClient = client;
}
