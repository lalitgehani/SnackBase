import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { FolderKanban, Loader2 } from 'lucide-react'
import { useAuth, useSnackBase } from '@snackbase/react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Field, FieldGroup, FieldLabel, FieldError } from '@/components/ui/field'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { createProject } from '@/lib/control-plane/create-project'
import { enqueueProvisionJob } from '@/lib/control-plane/enqueue-provision'
import { listAvailableRegions } from '@/lib/control-plane/regions'
import { getErrorMessage } from '@/lib/errors'
import { isValidSlug, slugifyName } from '@/lib/slug'
import { loadConfig } from '@/lib/config'
import type { Organization, TenancyMode } from '@/types/control-plane'

const schema = z.object({
  organizationId: z.string().min(1, 'Organization is required'),
  name: z.string().min(1, 'Name is required').max(200),
  slug: z
    .string()
    .min(1, 'Slug is required')
    .refine(isValidSlug, 'Use lowercase letters, numbers, and hyphens only'),
  region: z.string().min(1, 'Region is required'),
  tenancyMode: z.enum(['single', 'multi'], {
    message: 'Tenancy mode is required',
  }),
})

type FormData = z.infer<typeof schema>

export default function CreateProjectPage() {
  const { orgId } = useParams<{ orgId: string }>()
  const client = useSnackBase()
  const { user } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const slugTouched = useRef(false)
  const adminEmail = user?.email ?? ''
  const { provisionApiUrl } = loadConfig()

  const {
    data: orgs = [],
    isLoading: orgsLoading,
  } = useQuery({
    queryKey: ['organizations'],
    queryFn: async () => {
      const res = await client.records.list<Organization>('organizations', {
        sort: 'name',
        limit: 100,
      })
      return res.items
    },
  })

  const {
    data: regions = [],
    isLoading: regionsLoading,
    isError: regionsError,
    error: regionsErr,
  } = useQuery({
    queryKey: ['regions', 'available'],
    queryFn: () => listAvailableRegions(client),
  })

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      organizationId: orgId ?? '',
      name: '',
      slug: '',
      region: '',
      tenancyMode: 'single',
    },
  })

  const nameValue = watch('name')

  useEffect(() => {
    if (orgId) {
      setValue('organizationId', orgId)
    }
  }, [orgId, setValue])

  useEffect(() => {
    if (slugTouched.current) return
    setValue('slug', slugifyName(nameValue ?? ''), { shouldValidate: false })
  }, [nameValue, setValue])

  // Default to sole available region when loaded
  useEffect(() => {
    if (regions.length === 1) {
      setValue('region', regions[0].code, { shouldValidate: true })
    }
  }, [regions, setValue])

  const back = orgId ? `/organizations/${orgId}/projects` : '/organizations'

  const onSubmit = async (data: FormData) => {
    setError(null)
    try {
      if (!adminEmail) {
        throw new Error('Sign in required to set instance admin email')
      }
      const token = client.internalAuthManager.token
      if (!token) {
        throw new Error('Missing access token; sign in again')
      }
      const { project, environment } = await createProject(client, {
        organizationId: data.organizationId,
        name: data.name,
        slug: data.slug,
        region: data.region,
        tenancyMode: data.tenancyMode as TenancyMode,
      })
      await enqueueProvisionJob({
        environmentId: environment.id,
        accessToken: token,
        provisionApiUrl,
      })
      await queryClient.invalidateQueries({ queryKey: ['projects'] })
      await queryClient.invalidateQueries({ queryKey: ['environments'] })
      navigate(
        `/organizations/${data.organizationId}/projects/${project.id}/environments`,
        { replace: true },
      )
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to create project'))
    }
  }

  return (
    <Card className="max-w-xl" data-testid="create-project-form">
      <CardHeader>
        <div className="mb-2 flex size-10 items-center justify-center rounded-md bg-muted">
          <FolderKanban className="size-5 text-muted-foreground" />
        </div>
        <CardTitle>Create project</CardTitle>
        <CardDescription>
          Choose a region and tenancy mode. A production environment is created
          automatically. Instance credentials are platform-managed — admin email is
          your signed-in account ({adminEmail || '…'}).
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {error && (
            <div
              className="rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
              role="alert"
              data-testid="create-project-error"
            >
              {error}
            </div>
          )}

          {(regionsError || (!regionsLoading && regions.length === 0)) && (
            <div
              className="rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
              role="alert"
              data-testid="regions-load-error"
            >
              {regionsError
                ? `Failed to load regions: ${getErrorMessage(regionsErr)}`
                : 'No regions configured. Run control-plane seed (or create a regions codelist).'}
            </div>
          )}

          <FieldGroup>
            <Field data-invalid={Boolean(errors.organizationId)}>
              <FieldLabel>Organization</FieldLabel>
              <Controller
                name="organizationId"
                control={control}
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                    disabled={orgsLoading}
                  >
                    <SelectTrigger data-testid="project-org-select">
                      <SelectValue placeholder="Select organization" />
                    </SelectTrigger>
                    <SelectContent>
                      {orgs.map((org) => (
                        <SelectItem key={org.id} value={org.id}>
                          {org.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              <FieldError errors={[errors.organizationId]} />
            </Field>

            <Field data-invalid={Boolean(errors.name)}>
              <FieldLabel htmlFor="project-name">Name</FieldLabel>
              <Input
                id="project-name"
                placeholder="Customer API"
                {...register('name')}
              />
              <FieldError errors={[errors.name]} />
            </Field>

            <Field data-invalid={Boolean(errors.slug)}>
              <FieldLabel htmlFor="project-slug">Slug</FieldLabel>
              <Input
                id="project-slug"
                placeholder="customer-api"
                autoComplete="off"
                {...register('slug', {
                  onChange: () => {
                    slugTouched.current = true
                  },
                })}
              />
              <p className="text-xs text-muted-foreground">
                Globally unique — used for public hostname mapping.
              </p>
              <FieldError errors={[errors.slug]} />
            </Field>

            <Field data-invalid={Boolean(errors.region)}>
              <FieldLabel>Region</FieldLabel>
              <Controller
                name="region"
                control={control}
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                    disabled={regionsLoading || regions.length === 0}
                  >
                    <SelectTrigger data-testid="project-region-select">
                      <SelectValue
                        placeholder={
                          regionsLoading ? 'Loading regions…' : 'Select region'
                        }
                      />
                    </SelectTrigger>
                    <SelectContent>
                      {regions.map((r) => (
                        <SelectItem key={r.id ?? r.code} value={r.code}>
                          {r.name} ({r.code})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              <FieldError errors={[errors.region]} />
            </Field>

            <Field data-invalid={Boolean(errors.tenancyMode)}>
              <FieldLabel>Tenancy mode</FieldLabel>
              <Controller
                name="tenancyMode"
                control={control}
                render={({ field }) => (
                  <RadioGroup
                    value={field.value}
                    onValueChange={field.onChange}
                    className="gap-3"
                    data-testid="project-tenancy-group"
                  >
                    <div className="flex items-start gap-3 rounded-md border p-3">
                      <RadioGroupItem value="single" id="tenancy-single" />
                      <div className="grid gap-1">
                        <Label htmlFor="tenancy-single" className="font-medium">
                          Single-tenant instance
                        </Label>
                        <p className="text-xs text-muted-foreground">
                          One SnackBase instance dedicated to this project
                          (single-tenant mode).
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3 rounded-md border p-3">
                      <RadioGroupItem value="multi" id="tenancy-multi" />
                      <div className="grid gap-1">
                        <Label htmlFor="tenancy-multi" className="font-medium">
                          Multi-tenant instance
                        </Label>
                        <p className="text-xs text-muted-foreground">
                          Instance runs multi-tenant mode so your app can host
                          multiple customer accounts.
                        </p>
                      </div>
                    </div>
                  </RadioGroup>
                )}
              />
              <FieldError errors={[errors.tenancyMode]} />
            </Field>

            <Field>
              <FieldLabel>Instance admin email</FieldLabel>
              <Input
                value={adminEmail}
                readOnly
                disabled
                data-testid="project-admin-email"
              />
              <p className="text-xs text-muted-foreground">
                Taken from your signed-in Cloud account. Password is generated by the platform.
              </p>
            </Field>
          </FieldGroup>

          <div className="flex flex-wrap gap-2 pt-2">
            <Button
              type="submit"
              disabled={isSubmitting || regionsLoading || regions.length === 0}
              data-testid="create-project-submit"
            >
              {isSubmitting && <Loader2 className="size-4 animate-spin" />}
              Create project
            </Button>
            <Button type="button" variant="outline" asChild>
              <Link to={back}>Cancel</Link>
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
