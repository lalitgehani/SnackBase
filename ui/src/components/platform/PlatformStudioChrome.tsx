import { Link, useLocation, useParams } from 'react-router';
import { ChevronRight } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useSnackBase } from '@snackbase/react';
import { EnvironmentStatusBadge } from '@/components/platform/EnvironmentStatusBadge';
import { environmentRefLookupFilter, environmentRouteRef } from '@/lib/control-plane/env-ref';
import { normalizeToAdminPath } from '@/lib/platform/studioPath';
import type { Environment, Organization, Project } from '@/types/control-plane';

/** Environment breadcrumb and switcher shown above Studio pages in platform mode (F4.3). */
export function PlatformStudioChrome() {
  const { ref } = useParams<{ ref: string }>();
  const location = useLocation();
  const client = useSnackBase();
  const adminPath = normalizeToAdminPath(location.pathname);
  const subRoute = adminPath.replace(/^\/admin\/?/, '') || 'dashboard';
  const currentSubPath = subRoute === 'dashboard' ? '' : `/${subRoute}`;

  const { data: environment } = useQuery({
    queryKey: ['platform-environment', ref],
    queryFn: async () => {
      if (!ref) return null;
      const res = await client.records.list<Environment>('environments', {
        filter: environmentRefLookupFilter(ref),
        limit: 1,
      });
      return res.items[0] ?? null;
    },
    enabled: Boolean(ref),
  });

  const { data: project } = useQuery({
    queryKey: ['projects', environment?.project],
    queryFn: async () => {
      if (!environment?.project) return null;
      return client.records.get<Project>('projects', environment.project);
    },
    enabled: Boolean(environment?.project),
  });

  const { data: org } = useQuery({
    queryKey: ['organizations', project?.organization],
    queryFn: async () => {
      if (!project?.organization) return null;
      return client.records.get<Organization>('organizations', project.organization);
    },
    enabled: Boolean(project?.organization),
  });

  const { data: siblingEnvs = [] } = useQuery({
    queryKey: ['environments', project?.id],
    queryFn: async () => {
      if (!project?.id) return [];
      const res = await client.records.list<Environment>('environments', {
        filter: `project = "${project.id}"`,
        sort: 'name',
        limit: 100,
      });
      return res.items.filter((e) => e.status !== 'deleted');
    },
    enabled: Boolean(project?.id),
  });

  const orgLink = org ? `/organizations/${org.id}/projects` : '/organizations';
  const envListLink =
    org && project
      ? `/organizations/${org.id}/projects/${project.id}/environments`
      : orgLink;

  return (
    <div
      className="flex shrink-0 flex-wrap items-center gap-2 border-b bg-background px-4 py-2 text-sm"
      data-testid="platform-studio-chrome"
    >
      <nav
        className="flex min-w-0 flex-1 flex-wrap items-center gap-1 text-muted-foreground"
        aria-label="Breadcrumb"
        data-testid="platform-studio-breadcrumb"
      >
        <Link to="/organizations" className="hover:text-foreground hover:underline">
          Organizations
        </Link>
        <ChevronRight className="size-3.5 shrink-0" />
        <Link to={orgLink} className="hover:text-foreground hover:underline">
          {org?.name ?? 'Projects'}
        </Link>
        <ChevronRight className="size-3.5 shrink-0" />
        <Link to={envListLink} className="hover:text-foreground hover:underline">
          {project?.name ?? 'Project'}
        </Link>
        <ChevronRight className="size-3.5 shrink-0" />
        <span className="inline-flex items-center gap-2 font-medium text-foreground">
          {environment?.name ?? ref}
          {environment && <EnvironmentStatusBadge status={environment.status} />}
        </span>
      </nav>
      {siblingEnvs.length > 1 && (
        <select
          className="h-8 max-w-[12rem] truncate rounded-md border bg-background px-2 text-sm"
          value={ref}
          onChange={(e) => {
            window.location.href = `/project/${e.target.value}${currentSubPath}`;
          }}
          aria-label="Switch environment"
          data-testid="environment-switcher"
        >
          {siblingEnvs.map((env) => (
            <option key={env.id} value={environmentRouteRef(env)}>
              {env.name} ({env.slug})
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
