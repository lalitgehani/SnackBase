/**
 * Tests for AppDialog component (FT2.4)
 *
 * Verifies:
 * - Dialog title, description, children, and footer render correctly
 * - Dialog is hidden when open=false
 * - X close button calls onOpenChange(false)
 * - Escape key calls onOpenChange(false)
 * - ReactNode title renders correctly
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/utils'
import { AppDialog } from '@/components/common/AppDialog'

describe('AppDialog', () => {
  describe('rendering', () => {
    it('renders title when open', () => {
      render(
        <AppDialog open={true} onOpenChange={vi.fn()} title="Test Title">
          <div>Content</div>
        </AppDialog>
      )
      expect(screen.getByText('Test Title')).toBeInTheDocument()
    })

    it('renders description when provided', () => {
      render(
        <AppDialog
          open={true}
          onOpenChange={vi.fn()}
          title="Title"
          description="Test description text"
        >
          <div>Content</div>
        </AppDialog>
      )
      expect(screen.getByText('Test description text')).toBeInTheDocument()
    })

    it('does not render description when not provided', () => {
      render(
        <AppDialog open={true} onOpenChange={vi.fn()} title="Title">
          <div>Content</div>
        </AppDialog>
      )
      expect(screen.queryByText('Test description text')).not.toBeInTheDocument()
    })

    it('renders children content', () => {
      render(
        <AppDialog open={true} onOpenChange={vi.fn()} title="Title">
          <div data-testid="dialog-body">Dialog body content</div>
        </AppDialog>
      )
      expect(screen.getByTestId('dialog-body')).toBeInTheDocument()
      expect(screen.getByText('Dialog body content')).toBeInTheDocument()
    })

    it('renders footer content when footer prop is provided', () => {
      render(
        <AppDialog
          open={true}
          onOpenChange={vi.fn()}
          title="Title"
          footer={<button>Submit Action</button>}
        >
          <div>Content</div>
        </AppDialog>
      )
      expect(screen.getByRole('button', { name: 'Submit Action' })).toBeInTheDocument()
    })

    it('does not render footer content when footer prop is omitted', () => {
      render(
        <AppDialog open={true} onOpenChange={vi.fn()} title="Title">
          <div>Content</div>
        </AppDialog>
      )
      expect(screen.queryByRole('button', { name: 'Submit Action' })).not.toBeInTheDocument()
    })

    it('does not render dialog content when open is false', () => {
      render(
        <AppDialog open={false} onOpenChange={vi.fn()} title="Hidden Title">
          <div>Hidden content</div>
        </AppDialog>
      )
      expect(screen.queryByText('Hidden Title')).not.toBeInTheDocument()
      expect(screen.queryByText('Hidden content')).not.toBeInTheDocument()
    })

    it('renders ReactNode as title', () => {
      render(
        <AppDialog
          open={true}
          onOpenChange={vi.fn()}
          title={<span data-testid="custom-title">Rich Title Node</span>}
        >
          <div>Content</div>
        </AppDialog>
      )
      expect(screen.getByTestId('custom-title')).toBeInTheDocument()
      expect(screen.getByText('Rich Title Node')).toBeInTheDocument()
    })
  })

  describe('close behavior', () => {
    it('calls onOpenChange(false) when X close button is clicked', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()

      render(
        <AppDialog open={true} onOpenChange={onOpenChange} title="Title">
          <div>Content</div>
        </AppDialog>
      )

      const closeButton = screen.getByRole('button', { name: /close/i })
      await user.click(closeButton)
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })

    it('calls onOpenChange(false) when Escape key is pressed', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()

      render(
        <AppDialog open={true} onOpenChange={onOpenChange} title="Title">
          <input data-testid="focus-target" />
        </AppDialog>
      )

      // Focus something inside the dialog so Escape is captured
      const input = screen.getByTestId('focus-target')
      await user.click(input)
      await user.keyboard('{Escape}')
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })
  })
})
