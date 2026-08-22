import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2 } from 'lucide-react'
import { useAuth } from '@snackbase/react'
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

const loginSchema = z.object({
  account: z.string().min(1, 'Account slug or ID is required'),
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
})

type LoginFormData = z.infer<typeof loginSchema>

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()
  const [error, setError] = useState<string | null>(null)

  const searchParams = new URLSearchParams(location.search)
  const returnTo = searchParams.get('returnTo')
  const from =
    (returnTo && returnTo.startsWith('/') ? returnTo : null) ??
    (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ??
    '/organizations'

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      account: '',
      email: '',
      password: '',
    },
  })

  const onSubmit = async (data: LoginFormData) => {
    setError(null)
    try {
      await login({
        email: data.email,
        password: data.password,
        account: data.account,
      })
      navigate(from, { replace: true })
    } catch (err) {
      setError(getErrorMessage(err, 'Invalid credentials'))
    }
  }

  return (
    <div className="relative flex min-h-svh w-full items-center justify-center p-6 md:p-10">
      <div className="absolute right-4 top-4 md:right-6 md:top-6">
        <ModeToggle />
      </div>
      <div className="w-full max-w-sm">
        <Card>
          <CardHeader className="py-4 text-left">
            <CardTitle className="text-2xl font-semibold tracking-tight">
              Sign in to SnackBase Cloud
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Use your Cloud account slug or ID, email, and password
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} noValidate>
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="account" className="text-sm font-medium">
                    Account
                  </FieldLabel>
                  <Input
                    id="account"
                    type="text"
                    autoComplete="organization"
                    placeholder="my-account or AB1234"
                    {...register('account')}
                    disabled={isSubmitting}
                  />
                  <p className="text-xs text-muted-foreground">
                    Account slug or ID (required for multi-tenant login)
                  </p>
                  <FieldError errors={[errors.account]} />
                </Field>
                <Field>
                  <FieldLabel htmlFor="email" className="text-sm font-medium">
                    Email
                  </FieldLabel>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    placeholder="you@example.com"
                    {...register('email')}
                    disabled={isSubmitting}
                  />
                  <FieldError errors={[errors.email]} />
                </Field>
                <Field>
                  <FieldLabel htmlFor="password" className="text-sm font-medium">
                    Password
                  </FieldLabel>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    {...register('password')}
                    disabled={isSubmitting}
                  />
                  <FieldError errors={[errors.password]} />
                </Field>

                {error && (
                  <div
                    className="rounded-md border border-destructive/20 bg-destructive/10 p-3"
                    role="alert"
                    data-testid="login-error"
                  >
                    <p className="text-sm text-destructive">{error}</p>
                  </div>
                )}

                <Field className="gap-4">
                  <Button type="submit" className="w-full" disabled={isSubmitting}>
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Signing in…
                      </>
                    ) : (
                      'Sign in'
                    )}
                  </Button>
                </Field>
              </FieldGroup>
            </form>
            <p className="mt-4 text-center text-sm text-muted-foreground">
              Don&apos;t have an account?{' '}
              <Link to="/register" className="font-medium text-primary underline-offset-4 hover:underline">
                Register
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
