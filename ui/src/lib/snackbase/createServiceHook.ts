import { useMemo } from 'react';
import type { SnackBaseClient } from '@snackbase/sdk';
import { useInstanceClient } from './InstanceClientProvider';

/**
 * Factory for instance-scoped service hooks.
 */
export function createServiceHook<T>(factory: (client: SnackBaseClient) => T) {
  return function useService(): T {
    const client = useInstanceClient();
    return useMemo(() => factory(client), [client]);
  };
}
