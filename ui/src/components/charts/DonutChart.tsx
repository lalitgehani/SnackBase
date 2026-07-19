/**
 * Donut chart for composition / status breakdowns.
 */

import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { SERIES_COLORS } from './theme';
import type { CategoryValueDatum } from './types';

export interface DonutChartProps {
  data: CategoryValueDatum[];
  height?: number;
  innerRadius?: number;
  outerRadius?: number;
}

export function DonutChart({
  data,
  height = 240,
  innerRadius = 55,
  outerRadius = 80,
}: DonutChartProps) {
  const filtered = data.filter((d) => d.value > 0);
  if (!filtered.length) {
    return null;
  }

  return (
    <div style={{ width: '100%', height }} data-testid="donut-chart">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={filtered}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            paddingAngle={2}
            isAnimationActive={false}
          >
            {filtered.map((entry, index) => (
              <Cell
                key={`cell-${entry.name}`}
                fill={entry.color ?? SERIES_COLORS[index % SERIES_COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: 'var(--card)',
              border: '1px solid var(--border)',
              borderRadius: '0.5rem',
              fontSize: 12,
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 12, color: 'var(--foreground)' }}
            formatter={(value) => String(value)}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
