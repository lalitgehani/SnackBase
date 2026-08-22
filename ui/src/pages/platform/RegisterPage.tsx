import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
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

const registerSchema = z
  .object({
    account_name: z.string().min(1, 'Account name is required').max(255),
    account_slug: z
      .string()
      .max(32)
      .regex(/^[a-z0-9-]*$/, 'Slug must be lowercase letters, numbers, or hyphens')
      .optional()
      .or(z.literal('')),
    email: z.string().email('Invalid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string().min(1, 'Confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type RegisterFormData = z.infer<typeof registerSchema>

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register: registerUser } = useAuth()
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      account_name: '',
      account_slug: '',
      email: '',
      password: '',
      confirmPassword: '',
    },
  })

  const onSubmit = async (data: RegisterFormData) => {
    setError(null)
    try {
      const payload: {
        email: string
        password: string
        account_name: string
        account_slug?: string
      } = {
        email: data.email,
        password: data.password,
        account_name: data.account_name,
      }
      if (data.account_slug?.trim()) {
        payload.account_slug = data.account_slug.trim().toLowerCase()
      }
      await registerUser(payload)
      navigate('/organizations', { replace: true })
    } catch (err) {
      setError(getErrorMessage(err, 'Registration failed'))
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
              Create your Cloud account
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              Register a multi-tenant SnackBase Cloud account to manage organizations
              and projects
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} noValidate>
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="account_name" className="text-sm font-medium">
                    Account name
                  </FieldLabel>
                  <Input
                    id="account_name"
                    type="text"
                    placeholder="Acme Inc"
                    {...register('account_name')}
                    disabled={isSubmitting}
                  />
                  <FieldError errors={[errors.account_name]} />
                </Field>
                <Field>
                  <FieldLabel htmlFor="account_slug" className="text-sm font-medium">
                    Account slug <span className="font-normal text-muted-foreground">(optional)</span>
                  </FieldLabel>
                  <Input
                    id="account_slug"
                    type="text"
                    placeholder="acme-inc"
                    {...register('account_slug')}
                    disabled={isSubmitting}
                  />
                  <p className="text-xs text-muted-foreground">
                    Used at login. Auto-generated if left blank.
                  </p>
                  <FieldError errors={[errors.account_slug]} />
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
                    autoComplete="new-password"
                    {...register('password')}
                    disabled={isSubmitting}
                  />
                  <FieldError errors={[errors.password]} />
                </Field>
                <Field>
                  <FieldLabel htmlFor="confirmPassword" className="text-sm font-medium">
                    Confirm password
                  </FieldLabel>
                  <Input
                    id="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    {...register('confirmPassword')}
                    disabled={isSubmitting}
                  />
                  <FieldError errors={[errors.confirmPassword]} />
                </Field>

                {error && (
                  <div
                    className="rounded-md border border-destructive/20 bg-destructive/10 p-3"
                    role="alert"
                    data-testid="register-error"
                  >
                    <p className="text-sm text-destructive">{error}</p>
                  </div>
                )}

                <Field className="gap-4">
                  <Button type="submit" className="w-full" disabled={isSubmitting}>
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Creating account…
                      </>
                    ) : (
                      'Create account'
                    )}
                  </Button>
                </Field>
              </FieldGroup>
            </form>
            <p className="mt-4 text-center text-sm text-muted-foreground">
              Already have an account?{' '}
              <Link to="/login" className="font-medium text-primary underline-offset-4 hover:underline">
                Sign in
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
