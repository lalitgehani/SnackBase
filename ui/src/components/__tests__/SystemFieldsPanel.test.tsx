/**
 * Tests for SystemFieldsPanel
 */

import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { render } from '@/test/utils'
import SystemFieldsPanel, {
  SYSTEM_FIELDS,
} from '@/components/collections/SystemFieldsPanel'

describe('SystemFieldsPanel', () => {
  it('renders all system fields', () => {
    render(<SystemFieldsPanel />)
    expect(screen.getByTestId('system-fields-panel')).toBeInTheDocument()
    for (const field of SYSTEM_FIELDS) {
      expect(screen.getByText(field.name)).toBeInTheDocument()
    }
  })

  it('explains fields are platform-managed', () => {
    render(<SystemFieldsPanel />)
    expect(
      screen.getByText(/always applied by the platform/i),
    ).toBeInTheDocument()
  })

  it('does not render delete or edit controls for system fields', () => {
    render(<SystemFieldsPanel />)
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })
})
