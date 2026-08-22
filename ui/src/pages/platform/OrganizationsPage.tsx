import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { Building2, ChevronRight } from 'lucide-react'
import { useSnackBase } from '@snackbase/react'
import { EmptyState } from '@/components/platform/EmptyState'
import { ListSkeleton } from '@/components/platform/ListSkeleton'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useOrgContextStore } from '@/stores/org-context.store'
import type { Organization } from '@/types/control-plane'

function formatCreatedAt(value?: string): string | null {
  if (!value) return null
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export default function OrganizationsPage() {
  const client = useSnackBase()
  const navigate = useNavigate()
  const setActiveOrg = useOrgContextStore((s) => s.setActiveOrg)

  const { data: orgs = [], isLoading, isError, error } = useQuery({
    queryKey: ['organizations'],
    queryFn: async () => {
      const res = await client.records.list<Organization>('organizations', {
        sort: 'name',
        limit: 100,
      })
      return res.items
    },
  })

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
          Failed to load organizations: {(error as Error)?.message ?? 'Unknown error'}
        </p>
      </div>
    )
  }

  if (orgs.length === 0) {
    return (
      <EmptyState
        icon={Building2}
        title="No organizations yet"
        description="Create an organization to group your projects by team or product line."
        actionLabel="Create organization"
        onAction={() => navigate('/organizations/new')}
        testId="orgs-empty-state"
        actionTestId="create-org-cta"
      />
    )
  }

  return (
    <div className="space-y-4" data-testid="orgs-list">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          {orgs.length} organization{orgs.length === 1 ? '' : 's'}
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => navigate('/organizations/new')}
          data-testid="create-org-link"
        >
          Create organization
        </Button>
      </div>
      <ul className="divide-y rounded-lg border bg-card">
        {orgs.map((org) => {
          const created = formatCreatedAt(org.created_at)
          return (
            <li key={org.id}>
              <button
                type="button"
                className="flex w-full items-center gap-4 p-4 text-left transition-colors hover:bg-muted/50"
                onClick={() => {
                  setActiveOrg({ id: org.id, name: org.name, slug: org.slug })
                  navigate(`/organizations/${org.id}/projects`)
                }}
                data-testid={`org-row-${org.id}`}
              >
                <div className="flex size-10 items-center justify-center rounded-md bg-muted">
                  <Building2 className="size-5 text-muted-foreground" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="truncate font-medium">{org.name}</span>
                    <Badge variant="secondary">{org.status}</Badge>
                  </div>
                  <p className="truncate text-sm text-muted-foreground">
                    {org.slug}
                    {created ? ` · Created ${created}` : ''}
                  </p>
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
