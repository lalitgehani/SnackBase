/**
 * Horizontal ranked bar chart (e.g. records by collection).
 */

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { CHART_COLORS } from './theme';
import type { RankedBarDatum } from './types';

export interface HorizontalBarChartProps {
  data: RankedBarDatum[];
  height?: number;
  color?: string;
}

export function HorizontalBarChart({
  data,
  height = 280,
  color = CHART_COLORS.chart1,
}: HorizontalBarChartProps) {
  if (!data.length) {
    return null;
  }

  // Ensure enough vertical space for labels
  const computedHeight = Math.max(height, data.length * 32 + 40);

  return (
    <div style={{ width: '100%', height: computedHeight }} data-testid="horizontal-bar-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 8, right: 16, left: 8, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
          <YAxis
            type="category"
            dataKey="name"
            width={100}
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--card)',
              border: '1px solid var(--border)',
              borderRadius: '0.5rem',
              fontSize: 12,
            }}
          />
          <Bar dataKey="value" fill={color} radius={[0, 4, 4, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
