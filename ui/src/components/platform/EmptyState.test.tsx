import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Building2 } from 'lucide-react'
import { EmptyState } from './EmptyState'

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(
      <EmptyState
        icon={Building2}
        title="No organizations yet"
        description="Create an organization to get started."
      />,
    )
    expect(screen.getByText('No organizations yet')).toBeInTheDocument()
    expect(
      screen.getByText('Create an organization to get started.'),
    ).toBeInTheDocument()
  })

  it('shows Create organization CTA and fires onAction', async () => {
    const user = userEvent.setup()
    const onAction = vi.fn()
    render(
      <EmptyState
        icon={Building2}
        title="No organizations yet"
        description="Create one."
        actionLabel="Create organization"
        onAction={onAction}
        actionTestId="create-org-cta"
      />,
    )
    const cta = screen.getByTestId('create-org-cta')
    expect(cta).toHaveTextContent('Create organization')
    await user.click(cta)
    expect(onAction).toHaveBeenCalledOnce()
  })

  it('hides CTA when actionLabel is omitted', () => {
    render(
      <EmptyState
        icon={Building2}
        title="Empty"
        description="No action"
      />,
    )
    expect(screen.queryByTestId('empty-state-cta')).not.toBeInTheDocument()
  })
})
