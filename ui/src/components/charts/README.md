# Chart primitives

Shared Recharts wrappers for the admin UI (dashboard and future pages such as Jobs).

## Components

| Component | Use for |
|-----------|---------|
| `ChartContainer` | Card shell: title, description, loading skeleton, empty state, optional `summary` (sr-only) |
| `Sparkline` | Compact KPI trends |
| `TimeSeriesAreaChart` | Multi-series growth over time |
| `StackedBarChart` | Multi-series daily stacks (e.g. audit CREATE/UPDATE/DELETE) |
| `DonutChart` | Composition / status breakdowns (jobs, access mix) |
| `HorizontalBarChart` | Ranked bars (records by collection) |

Import from `@/components/charts` (see `index.ts`).

## Theme

Colors come from CSS variables in `App.css` via `CHART_COLORS` / `SERIES_COLORS` in `theme.ts`:

- `--chart-1` … `--chart-5` (light and dark modes)
- Axis ticks use `var(--muted-foreground)` for contrast on both themes
- Tooltips use `var(--card)` / `var(--border)` for dual-theme surfaces
- `ChartContainer` remounts chart children when `html.dark` flips so Recharts rebinds CSS-var strokes/fills without a hard reload
- Prefer live `var(--…)` strings over caching `resolveCssColor()` results

Always pass **named series / slice labels** so status is not color-only.

## Empty / loading contract

1. Prefer computing `isEmpty` in the page from data (all zeros or empty arrays).
2. Set `ChartContainer` `isEmpty` / `isLoading` so children (Recharts) do **not** mount on empty payloads.
3. Chart primitives return `null` when `data` is empty as a second safety net.
4. Pass a short `summary` string for screen readers (totals, not only colors).

## Accessibility

- Primary controls (range, refresh) live on the page with `aria-label`s.
- Chart containers accept `summary` → rendered with `sr-only` + `data-testid="chart-summary"`.
- Legends use text labels; donut slices use named categories (Success, Failed, Dead, …).

## Example

```tsx
import {
  ChartContainer,
  TimeSeriesAreaChart,
  CHART_COLORS,
} from '@/components/charts';

<ChartContainer
  title="Growth"
  description="Last 7 days"
  isLoading={isLoading}
  isEmpty={isEmpty}
  emptyMessage="No growth in this period"
  summary="Accounts created: 3. Users created: 11. Period: Last 7 days."
>
  <TimeSeriesAreaChart
    data={data}
    series={[
      { key: 'accounts', label: 'Accounts', color: CHART_COLORS.chart1 },
      { key: 'users', label: 'Users', color: CHART_COLORS.chart2 },
    ]}
  />
</ChartContainer>
```
