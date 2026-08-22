import { Navigate, useLocation, useParams } from 'react-router';
import { InstanceClientProvider } from '@/lib/snackbase/InstanceClientProvider';
import { StudioBasePathProvider } from '@/lib/platform/StudioBasePathContext';
import { useControlPlaneAccessToken } from '@/lib/platform/useControlPlaneAccessToken';
import { EnvironmentColdStartGate } from '@/components/platform/EnvironmentColdStartGate';
import { getLastProjectRef, adminSuffix } from '@/lib/platform/studioPath';
import type { ReactNode } from 'react';

export interface ProjectStudioRootProps {
  children: ReactNode;
}

/** Wraps /project/:ref/* with session bridge and cold-start gate (F4.4, F4.5). */
export function ProjectStudioRoot({ children }: ProjectStudioRootProps) {
  const { ref } = useParams<{ ref: string }>();
  const getAccessToken = useControlPlaneAccessToken();

  if (!ref) {
    return <Navigate to="/organizations" replace />;
  }

  return (
    <StudioBasePathProvider envRef={ref}>
      <EnvironmentColdStartGate ref={ref}>
        <InstanceClientProvider envRef={ref} getAccessToken={getAccessToken}>
          {children}
        </InstanceClientProvider>
      </EnvironmentColdStartGate>
    </StudioBasePathProvider>
  );
}

/** Redirect legacy /admin/* navigations to /project/{ref}/* in platform mode. */
export function PlatformAdminRedirect() {
  const location = useLocation();
  const ref = getLastProjectRef();
  if (!ref) {
    return <Navigate to="/organizations" replace />;
  }
  const suffix = adminSuffix(location.pathname);
  return (
    <Navigate
      to={`/project/${ref}${suffix}${location.search}${location.hash}`}
      replace
    />
  );
}
