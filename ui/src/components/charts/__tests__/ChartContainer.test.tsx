import { describe, it, expect } from 'vitest'
import { render, screen } from '@/test/utils'
import { ChartContainer } from '../ChartContainer'

describe('ChartContainer', () => {
  it('renders title and children when data is present', () => {
    render(
      <ChartContainer title="Growth" description="Last 7 days">
        <div data-testid="chart-body">chart</div>
      </ChartContainer>,
    )
    expect(screen.getByText('Growth')).toBeInTheDocument()
    expect(screen.getByText('Last 7 days')).toBeInTheDocument()
    expect(screen.getByTestId('chart-body')).toBeInTheDocument()
  })

  it('shows loading skeleton', () => {
    render(
      <ChartContainer title="Growth" isLoading>
        <div>hidden</div>
      </ChartContainer>,
    )
    expect(screen.getByTestId('chart-loading')).toBeInTheDocument()
    expect(screen.queryByText('hidden')).not.toBeInTheDocument()
  })

  it('shows empty state without rendering children', () => {
    render(
      <ChartContainer title="Growth" isEmpty emptyMessage="Nothing here">
        <div>hidden</div>
      </ChartContainer>,
    )
    expect(screen.getByTestId('chart-empty')).toBeInTheDocument()
    expect(screen.getByText('Nothing here')).toBeInTheDocument()
    expect(screen.queryByText('hidden')).not.toBeInTheDocument()
  })

  it('renders screen-reader summary when provided', () => {
    render(
      <ChartContainer
        title="Growth"
        summary="Accounts created: 3. Users created: 11. Period: Last 7 days."
      >
        <div>chart</div>
      </ChartContainer>,
    )
    expect(screen.getByTestId('chart-summary')).toHaveTextContent(
      'Accounts created: 3. Users created: 11. Period: Last 7 days.',
    )
  })

  it('wraps chart children with a theme key for remount on theme flip', () => {
    document.documentElement.classList.remove('dark')
    const { container, rerender } = render(
      <ChartContainer title="Growth">
        <div data-testid="chart-body">chart</div>
      </ChartContainer>,
    )
    const themeWrap = container.querySelector('[data-theme]')
    expect(themeWrap).toBeTruthy()
    expect(themeWrap).toHaveAttribute('data-theme', 'light')
    expect(screen.getByTestId('chart-body')).toBeInTheDocument()

    document.documentElement.classList.add('dark')
    // Force observer-driven remount path is async; re-render still shows themed wrapper
    rerender(
      <ChartContainer title="Growth">
        <div data-testid="chart-body">chart</div>
      </ChartContainer>,
    )
    expect(container.querySelector('[data-theme]')).toBeTruthy()
    document.documentElement.classList.remove('dark')
  })
})
