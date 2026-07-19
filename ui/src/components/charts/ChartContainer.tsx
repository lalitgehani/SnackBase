/**
 * Card shell for dashboard charts — title, description, loading skeleton, empty state.
 */

import type { ReactNode } from 'react';
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
        {isLoading ? (
          <div className="space-y-3" data-testid="chart-loading">
            <Skeleton className="h-[200px] w-full rounded-md" />
          </div>
        ) : isEmpty ? (
          <div
            className="flex h-[200px] flex-col items-center justify-center rounded-md border border-dashed text-center"
            data-testid="chart-empty"
          >
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
