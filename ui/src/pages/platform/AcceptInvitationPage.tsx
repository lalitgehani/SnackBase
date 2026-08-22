import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2 } from 'lucide-react'
import { useInvitation, useSnackBase } from '@snackbase/react'
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
import { ModeToggle } from '@/components/mode-toggle'
import { getErrorMessage } from '@/lib/errors'

const passwordSchema = z
  .object({
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string().min(1, 'Confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type PasswordForm = z.infer<typeof passwordSchema>

export default function AcceptInvitationPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const navigate = useNavigate()
  const client = useSnackBase()
  const { getPublic, accept, invitation, loading } = useInvitation()

  const [loadError, setLoadError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [fetched, setFetched] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { password: '', confirmPassword: '' },
  })

  useEffect(() => {
    if (!token) {
      setLoadError('Invitation token is missing. Open the link from your invite email.')
      setFetched(true)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        await getPublic(token)
      } catch (err) {
        if (!cancelled) {
          setLoadError(getErrorMessage(err, 'Invalid or expired invitation.'))
        }
      } finally {
        if (!cancelled) setFetched(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token, getPublic])

  const onSubmit = async (data: PasswordForm) => {
    if (!token) return
    setSubmitError(null)
    try {
      const auth = await accept(token, data.password)
      // InvitationService returns tokens but does not hydrate AuthManager — apply here.
      await client.internalAuthManager.updateState(auth)
      navigate('/organizations', { replace: true })
    } catch (err) {
      setSubmitError(
        getErrorMessage(err, 'Failed to accept invitation. Please try again.'),
      )
    }
  }

  const showForm =
    fetched && !loadError && invitation && (invitation.is_valid !== false)

  return (
    <div className="relative flex min-h-svh w-full items-center justify-center p-6 md:p-10">
      <div className="absolute right-4 top-4 md:right-6 md:top-6">
        <ModeToggle />
      </div>
      <Card className="w-full max-w-sm" data-testid="accept-invitation">
        <CardHeader>
          <CardTitle>Accept invitation</CardTitle>
          <CardDescription>
            {invitation?.account_name
              ? `Join ${invitation.account_name} on SnackBase Cloud.`
              : 'Team invites use native SnackBase account invitations (account-scoped).'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {(!fetched || loading) && !loadError && (
            <div className="flex justify-center py-6">
              <Loader2 className="size-8 animate-spin text-primary" />
            </div>
          )}

          {loadError && (
            <div
              className="rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
              role="alert"
              data-testid="accept-invite-error"
            >
              {loadError}
            </div>
          )}

          {invitation && !loadError && (
            <div className="space-y-1 text-sm">
              <p>
                <span className="text-muted-foreground">Email: </span>
                <span className="font-medium">{invitation.email}</span>
              </p>
              {invitation.invited_by_name && (
                <p>
                  <span className="text-muted-foreground">Invited by: </span>
                  <span className="font-medium">{invitation.invited_by_name}</span>
                </p>
              )}
            </div>
          )}

          {showForm && (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {submitError && (
                <div
                  className="rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
                  role="alert"
                  data-testid="accept-invite-submit-error"
                >
                  {submitError}
                </div>
              )}
              <FieldGroup>
                <Field data-invalid={Boolean(errors.password)}>
                  <FieldLabel htmlFor="invite-password">Create password</FieldLabel>
                  <Input
                    id="invite-password"
                    type="password"
                    autoComplete="new-password"
                    {...register('password')}
                  />
                  <FieldError errors={[errors.password]} />
                </Field>
                <Field data-invalid={Boolean(errors.confirmPassword)}>
                  <FieldLabel htmlFor="invite-confirm">Confirm password</FieldLabel>
                  <Input
                    id="invite-confirm"
                    type="password"
                    autoComplete="new-password"
                    {...register('confirmPassword')}
                  />
                  <FieldError errors={[errors.confirmPassword]} />
                </Field>
              </FieldGroup>
              <Button
                type="submit"
                className="w-full"
                disabled={isSubmitting}
                data-testid="accept-invite-submit"
              >
                {isSubmitting && <Loader2 className="size-4 animate-spin" />}
                Accept invitation
              </Button>
            </form>
          )}

          {loadError && (
            <div className="flex flex-col gap-2">
              <Button asChild>
                <Link to="/login">Sign in</Link>
              </Button>
              <Button asChild variant="outline">
                <Link to="/register">Create account</Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
