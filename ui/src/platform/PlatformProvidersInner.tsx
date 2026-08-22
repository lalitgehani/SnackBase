import type { ReactNode } from 'react';
import { SnackBaseProvider } from '@snackbase/react';
import { controlPlaneClient } from '@/lib/control-plane/client';

export function PlatformProvidersInner({ children }: { children: ReactNode }) {
  return <SnackBaseProvider client={controlPlaneClient}>{children}</SnackBaseProvider>;
}
