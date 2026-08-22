import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQueryClient } from '@tanstack/react-query'
import { Building2, Loader2 } from 'lucide-react'
import { useSnackBase } from '@snackbase/react'
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
import { createOrganization } from '@/lib/control-plane/create-organization'
import { getErrorMessage } from '@/lib/errors'
import { isValidSlug, slugifyName } from '@/lib/slug'
import { useOrgContextStore } from '@/stores/org-context.store'

const schema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  slug: z
    .string()
    .min(1, 'Slug is required')
    .refine(isValidSlug, 'Use lowercase letters, numbers, and hyphens only'),
})

type FormData = z.infer<typeof schema>

export default function CreateOrganizationPage() {
  const client = useSnackBase()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setActiveOrg = useOrgContextStore((s) => s.setActiveOrg)
  const [error, setError] = useState<string | null>(null)
  const [slugTouched, setSlugTouched] = useState(false)

  const {
    register,
    handleSubmit,
    control,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', slug: '' },
  })

  const nameValue = useWatch({ control, name: 'name' })

  useEffect(() => {
    if (slugTouched) return
    const derived = slugifyName(nameValue ?? '')
    setValue('slug', derived, { shouldValidate: false })
  }, [nameValue, setValue, slugTouched])

  const onSubmit = async (data: FormData) => {
    setError(null)
    try {
      const { organization } = await createOrganization(client, data)
      await queryClient.invalidateQueries({ queryKey: ['organizations'] })
      setActiveOrg({
        id: organization.id,
        name: organization.name,
        slug: organization.slug,
      })
      navigate(`/organizations/${organization.id}/projects`, { replace: true })
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to create organization'))
    }
  }

  return (
    <Card className="max-w-lg" data-testid="create-org-form">
      <CardHeader>
        <div className="mb-2 flex size-10 items-center justify-center rounded-md bg-muted">
          <Building2 className="size-5 text-muted-foreground" />
        </div>
        <CardTitle>Create organization</CardTitle>
        <CardDescription>
          Organizations group your projects by team or product line.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {error && (
            <div
              className="rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
              role="alert"
              data-testid="create-org-error"
            >
              {error}
            </div>
          )}
          <FieldGroup>
            <Field data-invalid={Boolean(errors.name)}>
              <FieldLabel htmlFor="org-name">Name</FieldLabel>
              <Input
                id="org-name"
                placeholder="Acme Engineering"
                autoComplete="organization"
                {...register('name')}
              />
              <FieldError errors={[errors.name]} />
            </Field>
            <Field data-invalid={Boolean(errors.slug)}>
              <FieldLabel htmlFor="org-slug">Slug</FieldLabel>
              <Input
                id="org-slug"
                placeholder="acme-engineering"
                autoComplete="off"
                {...register('slug', {
                  onChange: () => setSlugTouched(true),
                })}
              />
              <p className="text-xs text-muted-foreground">
                URL-safe identifier. Unique in SnackBase Cloud for MVP.
              </p>
              <FieldError errors={[errors.slug]} />
            </Field>
          </FieldGroup>
          <div className="flex flex-wrap gap-2 pt-2">
            <Button type="submit" disabled={isSubmitting} data-testid="create-org-submit">
              {isSubmitting && <Loader2 className="size-4 animate-spin" />}
              Create organization
            </Button>
            <Button type="button" variant="outline" asChild>
              <Link to="/organizations">Cancel</Link>
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
