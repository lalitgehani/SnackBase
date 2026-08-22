import { useCallback } from 'react';
import { useSnackBase } from '@snackbase/react';

/**
 * Bridge control-plane session token to InstanceClientProvider (F4.4).
 */
export function useControlPlaneAccessToken(): () => string | null {
  const client = useSnackBase();

  return useCallback(() => client.internalAuthManager.token, [client]);
}
