import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { rememberProjectRef, studioPath } from '@/lib/platform/studioPath';

interface StudioBasePathContextValue {
  ref: string;
  basePath: string;
  toStudioPath: (adminPath: string) => string;
}

const StudioBasePathContext = createContext<StudioBasePathContextValue | null>(null);

export interface StudioBasePathProviderProps {
  envRef: string;
  children: ReactNode;
}

export function StudioBasePathProvider({ envRef, children }: StudioBasePathProviderProps) {
  const value = useMemo<StudioBasePathContextValue>(() => {
    rememberProjectRef(envRef);
    return {
      ref: envRef,
      basePath: `/project/${envRef}`,
      toStudioPath: (adminPath: string) => studioPath(adminPath, envRef),
    };
  }, [envRef]);

  return (
    <StudioBasePathContext.Provider value={value}>{children}</StudioBasePathContext.Provider>
  );
}

export function useStudioBasePath(): StudioBasePathContextValue | null {
  return useContext(StudioBasePathContext);
}

export function useStudioNavUrl(adminPath: string): string {
  const ctx = useStudioBasePath();
  return ctx ? ctx.toStudioPath(adminPath) : adminPath;
}
