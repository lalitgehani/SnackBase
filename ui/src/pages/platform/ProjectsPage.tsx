import { useEffect, useMemo } from 'react'
import { useQuery, useQueries } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router'
import { FolderKanban, ChevronRight } from 'lucide-react'
import { useSnackBase } from '@snackbase/react'
import { EmptyState } from '@/components/platform/EmptyState'
import { ListSkeleton } from '@/components/platform/ListSkeleton'
import { ProjectMetaBadges } from '@/components/platform/ProjectMetaBadges'
import { EnvironmentStatusBadge } from '@/components/platform/EnvironmentStatusBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useOrgContextStore } from '@/stores/org-context.store'
import type { Environment, Organization, Project } from '@/types/control-plane'

export default function ProjectsPage() {
  const { orgId } = useParams<{ orgId: string }>()
  const client = useSnackBase()
  const navigate = useNavigate()
  const { activeOrg, setActiveOrg } = useOrgContextStore()

  const { data: org } = useQuery({
    queryKey: ['organizations', orgId],
    queryFn: async () => {
      if (!orgId) return null
      return client.records.get<Organization>('organizations', orgId)
    },
    enabled: Boolean(orgId),
  })

  useEffect(() => {
    if (org) {
      setActiveOrg({ id: org.id, name: org.name, slug: org.slug })
    }
  }, [org, setActiveOrg])

  const { data: projects = [], isLoading, isError, error } = useQuery({
    queryKey: ['projects', orgId],
    queryFn: async () => {
      const res = await client.records.list<Project>('projects', {
        filter: `organization = "${orgId}"`,
        sort: '-created_at',
        limit: 100,
      })
      return res.items
    },
    enabled: Boolean(orgId),
  })

  const envQueries = useQueries({
    queries: projects.map((project) => ({
      queryKey: ['environments', project.id, 'summary'],
      queryFn: async () => {
        const res = await client.records.list<Environment>('environments', {
          filter: `project = "${project.id}" && slug = "production"`,
          limit: 1,
        })
        return res.items[0] ?? null
      },
      enabled: Boolean(project.id),
      staleTime: 30_000,
    })),
  })

  const productionByProjectId = useMemo(() => {
    const map = new Map<string, Environment | null>()
    projects.forEach((p, i) => {
      map.set(p.id, envQueries[i]?.data ?? null)
    })
    return map
  }, [projects, envQueries])

  if (!orgId) {
    return (
      <EmptyState
        icon={FolderKanban}
        title="Select an organization"
        description="Choose an organization to view its projects."
        actionLabel="View organizations"
        onAction={() => navigate('/organizations')}
      />
    )
  }

  if (isLoading) {
    return <ListSkeleton />
  }

  if (isError) {
    return (
      <div
        className="rounded-md border border-destructive/20 bg-destructive/10 p-4"
        role="alert"
      >
        <p className="text-sm text-destructive">
          Failed to load projects: {(error as Error)?.message ?? 'Unknown error'}
        </p>
      </div>
    )
  }

  if (projects.length === 0) {
    return (
      <EmptyState
        icon={FolderKanban}
        title="No projects yet"
        description={`Create a project in ${activeOrg?.name ?? org?.name ?? 'this organization'} to provision environments.`}
        actionLabel="Create project"
        onAction={() => navigate(`/organizations/${orgId}/projects/new`)}
        testId="projects-empty-state"
        actionTestId="create-project-cta"
      />
    )
  }

  return (
    <div className="space-y-4" data-testid="projects-list">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          {projects.length} project{projects.length === 1 ? '' : 's'}
          {(activeOrg?.name || org?.name) && (
            <>
              {' '}
              in{' '}
              <span className="font-medium text-foreground">
                {activeOrg?.name ?? org?.name}
              </span>
            </>
          )}
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => navigate(`/organizations/${orgId}/projects/new`)}
          data-testid="create-project-link"
        >
          Create project
        </Button>
      </div>
      <ul className="divide-y rounded-lg border bg-card">
        {projects.map((project) => {
          const prod = productionByProjectId.get(project.id)
          return (
            <li key={project.id}>
              <button
                type="button"
                className="flex w-full items-center gap-4 p-4 text-left transition-colors hover:bg-muted/50"
                onClick={() =>
                  navigate(
                    `/organizations/${orgId}/projects/${project.id}/environments`,
                  )
                }
                data-testid={`project-row-${project.id}`}
              >
                <div className="flex size-10 items-center justify-center rounded-md bg-muted">
                  <FolderKanban className="size-5 text-muted-foreground" />
                </div>
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="truncate font-medium">{project.name}</span>
                    <Badge variant="secondary">{project.status}</Badge>
                    {prod && (
                      <span data-testid={`project-prod-status-${project.id}`}>
                        <EnvironmentStatusBadge status={prod.status} />
                      </span>
                    )}
                  </div>
                  <p className="truncate text-sm text-muted-foreground">
                    {project.slug}
                    {prod ? ' · production' : ''}
                  </p>
                  <ProjectMetaBadges
                    region={project.region}
                    tenancyMode={project.tenancy_mode}
                  />
                </div>
                <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
