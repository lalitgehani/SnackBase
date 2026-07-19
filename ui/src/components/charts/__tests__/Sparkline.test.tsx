import { describe, it, expect } from 'vitest'
import { render, screen } from '@/test/utils'
import { Sparkline } from '../Sparkline'

describe('Sparkline', () => {
  it('renders empty state for empty data', () => {
    render(<Sparkline data={[]} />)
    expect(screen.getByTestId('sparkline-empty')).toBeInTheDocument()
  })

  it('renders empty state when all counts are zero', () => {
    render(
      <Sparkline
        data={[
          { date: '2026-07-01', count: 0 },
          { date: '2026-07-02', count: 0 },
        ]}
      />,
    )
    expect(screen.getByTestId('sparkline-empty')).toBeInTheDocument()
  })

  it('renders chart when data has non-zero values', () => {
    render(
      <Sparkline
        data={[
          { date: '2026-07-01', count: 1 },
          { date: '2026-07-02', count: 3 },
        ]}
      />,
    )
    expect(screen.getByTestId('sparkline')).toBeInTheDocument()
  })
})
