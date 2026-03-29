/**
 * AggregationSummaryBar
 * Collapsible section showing count + per-numeric-field stats (sum, avg, min, max).
 * Recalculates whenever filterExpression changes.
 */

import { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, BarChart2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { aggregateRecords } from '@/services/records.service';
import type { Collection } from '@/services/collections.service';
import type { AggregationResult } from '@/types/records.types';

interface Props {
	collection: Collection;
	filterExpression: string;
}

interface StatCard {
	label: string;
	value: string;
}

function formatNumber(val: unknown): string {
	if (val === null || val === undefined) return '—';
	const n = Number(val);
	if (isNaN(n)) return String(val);
	return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export default function AggregationSummaryBar({ collection, filterExpression }: Props) {
	const [open, setOpen] = useState(false);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [stats, setStats] = useState<StatCard[]>([]);

	const numericFields = (collection.schema ?? []).filter(
		(f) => f.type === 'number' || f.type === 'integer',
	);

	useEffect(() => {
		const run = async () => {
			setLoading(true);
			setError(null);
			try {
				const fnParts = ['count()'];
				for (const f of numericFields) {
					fnParts.push(`sum(${f.name})`, `avg(${f.name})`, `min(${f.name})`, `max(${f.name})`);
				}
				const params: { functions: string; filter?: string } = {
					functions: fnParts.join(','),
				};
				if (filterExpression) {
					params.filter = filterExpression;
				}
				const res = await aggregateRecords(collection.name, params);
				const row: AggregationResult = res.results[0] ?? {};

				const cards: StatCard[] = [
					{ label: 'Total Records', value: formatNumber(row['count'] ?? row['count()']) },
				];
				for (const f of numericFields) {
					cards.push(
						{ label: `Sum of ${f.name}`, value: formatNumber(row[`sum_${f.name}`]) },
						{ label: `Avg of ${f.name}`, value: formatNumber(row[`avg_${f.name}`]) },
						{ label: `Min of ${f.name}`, value: formatNumber(row[`min_${f.name}`]) },
						{ label: `Max of ${f.name}`, value: formatNumber(row[`max_${f.name}`]) },
					);
				}
				setStats(cards);
			} catch {
				setError('Failed to load summary');
			} finally {
				setLoading(false);
			}
		};
		run();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [collection.name, filterExpression]);

	return (
		<div className="border rounded-lg overflow-hidden">
			{/* Header */}
			<Button
				variant="ghost"
				className="w-full flex items-center justify-between px-4 py-2 h-auto rounded-none bg-muted/40 hover:bg-muted/60"
				onClick={() => setOpen((v) => !v)}
			>
				<span className="flex items-center gap-2 text-sm font-medium">
					<BarChart2 className="h-4 w-4 text-primary" />
					Summary
					{filterExpression && (
						<span className="text-xs text-muted-foreground font-normal">(filtered)</span>
					)}
				</span>
				{open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
			</Button>

			{/* Body */}
			{open && (
				<div className="p-4">
					{error ? (
						<p className="text-sm text-muted-foreground">{error}</p>
					) : loading ? (
						<div className="grid grid-cols-2 md:grid-cols-4 gap-3">
							{Array.from({ length: Math.max(1, 1 + numericFields.length * 4) }).map((_, i) => (
								<Card key={i} className="shadow-none">
									<CardContent className="p-3 space-y-2">
										<Skeleton className="h-3 w-24" />
										<Skeleton className="h-5 w-16" />
									</CardContent>
								</Card>
							))}
						</div>
					) : (
						<div className="grid grid-cols-2 md:grid-cols-4 gap-3">
							{stats.map((card) => (
								<Card key={card.label} className="shadow-none">
									<CardContent className="p-3">
										<p className="text-xs text-muted-foreground truncate">{card.label}</p>
										<p className="text-lg font-semibold mt-1 truncate">{card.value}</p>
									</CardContent>
								</Card>
							))}
						</div>
					)}
				</div>
			)}
		</div>
	);
}
