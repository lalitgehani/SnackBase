import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import {
  EnvironmentStatusBadge,
  ENVIRONMENT_STATUS_STYLES,
  getEnvironmentStatusMeta,
} from './EnvironmentStatusBadge'
import type { EnvironmentStatus } from '@/types/control-plane'

const ALL_STATUSES: EnvironmentStatus[] = [
  'pending',
  'provisioning',
  'ready',
  'failed',
  'deleting',
  'deleted',
]

describe('getEnvironmentStatusMeta', () => {
  it('maps every lifecycle status to a distinct label', () => {
    const labels = ALL_STATUSES.map((s) => getEnvironmentStatusMeta(s).label)
    expect(new Set(labels).size).toBe(ALL_STATUSES.length)
  })

  it('returns fallback for unknown status', () => {
    const meta = getEnvironmentStatusMeta('unknown-status')
    expect(meta.label).toBe('unknown-status')
  })
})

describe('EnvironmentStatusBadge', () => {
  it.each(ALL_STATUSES)('renders badge for status %s', (status) => {
    render(<EnvironmentStatusBadge status={status} />)
    const badge = screen.getByTestId('environment-status-badge')
    expect(badge).toHaveAttribute('data-status', status)
    expect(badge).toHaveTextContent(ENVIRONMENT_STATUS_STYLES[status].label)
  })

  it('uses distinct color classes for ready vs failed', () => {
    const ready = getEnvironmentStatusMeta('ready').className
    const failed = getEnvironmentStatusMeta('failed').className
    expect(ready).not.toEqual(failed)
    expect(ready).toMatch(/green/)
    expect(failed).toMatch(/red/)
  })
})
