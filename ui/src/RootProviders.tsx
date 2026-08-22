import { lazy, Suspense, type ReactNode } from 'react';
import { IS_PLATFORM } from '@/lib/config';
import { PlatformProvidersInner } from '@/platform/PlatformProvidersInner';

export function RootProviders({ children }: { children: ReactNode }) {
  if (IS_PLATFORM) {
    return <PlatformProvidersInner>{children}</PlatformProvidersInner>;
  }
  return children;
}
