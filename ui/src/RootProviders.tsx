import { lazy, Suspense, type ReactNode } from 'react';
import { IS_PLATFORM } from '@/lib/config';

const PlatformProvidersLazy = IS_PLATFORM
  ? lazy(() =>
      import('@/platform/PlatformProvidersInner').then((m) => ({
        default: m.PlatformProvidersInner,
      })),
    )
  : null;

export function RootProviders({ children }: { children: ReactNode }) {
  if (PlatformProvidersLazy) {
    return (
      <Suspense fallback={null}>
        <PlatformProvidersLazy>{children}</PlatformProvidersLazy>
      </Suspense>
    );
  }
  return children;
}
