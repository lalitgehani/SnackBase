/**
 * Compact sparkline for KPI cards — area/line over a time series.
 */

import {
  Area,
  AreaChart,
  ResponsiveContainer,
  YAxis,
} from 'recharts';
import { CHART_COLORS } from './theme';
import type { TimeSeriesDatum } from './types';
import { cn } from '@/lib/utils';

export interface SparklineProps {
  data: TimeSeriesDatum[];
  dataKey?: string;
  color?: string;
  className?: string;
  height?: number;
  /** When all zeros / empty, show a neutral flat line placeholder */
  showEmptyState?: boolean;
}

export function Sparkline({
  data,
  dataKey = 'count',
  color = CHART_COLORS.chart1,
  className,
  height = 40,
  showEmptyState = true,
}: SparklineProps) {
  const hasData = data.length > 0;
  const allZero = hasData && data.every((d) => Number(d[dataKey] ?? 0) === 0);

  if (!hasData || (allZero && showEmptyState)) {
    return (
      <div
        className={cn('flex w-full items-end', className)}
        style={{ height }}
        data-testid="sparkline-empty"
        aria-hidden
      >
        <div className="h-px w-full bg-muted-foreground/20" />
      </div>
    );
  }

  const gradientId = `sparkline-${dataKey.replace(/[^a-zA-Z0-9_-]/g, '')}`;

  return (
    <div className={cn('w-full', className)} style={{ height }} data-testid="sparkline">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <YAxis hide domain={['dataMin', 'dataMax']} />
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#${gradientId})`}
            isAnimationActive={false}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
