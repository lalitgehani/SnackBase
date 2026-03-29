/**
 * Analytics Page
 * Group-by query builder with aggregation results table and CSV export.
 */

import { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router';
import { ArrowLeft, BarChart2, Play, Download, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import FilterBuilderPanel, {
	type FilterRow,
	compileFilterExpression,
} from '@/components/records/FilterBuilderPanel';
import { getCollectionByName, type Collection } from '@/services/collections.service';
import { aggregateRecords } from '@/services/records.service';
import type { AggregationResult } from '@/types/records.types';
import { handleApiError } from '@/lib/api';
import { useEffect } from 'react';

type AggFn = 'count' | 'sum' | 'avg' | 'min' | 'max';

interface FieldFunction {
	fn: AggFn;
	field?: string; // undefined for count()
}

function buildFunctionsParam(selected: FieldFunction[]): string {
	return selected
		.map(({ fn, field }) => (field ? `${fn}(${field})` : `${fn}()`))
		.join(',');
}

function resultKey(fn: AggFn, field?: string): string {
	if (!field) return 'count';
	return `${fn}_${field}`;
}

function formatValue(val: unknown): string {
	if (val === null || val === undefined) return '—';
	const n = Number(val);
	if (!isNaN(n) && typeof val !== 'boolean') {
		return n.toLocaleString(undefined, { maximumFractionDigits: 4 });
	}
	return String(val);
}

function exportCsv(columns: string[], rows: AggregationResult[], filename: string) {
	const header = columns.join(',');
	const body = rows
		.map((row) =>
			columns
				.map((col) => {
					const v = row[col];
					const s = v === null || v === undefined ? '' : String(v);
					return s.includes(',') || s.includes('"') ? `"${s.replace(/"/g, '""')}"` : s;
				})
				.join(','),
		)
		.join('\n');
	const blob = new Blob([`${header}\n${body}`], { type: 'text/csv' });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	a.click();
	URL.revokeObjectURL(url);
}

export default function AnalyticsPage() {
	const { collectionName } = useParams<{ collectionName: string }>();
	const navigate = useNavigate();

	const [collection, setCollection] = useState<Collection | null>(null);
	const [loadingCollection, setLoadingCollection] = useState(true);
	const [collectionError, setCollectionError] = useState<string | null>(null);

	// Filter state
	const [filterExpression, setFilterExpression] = useState('');
	const [appliedFilterRows, setAppliedFilterRows] = useState<FilterRow[]>([]);

	// Group by state
	const [groupByFields, setGroupByFields] = useState<string[]>([]);

	// Function selection: always include count; optionally per-field fns
	const [includeCount, setIncludeCount] = useState(true);
	const [numericFns, setNumericFns] = useState<Record<string, Set<AggFn>>>({});

	// Having clause
	const [having, setHaving] = useState('');

	// Results
	const [results, setResults] = useState<AggregationResult[] | null>(null);
	const [totalGroups, setTotalGroups] = useState(0);
	const [resultColumns, setResultColumns] = useState<string[]>([]);
	const [running, setRunning] = useState(false);
	const [runError, setRunError] = useState<string | null>(null);

	useEffect(() => {
		if (!collectionName) return;
		setLoadingCollection(true);
		getCollectionByName(collectionName)
			.then(setCollection)
			.catch((err) => setCollectionError(handleApiError(err)))
			.finally(() => setLoadingCollection(false));
	}, [collectionName]);

	const numericFields =
		collection?.schema?.filter((f) => f.type === 'number' || f.type === 'integer') ?? [];
	const allFields = collection?.schema ?? [];

	const toggleGroupBy = (field: string) => {
		setGroupByFields((prev) =>
			prev.includes(field) ? prev.filter((f) => f !== field) : [...prev, field],
		);
	};

	const toggleNumericFn = (fieldName: string, fn: AggFn) => {
		setNumericFns((prev) => {
			const current = new Set(prev[fieldName] ?? []);
			if (current.has(fn)) {
				current.delete(fn);
			} else {
				current.add(fn);
			}
			return { ...prev, [fieldName]: current };
		});
	};

	const handleRun = useCallback(async () => {
		if (!collectionName) return;

		const selected: FieldFunction[] = [];
		if (includeCount) selected.push({ fn: 'count' });
		for (const [field, fns] of Object.entries(numericFns)) {
			for (const fn of fns) {
				selected.push({ fn, field });
			}
		}

		if (selected.length === 0) {
			setRunError('Select at least one aggregation function.');
			return;
		}

		setRunning(true);
		setRunError(null);
		setResults(null);

		try {
			const params: Parameters<typeof aggregateRecords>[1] = {
				functions: buildFunctionsParam(selected),
			};
			if (groupByFields.length > 0) params.group_by = groupByFields.join(',');
			if (filterExpression) params.filter = filterExpression;
			if (having.trim()) params.having = having.trim();

			const res = await aggregateRecords(collectionName, params);
			setResults(res.results);
			setTotalGroups(res.total_groups);

			// Derive columns: group-by fields first, then aggregation result keys
			const aggKeys = selected.map(({ fn, field }) => resultKey(fn, field));
			setResultColumns([...groupByFields, ...aggKeys]);
		} catch (err) {
			setRunError(handleApiError(err));
		} finally {
			setRunning(false);
		}
	}, [collectionName, includeCount, numericFns, groupByFields, filterExpression, having]);

	const handleApplyFilters = (expression: string, rows: FilterRow[]) => {
		setFilterExpression(expression);
		setAppliedFilterRows(rows);
	};

	const handleClearFilters = () => {
		setFilterExpression('');
		setAppliedFilterRows([]);
	};

	const handleRemoveFilterPill = (id: string) => {
		if (!collection) return;
		const remaining = appliedFilterRows.filter((r) => r.id !== id);
		const expression = compileFilterExpression(remaining, collection.schema ?? []);
		setAppliedFilterRows(remaining);
		setFilterExpression(expression);
	};

	if (loadingCollection) {
		return (
			<div className="flex items-center justify-center py-20">
				<RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
			</div>
		);
	}

	if (collectionError || !collection) {
		return (
			<div className="space-y-4">
				<Button variant="ghost" size="sm" onClick={() => navigate(`/admin/collections/${collectionName}/records`)} className="gap-1">
					<ArrowLeft className="h-4 w-4" /> Records
				</Button>
				<p className="text-destructive">{collectionError ?? 'Collection not found'}</p>
			</div>
		);
	}

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex items-center justify-between">
				<div>
					<div className="flex items-center gap-2 mb-2">
						<Button
							variant="ghost"
							size="sm"
							onClick={() => navigate(`/admin/collections/${collectionName}/records`)}
							className="gap-1"
						>
							<ArrowLeft className="h-4 w-4" />
							Records
						</Button>
					</div>
					<h1 className="text-3xl font-bold flex items-center gap-2">
						<BarChart2 className="h-7 w-7 text-primary" />
						{collectionName} — Analytics
					</h1>
					<p className="text-muted-foreground mt-2">
						Group records and compute aggregations
					</p>
				</div>
			</div>

			<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
				{/* Left column: Filter + Group By Builder */}
				<div className="lg:col-span-1 space-y-4">
					{/* Filter Panel */}
					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="text-base">Filters</CardTitle>
							<CardDescription>Apply before aggregation</CardDescription>
						</CardHeader>
						<CardContent>
							<FilterBuilderPanel
								schema={collection.schema}
								appliedRows={appliedFilterRows}
								onApply={handleApplyFilters}
								onClear={handleClearFilters}
								onRemovePill={handleRemoveFilterPill}
							/>
						</CardContent>
					</Card>

					{/* Group By Builder */}
					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="text-base">Group By</CardTitle>
							<CardDescription>Select fields to group results</CardDescription>
						</CardHeader>
						<CardContent className="space-y-2">
							{allFields.length === 0 ? (
								<p className="text-sm text-muted-foreground">No fields available</p>
							) : (
								allFields.map((f) => (
									<div key={f.name} className="flex items-center gap-2">
										<Checkbox
											id={`gb-${f.name}`}
											checked={groupByFields.includes(f.name)}
											onCheckedChange={() => toggleGroupBy(f.name)}
										/>
										<Label htmlFor={`gb-${f.name}`} className="cursor-pointer font-mono text-sm">
											{f.name}
										</Label>
										<Badge variant="outline" className="text-xs ml-auto">{f.type}</Badge>
									</div>
								))
							)}
						</CardContent>
					</Card>

					{/* Aggregation Functions */}
					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="text-base">Aggregation Functions</CardTitle>
							<CardDescription>Choose what to compute</CardDescription>
						</CardHeader>
						<CardContent className="space-y-4">
							{/* Count */}
							<div className="flex items-center gap-2">
								<Checkbox
									id="fn-count"
									checked={includeCount}
									onCheckedChange={(v) => setIncludeCount(!!v)}
								/>
								<Label htmlFor="fn-count" className="cursor-pointer font-mono text-sm">
									count()
								</Label>
							</div>

							{/* Per-numeric-field functions */}
							{numericFields.map((f) => (
								<div key={f.name} className="space-y-1">
									<p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
										{f.name}
									</p>
									{(['sum', 'avg', 'min', 'max'] as AggFn[]).map((fn) => (
										<div key={fn} className="flex items-center gap-2 pl-2">
											<Checkbox
												id={`fn-${fn}-${f.name}`}
												checked={numericFns[f.name]?.has(fn) ?? false}
												onCheckedChange={() => toggleNumericFn(f.name, fn)}
											/>
											<Label
												htmlFor={`fn-${fn}-${f.name}`}
												className="cursor-pointer font-mono text-sm"
											>
												{fn}({f.name})
											</Label>
										</div>
									))}
								</div>
							))}

							{numericFields.length === 0 && (
								<p className="text-sm text-muted-foreground">
									No numeric fields — only count() is available
								</p>
							)}
						</CardContent>
					</Card>

					{/* Having */}
					<Card>
						<CardHeader className="pb-3">
							<CardTitle className="text-base">Having</CardTitle>
							<CardDescription>Filter aggregated results</CardDescription>
						</CardHeader>
						<CardContent>
							<Input
								value={having}
								onChange={(e) => setHaving(e.target.value)}
								placeholder='e.g. count() > 5'
								className="font-mono text-sm"
							/>
						</CardContent>
					</Card>

					<Button onClick={handleRun} disabled={running} className="w-full gap-2">
						{running ? (
							<RefreshCw className="h-4 w-4 animate-spin" />
						) : (
							<Play className="h-4 w-4" />
						)}
						Run
					</Button>

					{runError && (
						<p className="text-sm text-destructive">{runError}</p>
					)}
				</div>

				{/* Right column: Results */}
				<div className="lg:col-span-2">
					<Card className="h-full">
						<CardHeader>
							<div className="flex items-center justify-between">
								<div>
									<CardTitle className="text-base">Results</CardTitle>
									{results !== null && (
										<CardDescription>
											{totalGroups} group{totalGroups !== 1 ? 's' : ''}
										</CardDescription>
									)}
								</div>
								{results && results.length > 0 && (
									<Button
										variant="outline"
										size="sm"
										className="gap-2"
										onClick={() =>
											exportCsv(
												resultColumns,
												results,
												`${collectionName}-analytics.csv`,
											)
										}
									>
										<Download className="h-4 w-4" />
										Export CSV
									</Button>
								)}
							</div>
						</CardHeader>
						<CardContent>
							{results === null && !running && (
								<div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
									<BarChart2 className="h-12 w-12 opacity-30" />
									<p className="text-sm">Configure options and click Run</p>
								</div>
							)}

							{running && (
								<div className="flex items-center justify-center py-20">
									<RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
								</div>
							)}

							{results !== null && !running && results.length === 0 && (
								<div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
									<p className="text-sm">No results</p>
								</div>
							)}

							{results !== null && !running && results.length > 0 && (
								<div className="overflow-x-auto">
									<Table>
										<TableHeader>
											<TableRow>
												{resultColumns.map((col) => (
													<TableHead key={col} className="font-mono text-xs whitespace-nowrap">
														{col}
													</TableHead>
												))}
											</TableRow>
										</TableHeader>
										<TableBody>
											{results.map((row, i) => (
												<TableRow key={i}>
													{resultColumns.map((col) => (
														<TableCell key={col} className="font-mono text-sm whitespace-nowrap">
															{formatValue(row[col])}
														</TableCell>
													))}
												</TableRow>
											))}
										</TableBody>
									</Table>
								</div>
							)}
						</CardContent>
					</Card>
				</div>
			</div>
		</div>
	);
}
