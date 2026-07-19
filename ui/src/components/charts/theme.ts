/**
 * Chart theme helpers — resolve CSS variables for Recharts strokes/fills.
 * Works in light and dark mode via theme tokens in App.css.
 */

export const CHART_COLORS = {
  primary: 'var(--primary)',
  muted: 'var(--muted-foreground)',
  chart1: 'var(--chart-1)',
  chart2: 'var(--chart-2)',
  chart3: 'var(--chart-3)',
  chart4: 'var(--chart-4)',
  chart5: 'var(--chart-5)',
  border: 'var(--border)',
  background: 'var(--background)',
  card: 'var(--card)',
  foreground: 'var(--foreground)',
} as const;

/** Default palette for multi-series charts */
export const SERIES_COLORS = [
  CHART_COLORS.chart1,
  CHART_COLORS.chart2,
  CHART_COLORS.chart3,
  CHART_COLORS.chart4,
  CHART_COLORS.chart5,
] as const;

/**
 * Resolve a CSS variable to a concrete color when Recharts needs a computed value
 * (e.g. gradients in SVG). Falls back to the raw var string if document is unavailable.
 */
export function resolveCssColor(cssVar: string, fallback = '#888888'): string {
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return fallback;
  }
  // Support "var(--token)" and bare "--token"
  const match = cssVar.match(/var\((--[^)]+)\)/) || cssVar.match(/^(--[\w-]+)$/);
  const prop = match?.[1] ?? cssVar;
  const value = getComputedStyle(document.documentElement).getPropertyValue(prop).trim();
  return value || fallback;
}
