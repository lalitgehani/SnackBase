/**
 * Lazy-bound service exports for legacy module-level function imports.
 * Resolves the instance client on each call, not when properties are read.
 */
import type { SnackBaseClient } from '@snackbase/sdk';
import { getInstanceClient } from './instanceClientRef';

export function bindService<T extends object>(
  factory: (client: SnackBaseClient) => T,
): T {
  return new Proxy({} as T, {
    get(_target, prop) {
      if (typeof prop !== 'string') {
        return undefined;
      }
      return (...args: unknown[]) => {
        const service = factory(getInstanceClient());
        const value = service[prop as keyof T];
        if (typeof value === 'function') {
          return (value as (...a: unknown[]) => unknown).apply(service, args);
        }
        return value;
      };
    },
  });
}
