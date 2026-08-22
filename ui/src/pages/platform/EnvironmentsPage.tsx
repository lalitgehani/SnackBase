import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router'
import {
  Server,
  Copy,
  Check,
  ChevronRight,
  RefreshCw,
  Trash2,
  Plus,
} from 'lucide-react'
import { useSnackBase, useAuth } from '@snackbase/react'
import { EmptyState } from '@/components/platform/EmptyState'
import { ListSkeleton } from '@/components/platform/ListSkeleton'
import { EnvironmentStatusBadge } from '@/components/platform/EnvironmentStatusBadge'
import { ProjectMetaBadges } from '@/components/platform/ProjectMetaBadges'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { createEnvironment } from '@/lib/control-plane/create-environment'
import { enqueueProvisionJob } from '@/lib/control-plane/enqueue-provision'
import { invokeBreakGlass } from '@/lib/control-plane/break-glass'
import { retryProvision } from '@/lib/control-plane/retry-provision'
import {
  archiveProjectWithEnvironments,
  requestEnvironmentDelete,
} from '@/lib/control-plane/delete-environment'
import { getErrorMessage } from '@/lib/errors'
import { slugifyName } from '@/lib/slug'
import { loadConfig } from '@/lib/config'
import { environmentRouteRef } from '@/lib/control-plane/env-ref'
import type { Environment, Organization, Project } from '@/types/control-plane'

const IN_FLIGHT = new Set(['pending', 'provisioning', 'deleting'])

export default function EnvironmentsPage() {
  const { orgId, projectId } = useParams<{ orgId: string; projectId: string }>()
  const client = useSnackBase()
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [copyToast, setCopyToast] = useState(false)
  const [showAddEnv, setShowAddEnv] = useState(false)
  const [newEnvName, setNewEnvName] = useState('Staging')
  const [newEnvSlug, setNewEnvSlug] = useState('staging')
  const [retryEnvId, setRetryEnvId] = useState<string | null>(null)
  const [breakGlassEnvId, setBreakGlassEnvId] = useState<string | null>(null)
  const [breakGlassResult, setBreakGlassResult] = useState<{
    instance_url: string
    email: string
    password: string
  } | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const adminEmail = user?.email ?? ''
  const { provisionApiUrl } = loadConfig()

  const requireToken = () => {
    const token = client.internalAuthManager.token
    if (!token) throw new Error('Missing access token; sign in again')
    return token
  }

  const { data: project } = useQuery({
    queryKey: ['projects', projectId],
    queryFn: async () => {
      if (!projectId) return null
      return client.records.get<Project>('projects', projectId)
    },
    enabled: Boolean(projectId),
  })

  const { data: org } = useQuery({
    queryKey: ['organizations', orgId],
    queryFn: async () => {
      if (!orgId) return null
      return client.records.get<Organization>('organizations', orgId)
    },
    enabled: Boolean(orgId),
  })

  const {
    data: environments = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['environments', projectId],
    queryFn: async () => {
      const res = await client.records.list<Environment>('environments', {
        filter: `project = "${projectId}"`,
        sort: 'name',
        limit: 100,
      })
      return res.items
    },
    enabled: Boolean(projectId),
    refetchInterval: (query) => {
      const items = query.state.data ?? []
      const needsPoll = items.some((e) => IN_FLIGHT.has(e.status))
      return needsPoll ? 2500 : false
    },
  })

  const visibleEnvs = useMemo(
    () => environments.filter((e) => e.status !== 'deleted'),
    [environments],
  )

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['environments', projectId] })
    void queryClient.invalidateQueries({ queryKey: ['projects', projectId] })
  }

  const retryMutation = useMutation({
    mutationFn: async () => {
      if (!retryEnvId) throw new Error('No environment selected')
      const token = requireToken()
      await retryProvision(client, retryEnvId)
      await enqueueProvisionJob({
        environmentId: retryEnvId,
        accessToken: token,
        provisionApiUrl,
      })
    },
    onSuccess: () => {
      setActionError(null)
      setRetryEnvId(null)
      invalidate()
    },
    onError: (err) => setActionError(getErrorMessage(err)),
  })

  const deleteMutation = useMutation({
    mutationFn: (envId: string) => requestEnvironmentDelete(client, envId),
    onSuccess: () => {
      setActionError(null)
      invalidate()
    },
    onError: (err) => setActionError(getErrorMessage(err)),
  })

  const createEnvMutation = useMutation({
    mutationFn: async () => {
      if (!adminEmail) throw new Error('Sign in required')
      const token = requireToken()
      const env = await createEnvironment(client, {
        projectId: projectId!,
        name: newEnvName,
        slug: newEnvSlug,
      })
      await enqueueProvisionJob({
        environmentId: env.id,
        accessToken: token,
        provisionApiUrl,
      })
      return env
    },
    onSuccess: () => {
      setActionError(null)
      setShowAddEnv(false)
      setNewEnvName('Staging')
      setNewEnvSlug('staging')
      invalidate()
    },
    onError: (err) => setActionError(getErrorMessage(err)),
  })

  const breakGlassMutation = useMutation({
    mutationFn: async (env: Environment) => {
      const token = requireToken()
      const ref = environmentRouteRef(env)
      return invokeBreakGlass({ envRef: ref, accessToken: token })
    },
    onSuccess: (result) => {
      setActionError(null)
      setBreakGlassResult(result)
      setBreakGlassEnvId(null)
    },
    onError: (err) => setActionError(getErrorMessage(err)),
  })

  const archiveMutation = useMutation({
    mutationFn: async () => {
      if (!projectId) throw new Error('No project')
      await archiveProjectWithEnvironments(client, projectId, environments)
    },
    onSuccess: () => {
      setActionError(null)
      invalidate()
      if (orgId) navigate(`/organizations/${orgId}/projects`)
    },
    onError: (err) => setActionError(getErrorMessage(err)),
  })

  const copyUrl = async (env: Environment) => {
    if (!env.instance_url) return
    try {
      await navigator.clipboard.writeText(env.instance_url)
      setCopiedId(env.id)
      setCopyToast(true)
      window.setTimeout(() => setCopiedId((id) => (id === env.id ? null : id)), 2000)
      window.setTimeout(() => setCopyToast(false), 2500)
    } catch {
      setActionError('Could not copy to clipboard')
    }
  }

  if (!projectId) {
    return (
      <EmptyState
        icon={Server}
        title="Select a project"
        description="Choose a project to view its environments."
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
          Failed to load environments: {(error as Error)?.message ?? 'Unknown error'}
        </p>
      </div>
    )
  }

  const projectsHref = orgId ? `/organizations/${orgId}/projects` : '/organizations'
  const hasReady = visibleEnvs.some((e) => e.status === 'ready')

  return (
    <div className="space-y-4" data-testid="environments-list">
      {copyToast && (
        <div
          className="fixed bottom-4 right-4 z-50 rounded-md border bg-card px-4 py-2 text-sm shadow-lg"
          role="status"
          data-testid="copy-toast"
        >
          API URL copied to clipboard
        </div>
      )}

      <nav
        className="flex flex-wrap items-center gap-1 text-sm text-muted-foreground"
        aria-label="Breadcrumb"
        data-testid="project-breadcrumb"
      >
        <Link to="/organizations" className="hover:text-foreground hover:underline">
          Organizations
        </Link>
        <ChevronRight className="size-3.5 shrink-0" />
        {orgId ? (
          <Link to={projectsHref} className="hover:text-foreground hover:underline">
            {org?.name ?? 'Projects'}
          </Link>
        ) : (
          <span>Projects</span>
        )}
        <ChevronRight className="size-3.5 shrink-0" />
        <span className="font-medium text-foreground">
          {project?.name ?? 'Project'}
        </span>
      </nav>

      {project && (
        <div className="space-y-2 rounded-lg border bg-card p-4" data-testid="project-header">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-lg font-semibold tracking-tight">{project.name}</h3>
                <span className="text-sm text-muted-foreground">{project.slug}</span>
                {project.status === 'archived' && (
                  <span className="rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                    Archived
                  </span>
                )}
              </div>
              <ProjectMetaBadges
                region={project.region}
                tenancyMode={project.tenancy_mode}
              />
              <p className="text-xs text-muted-foreground">
                Single-tenant projects open in the integrated Studio. Multi-tenant
                environments use the instance URL directly.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setShowAddEnv((v) => !v)}
                data-testid="add-environment-toggle"
                disabled={project.status === 'archived'}
              >
                <Plus className="size-4" />
                Add environment
              </Button>
              {project.status !== 'archived' && (
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      data-testid="archive-project"
                    >
                      Archive project
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Archive this project?</AlertDialogTitle>
                      <AlertDialogDescription>
                        {hasReady
                          ? 'Ready environments will be deprovisioned (containers removed). This cannot be undone from the Console.'
                          : 'The project will be marked archived. Pending environments will still be cleaned up.'}
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={() => archiveMutation.mutate()}
                        data-testid="archive-project-confirm"
                      >
                        Archive
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              )}
            </div>
          </div>
        </div>
      )}

      {actionError && (
        <div
          className="rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
          role="alert"
          data-testid="env-action-error"
        >
          {actionError}
        </div>
      )}

      {showAddEnv && (
        <div
          className="space-y-3 rounded-lg border bg-card p-4"
          data-testid="add-environment-form"
        >
          <h4 className="text-sm font-medium">New environment</h4>
          <p className="text-xs text-muted-foreground">
            Uses this project&apos;s region ({project?.region}) and tenancy (
            {project?.tenancy_mode}). Instance credentials are platform-managed.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="env-name">Name</Label>
              <Input
                id="env-name"
                value={newEnvName}
                onChange={(e) => {
                  setNewEnvName(e.target.value)
                  setNewEnvSlug(slugifyName(e.target.value) || 'staging')
                }}
                data-testid="env-name-input"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="env-slug">Slug</Label>
              <Input
                id="env-slug"
                value={newEnvSlug}
                onChange={(e) => setNewEnvSlug(e.target.value.toLowerCase())}
                data-testid="env-slug-input"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              onClick={() => createEnvMutation.mutate()}
              disabled={createEnvMutation.isPending}
              data-testid="env-create-submit"
            >
              {createEnvMutation.isPending ? 'Creating…' : 'Create & provision'}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => setShowAddEnv(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {breakGlassResult && (
        <div
          className="space-y-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4"
          role="alert"
          data-testid="break-glass-result"
        >
          <p className="text-sm font-medium">Break-glass credentials (shown once)</p>
          <p className="text-xs text-muted-foreground">
            Copy these now — the password was rotated after this reveal.
          </p>
          <dl className="grid gap-1 text-sm">
            <div>
              <dt className="text-muted-foreground">Instance URL</dt>
              <dd className="font-mono break-all">{breakGlassResult.instance_url}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Admin email</dt>
              <dd className="font-mono">{breakGlassResult.email}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Password</dt>
              <dd className="font-mono">{breakGlassResult.password}</dd>
            </div>
          </dl>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setBreakGlassResult(null)}
          >
            Dismiss
          </Button>
        </div>
      )}

      {visibleEnvs.length === 0 ? (
        <EmptyState
          icon={Server}
          title="No environments yet"
          description="Create a project to bootstrap production, or add an environment above."
          actionLabel="Back to projects"
          onAction={() => navigate(projectsHref)}
          testId="environments-empty-state"
          actionTestId="environments-empty-cta"
        />
      ) : (
        <ul className="divide-y rounded-lg border bg-card">
          {visibleEnvs.map((env) => {
            const isReady = env.status === 'ready' && Boolean(env.instance_url)
            const isFailed = env.status === 'failed'
            const isBusy = IN_FLIGHT.has(env.status)
            return (
              <li
                key={env.id}
                className="flex flex-col gap-3 p-4 sm:flex-row sm:items-start"
                data-testid={`env-row-${env.id}`}
              >
                <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-muted">
                  <Server className="size-5 text-muted-foreground" />
                </div>
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="truncate font-medium">{env.name}</span>
                    <EnvironmentStatusBadge status={env.status} />
                  </div>
                  <p className="truncate text-sm text-muted-foreground">{env.slug}</p>
                  {(env.snackbase_superadmin_email ||
                    env.snackbase_secret_key) && (
                    <p
                      className="text-xs text-muted-foreground"
                      data-testid={`bootstrap-readonly-${env.id}`}
                    >
                      Instance credentials are platform-managed (provisioned
                      automatically).
                    </p>
                  )}
                  {isReady && (
                    <a
                      href={env.instance_url!}
                      target="_blank"
                      rel="noreferrer"
                      className="block truncate text-sm text-primary underline-offset-4 hover:underline"
                    >
                      {env.instance_url}
                    </a>
                  )}
                  {isFailed && env.error_message && (
                    <p className="text-sm text-destructive">{env.error_message}</p>
                  )}
                  {env.status === 'pending' && (
                    <p className="text-xs text-muted-foreground">
                      Waiting for provision worker…
                    </p>
                  )}
                  {env.status === 'provisioning' && (
                    <p className="text-xs text-muted-foreground">
                      Provisioning instance…
                    </p>
                  )}
                  {env.status === 'deleting' && (
                    <p className="text-xs text-muted-foreground">
                      Removing data-plane resources…
                    </p>
                  )}
                  {isReady && env.instance_url && (
                    <Collapsible className="pt-1">
                      <CollapsibleTrigger
                        className="text-xs text-muted-foreground underline-offset-4 hover:underline"
                        data-testid={`sdk-snippet-toggle-${env.id}`}
                      >
                        SDK connect snippet
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <pre
                          className="mt-2 overflow-x-auto rounded-md bg-muted p-3 text-xs"
                          data-testid={`sdk-snippet-${env.id}`}
                        >{`import { SnackBaseClient } from '@snackbase/sdk'

const client = new SnackBaseClient({
  baseUrl: '${env.instance_url}',
})`}</pre>
                      </CollapsibleContent>
                    </Collapsible>
                  )}
                </div>
                <div className="flex shrink-0 flex-wrap gap-2">
                  {isReady && (
                    <>
                      <Button
                        type="button"
                        size="sm"
                        asChild
                        data-testid={`open-studio-${env.id}`}
                      >
                        <Link to={`/project/${environmentRouteRef(env)}/collections`}>
                          Open Studio
                        </Link>
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => copyUrl(env)}
                        data-testid={`copy-url-${env.id}`}
                      >
                        {copiedId === env.id ? (
                          <Check className="size-4" />
                        ) : (
                          <Copy className="size-4" />
                        )}
                        {copiedId === env.id ? 'Copied' : 'Copy API URL'}
                      </Button>
                      <AlertDialog
                        open={breakGlassEnvId === env.id}
                        onOpenChange={(open) => {
                          if (!open) setBreakGlassEnvId(null)
                        }}
                      >
                        <AlertDialogTrigger asChild>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => setBreakGlassEnvId(env.id)}
                            data-testid={`break-glass-${env.id}`}
                          >
                            Break-glass access
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>
                              Reveal direct instance credentials?
                            </AlertDialogTitle>
                            <AlertDialogDescription>
                              This bypasses platform session controls and returns
                              the instance superadmin password once. The credential
                              is rotated immediately after reveal and the action is
                              audited. Use only when integrated Studio access is
                              broken.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              disabled={breakGlassMutation.isPending}
                              onClick={(e) => {
                                e.preventDefault()
                                breakGlassMutation.mutate(env)
                              }}
                              data-testid={`break-glass-confirm-${env.id}`}
                            >
                              {breakGlassMutation.isPending
                                ? 'Revealing…'
                                : 'Reveal credentials'}
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </>
                  )}
                  {isFailed && (
                    <AlertDialog
                      open={retryEnvId === env.id}
                      onOpenChange={(open) => {
                        if (!open) setRetryEnvId(null)
                      }}
                    >
                      <AlertDialogTrigger asChild>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => setRetryEnvId(env.id)}
                          disabled={retryMutation.isPending}
                          data-testid={`retry-provision-${env.id}`}
                        >
                          <RefreshCw className="size-4" />
                          Retry provision
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>
                            Retry provision for “{env.name}”?
                          </AlertDialogTitle>
                          <AlertDialogDescription>
                            The platform will re-queue provisioning with new
                            credentials. Admin email: {adminEmail || '—'}.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            disabled={retryMutation.isPending}
                            onClick={(e) => {
                              e.preventDefault()
                              retryMutation.mutate()
                            }}
                          >
                            {retryMutation.isPending ? 'Retrying…' : 'Retry'}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  )}
                  {!isBusy && env.status !== 'deleted' && (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          data-testid={`delete-env-${env.id}`}
                        >
                          <Trash2 className="size-4" />
                          Delete
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>
                            Delete environment “{env.name}”?
                          </AlertDialogTitle>
                          <AlertDialogDescription>
                            The running instance (if any) will be removed from the
                            data plane. Open Admin will no longer be available.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            className={buttonDestructiveClass}
                            onClick={() => deleteMutation.mutate(env.id)}
                            data-testid={`delete-env-confirm-${env.id}`}
                          >
                            Delete environment
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

/** Destructive styling for confirm action (AlertDialogAction uses default variants). */
const buttonDestructiveClass =
  'bg-destructive text-white hover:bg-destructive/90 focus-visible:ring-destructive/20'
