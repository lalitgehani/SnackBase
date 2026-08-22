import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { Loader2, RefreshCw } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useSnackBase } from '@snackbase/react';
import { Button } from '@/components/ui/button';
import { EnvironmentStatusBadge } from '@/components/platform/EnvironmentStatusBadge';
import { platformBaseUrl } from '@/lib/config';
import { useControlPlaneAccessToken } from '@/lib/platform/useControlPlaneAccessToken';
import type { Environment, EnvironmentStatus } from '@/types/control-plane';

const SUPPRESS_MS = 400;
const MAX_WAIT_MS = 180_000;
const DEFAULT_RETRY_MS = 2_000;

type ProxyState = 'ready' | 'waking' | 'unavailable';

interface PlatformStatusResponse {
  state: ProxyState;
  retry_after_ms?: number;
}

const TERMINAL_CP_STATUSES: EnvironmentStatus[] = ['failed', 'deleting', 'deleted'];

async function fetchPlatformStatus(
  ref: string,
  getAccessToken: () => string | null,
): Promise<PlatformStatusResponse> {
  const token = getAccessToken();
  const url = `${platformBaseUrl(ref)}/_platform/status`;
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (res.status === 401) {
    window.location.href = `/login?returnTo=${encodeURIComponent(window.location.pathname)}`;
    throw new Error('Session expired');
  }

  if (res.status === 403) {
    throw new AccessDeniedError();
  }

  if (!res.ok) {
    return { state: 'unavailable' };
  }

  return (await res.json()) as PlatformStatusResponse;
}

export class AccessDeniedError extends Error {
  constructor() {
    super('Access denied');
    this.name = 'AccessDeniedError';
  }
}

export interface EnvironmentColdStartGateProps {
  ref: string;
  children: ReactNode;
}

export function EnvironmentColdStartGate({ ref, children }: EnvironmentColdStartGateProps) {
  const client = useSnackBase();
  const getAccessToken = useControlPlaneAccessToken();
  const [showStarting, setShowStarting] = useState(false);
  const [timedOut, setTimedOut] = useState(false);
  const startedAt = useRef(0);
  const suppressTimer = useRef<number | null>(null);

  const { data: environment, isLoading: envLoading } = useQuery({
    queryKey: ['platform-environment', ref],
    queryFn: async () => {
      const res = await client.records.list<Environment>('environments', {
        filter: `slug = "${ref}" OR id = "${ref}"`,
        limit: 1,
      });
      return res.items[0] ?? null;
    },
  });

  const {
    data: status,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['platform-status', ref],
    queryFn: () => fetchPlatformStatus(ref, getAccessToken),
    enabled: Boolean(environment && environment.tenancy_mode !== 'multi'),
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      if (state === 'ready') return false;
      if (Date.now() - startedAt.current >= MAX_WAIT_MS) return false;
      return query.state.data?.retry_after_ms ?? DEFAULT_RETRY_MS;
    },
    retry: false,
  });

  useEffect(() => {
    startedAt.current = Date.now();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset cold-start UI when env ref changes
    setTimedOut(false);
    setShowStarting(false);
    if (suppressTimer.current) window.clearTimeout(suppressTimer.current);
    suppressTimer.current = window.setTimeout(() => setShowStarting(true), SUPPRESS_MS);
    return () => {
      if (suppressTimer.current) window.clearTimeout(suppressTimer.current);
    };
  }, [ref]);

  useEffect(() => {
    if (status?.state === 'ready') {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- clear transient cold-start state when proxy is ready
      setShowStarting(false);
      setTimedOut(false);
      return;
    }
    if (Date.now() - startedAt.current >= MAX_WAIT_MS && status?.state === 'waking') {
      setTimedOut(true);
    }
  }, [status]);

  const handleRetry = useCallback(() => {
    startedAt.current = Date.now();
    setTimedOut(false);
    void refetch();
  }, [refetch]);

  if (envLoading) {
    return <GateShell message="Loading environment…" />;
  }

  if (!environment) {
    return (
      <GateShell
        title="Environment not found"
        message="This environment does not exist or you do not have access."
        action={
          <Button asChild variant="outline">
            <Link to="/organizations">Back to organizations</Link>
          </Button>
        }
      />
    );
  }

  if (environment.tenancy_mode === 'multi') {
    return (
      <GateShell
        title="Integrated Studio unavailable"
        message="Multi-tenant environments use a dedicated instance URL. The integrated Studio is available for single-tenant projects."
        action={
          environment.instance_url ? (
            <Button asChild>
              <a href={environment.instance_url} target="_blank" rel="noreferrer">
                Open instance URL
              </a>
            </Button>
          ) : (
            <Button asChild variant="outline">
              <Link to="/organizations">Back to organizations</Link>
            </Button>
          )
        }
        testId="multi-tenant-explanation"
      />
    );
  }

  if (environment.status === 'pending' || environment.status === 'provisioning') {
    return (
      <GateShell
        title="Environment provisioning"
        message="This environment is still being provisioned. It will become available automatically."
        badge={<EnvironmentStatusBadge status={environment.status} />}
      />
    );
  }

  if (environment.status === 'failed') {
    return (
      <GateShell
        title="Provisioning failed"
        message={environment.error_message ?? 'Provisioning failed. Try again from the environments page.'}
        badge={<EnvironmentStatusBadge status={environment.status} />}
        action={
          <Button asChild variant="outline">
            <Link to="/organizations">View environments</Link>
          </Button>
        }
      />
    );
  }

  if (TERMINAL_CP_STATUSES.includes(environment.status)) {
    return (
      <GateShell
        title="Environment unavailable"
        message={
          environment.status === 'deleted'
            ? 'This environment has been deleted.'
            : 'This environment is being removed.'
        }
        badge={<EnvironmentStatusBadge status={environment.status} />}
      />
    );
  }

  if (error instanceof AccessDeniedError) {
    return (
      <GateShell
        title="Access denied"
        message="You no longer have access to this environment."
        action={
          <Button asChild variant="outline">
            <Link to="/organizations">Back to projects</Link>
          </Button>
        }
        testId="access-denied"
      />
    );
  }

  if (status?.state === 'ready') {
    return <>{children}</>;
  }

  if (timedOut || status?.state === 'unavailable' || isError) {
    return (
      <GateShell
        title="Could not start environment"
        message="The environment did not become ready in time. You can retry or return to the environments list."
        action={
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={handleRetry} disabled={isFetching}>
              <RefreshCw className="mr-2 size-4" />
              Retry
            </Button>
            <Button asChild variant="outline">
              <Link to="/organizations">View environments</Link>
            </Button>
          </div>
        }
        testId="cold-start-error"
      />
    );
  }

  if (showStarting && status?.state === 'waking') {
    return (
      <GateShell
        title="Starting environment"
        message="This project was idle and is waking up. This usually takes a moment."
        spinner
        testId="cold-start-waking"
      />
    );
  }

  return <GateShell message="Connecting…" spinner />;
}

function GateShell({
  title,
  message,
  spinner,
  badge,
  action,
  testId,
}: {
  title?: string;
  message: string;
  spinner?: boolean;
  badge?: ReactNode;
  action?: ReactNode;
  testId?: string;
}) {
  return (
    <div
      className="flex min-h-[50vh] flex-col items-center justify-center gap-4 p-8 text-center"
      data-testid={testId}
    >
      {spinner && <Loader2 className="size-10 animate-spin text-primary" aria-hidden />}
      {badge}
      {title && <h2 className="text-xl font-semibold">{title}</h2>}
      <p className="max-w-md text-muted-foreground">{message}</p>
      {action}
    </div>
  );
}
