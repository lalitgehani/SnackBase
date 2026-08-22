import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useAuth, useSnackBase } from '@snackbase/react'
import type { Invitation } from '@snackbase/sdk'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Field, FieldGroup, FieldLabel, FieldError } from '@/components/ui/field'
import { Badge } from '@/components/ui/badge'
import { getErrorMessage } from '@/lib/errors'

const inviteSchema = z.object({
  email: z.string().email('Enter a valid email'),
})

type InviteForm = z.infer<typeof inviteSchema>

export default function AccountSettingsPage() {
  const { user, account } = useAuth()
  const client = useSnackBase()
  const queryClient = useQueryClient()
  const [inviteError, setInviteError] = useState<string | null>(null)
  const [inviteSuccess, setInviteSuccess] = useState<string | null>(null)

  const {
    data: invitations = [],
    isLoading: invitesLoading,
    isError: invitesError,
    error: invitesErr,
  } = useQuery({
    queryKey: ['invitations'],
    queryFn: async () => {
      const res = await client.invitations.list({ status_filter: 'pending' })
      return res.invitations ?? []
    },
  })

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<InviteForm>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { email: '' },
  })

  const resendMutation = useMutation({
    mutationFn: (id: string) => client.invitations.resend(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['invitations'] }),
  })

  const cancelMutation = useMutation({
    mutationFn: (id: string) => client.invitations.cancel(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['invitations'] }),
  })

  const onInvite = async (data: InviteForm) => {
    setInviteError(null)
    setInviteSuccess(null)
    try {
      await client.invitations.create({ email: data.email.trim() })
      setInviteSuccess(`Invitation sent to ${data.email.trim()}`)
      reset()
      await queryClient.invalidateQueries({ queryKey: ['invitations'] })
    } catch (err) {
      const msg = getErrorMessage(err, 'Failed to send invitation')
      const lower = msg.toLowerCase()
      if (lower.includes('403') || lower.includes('forbidden') || lower.includes('permission')) {
        setInviteError('Only account admins can invite teammates.')
      } else {
        setInviteError(msg)
      }
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-4" data-testid="account-settings">
      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          <CardDescription>
            Account membership for SnackBase Cloud (control plane).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex justify-between gap-4 border-b py-2">
            <span className="text-muted-foreground">Email</span>
            <span className="font-medium">{user?.email ?? '—'}</span>
          </div>
          <div className="flex justify-between gap-4 border-b py-2">
            <span className="text-muted-foreground">Account name</span>
            <span className="font-medium">{account?.name ?? '—'}</span>
          </div>
          <div className="flex justify-between gap-4 border-b py-2">
            <span className="text-muted-foreground">Account slug</span>
            <span className="font-medium">{account?.slug ?? '—'}</span>
          </div>
          <div className="flex justify-between gap-4 py-2">
            <span className="text-muted-foreground">Account ID</span>
            <span className="font-mono text-xs font-medium">{account?.id ?? '—'}</span>
          </div>
        </CardContent>
      </Card>

      <Card data-testid="team-invites">
        <CardHeader>
          <CardTitle>Team invites</CardTitle>
          <CardDescription>
            Invite teammates to this Cloud account. Invites are{' '}
            <strong>account-scoped</strong> (not per organization) for MVP.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <form onSubmit={handleSubmit(onInvite)} className="space-y-3">
            {inviteError && (
              <div
                className="rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
                role="alert"
                data-testid="invite-error"
              >
                {inviteError}
              </div>
            )}
            {inviteSuccess && (
              <div
                className="rounded-md border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm text-emerald-700 dark:text-emerald-400"
                role="status"
                data-testid="invite-success"
              >
                {inviteSuccess}
              </div>
            )}
            <FieldGroup>
              <Field data-invalid={Boolean(errors.email)}>
                <FieldLabel htmlFor="invite-email">Email</FieldLabel>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Input
                    id="invite-email"
                    type="email"
                    placeholder="teammate@example.com"
                    className="flex-1"
                    {...register('email')}
                  />
                  <Button
                    type="submit"
                    disabled={isSubmitting}
                    data-testid="invite-submit"
                  >
                    {isSubmitting && <Loader2 className="size-4 animate-spin" />}
                    Send invite
                  </Button>
                </div>
                <FieldError errors={[errors.email]} />
              </Field>
            </FieldGroup>
          </form>

          <div className="space-y-2">
            <h4 className="text-sm font-medium">Pending invitations</h4>
            {invitesLoading && (
              <p className="text-sm text-muted-foreground">Loading…</p>
            )}
            {invitesError && (
              <p className="text-sm text-destructive" role="alert">
                {getErrorMessage(invitesErr, 'Failed to load invitations')}
              </p>
            )}
            {!invitesLoading && !invitesError && invitations.length === 0 && (
              <p className="text-sm text-muted-foreground" data-testid="invites-empty">
                No pending invitations.
              </p>
            )}
            <ul className="divide-y rounded-md border" data-testid="invites-list">
              {invitations.map((inv: Invitation) => (
                <li
                  key={inv.id}
                  className="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between"
                  data-testid={`invite-row-${inv.id}`}
                >
                  <div className="min-w-0 space-y-0.5">
                    <p className="truncate text-sm font-medium">{inv.email}</p>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="secondary">{inv.status}</Badge>
                      {inv.expires_at && (
                        <span className="text-xs text-muted-foreground">
                          Expires {new Date(inv.expires_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={resendMutation.isPending}
                      onClick={() => resendMutation.mutate(inv.id)}
                      data-testid={`invite-resend-${inv.id}`}
                    >
                      Resend
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={cancelMutation.isPending}
                      onClick={() => cancelMutation.mutate(inv.id)}
                      data-testid={`invite-cancel-${inv.id}`}
                    >
                      Cancel
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
