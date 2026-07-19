/**
 * Card shell for dashboard charts — title, description, loading skeleton, empty state.
 *
 * Usage:
 * - Wrap chart primitives (TimeSeriesAreaChart, DonutChart, etc.)
 * - Pass isLoading / isEmpty so Recharts never mounts on empty data
 * - Optional summary renders as visually-hidden text for screen readers
 */

import type { ReactNode } from 'react';
import { BarChart3 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

export interface ChartContainerProps {
  title: string;
  description?: string;
  isLoading?: boolean;
  isEmpty?: boolean;
  emptyMessage?: string;
  emptyHint?: string;
  /** Screen-reader summary of key series totals (not color-only). */
  summary?: string;
  className?: string;
  contentClassName?: string;
  headerAction?: ReactNode;
  children: ReactNode;
}

export function ChartContainer({
  title,
  description,
  isLoading = false,
  isEmpty = false,
  emptyMessage = 'No data for this period',
  emptyHint = 'Try a different time range or check back later.',
  summary,
  className,
  contentClassName,
  headerAction,
  children,
}: ChartContainerProps) {
  return (
    <Card className={cn(className)}>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="space-y-1">
          <CardTitle className="text-base font-semibold">{title}</CardTitle>
          {description ? (
            <CardDescription>{description}</CardDescription>
          ) : null}
        </div>
        {headerAction}
      </CardHeader>
      <CardContent className={cn('pt-2', contentClassName)}>
        {summary ? (
          <p className="sr-only" data-testid="chart-summary">
            {summary}
          </p>
        ) : null}
        {isLoading ? (
          <div className="space-y-3" data-testid="chart-loading">
            <Skeleton className="h-[200px] w-full rounded-md" />
          </div>
        ) : isEmpty ? (
          <div
            className="flex h-[200px] flex-col items-center justify-center rounded-md border border-dashed text-center"
            data-testid="chart-empty"
            role="status"
          >
            <BarChart3
              className="mb-3 h-8 w-8 text-muted-foreground/50"
              aria-hidden
            />
            <p className="text-sm font-medium text-muted-foreground">{emptyMessage}</p>
            {emptyHint ? (
              <p className="mt-1 max-w-xs text-xs text-muted-foreground/80">{emptyHint}</p>
            ) : null}
          </div>
        ) : (
          children
        )}
      </CardContent>
    </Card>
  );
}
