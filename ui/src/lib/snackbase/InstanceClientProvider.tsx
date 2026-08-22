/**
 * Instance-scoped SnackBase SDK client for the admin Studio.
 *
 * Nesting order (platform mode):
 *   SnackBaseProvider (@snackbase/react, control-plane) wraps InstanceClientProvider
 *   because getAccessToken reads the control-plane session via useSnackBase().
 *
 * Self-host mode: only InstanceClientProvider is mounted; the client owns its session.
 */

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from 'react';
import { SnackBaseClient } from '@snackbase/sdk';
import { IS_PLATFORM, loadConfig, platformBaseUrl } from '@/lib/config';
import { setInstanceClient } from '@/lib/snackbase/instanceClientRef';
import { AUTH_STORAGE_KEY } from '@/lib/snackbase/constants';

export const InstanceClientContext = createContext<SnackBaseClient | null>(null);

export class InstanceClientProviderError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'InstanceClientProviderError';
  }
}

export interface InstanceClientProviderProps {
  children: ReactNode;
  /** Environment ref for platform-mode proxied instance access */
  envRef?: string;
  /** Control-plane session token (platform mode only) */
  getAccessToken?: () => string | null;
}

function redirectToLogin(): void {
  if (typeof window === 'undefined') return;
  if (IS_PLATFORM) {
    if (!window.location.pathname.startsWith('/login')) {
      const returnTo = encodeURIComponent(
        `${window.location.pathname}${window.location.search}`,
      );
      window.location.href = `/login?returnTo=${returnTo}`;
    }
    return;
  }
  if (!window.location.pathname.startsWith('/admin/login')) {
    window.location.href = '/admin/login';
  }
}

export function InstanceClientProvider({
  children,
  envRef,
  getAccessToken,
}: InstanceClientProviderProps) {
  const previousClientRef = useRef<SnackBaseClient | null>(null);

  const baseUrl = useMemo(() => {
    const config = loadConfig();
    if (IS_PLATFORM) {
      if (!envRef) {
        throw new InstanceClientProviderError(
          'InstanceClientProvider requires ref in platform mode',
        );
      }
      return platformBaseUrl(envRef, config);
    }
    return config.apiBaseUrl;
  }, [envRef]);

  const client = useMemo(() => {
    if (IS_PLATFORM) {
      if (!getAccessToken) {
        throw new InstanceClientProviderError(
          'InstanceClientProvider requires getAccessToken in platform mode',
        );
      }
      return new SnackBaseClient({
        baseUrl,
        getAccessToken,
        storageBackend: 'memory',
        onAuthError: redirectToLogin,
      });
    }

    return new SnackBaseClient({
      baseUrl,
      storageBackend: 'localStorage',
      authStorageKey: AUTH_STORAGE_KEY,
      defaultAccount: 'SY0000',
      onAuthError: redirectToLogin,
    });
  }, [baseUrl, getAccessToken]);

  useEffect(() => {
    setInstanceClient(client);
    return () => {
      setInstanceClient(null);
    };
  }, [client]);

  useEffect(() => {
    const previous = previousClientRef.current;
    if (previous && previous !== client) {
      previous.realtime.disconnect();
    }
    previousClientRef.current = client;
  }, [client]);

  useEffect(() => {
    return () => {
      client.realtime.disconnect();
    };
  }, [client]);

  return (
    <InstanceClientContext.Provider value={client}>{children}</InstanceClientContext.Provider>
  );
}

export function useInstanceClient(): SnackBaseClient {
  const client = useContext(InstanceClientContext);
  if (!client) {
    throw new InstanceClientProviderError(
      'useInstanceClient must be used within an InstanceClientProvider',
    );
  }
  return client;
}
