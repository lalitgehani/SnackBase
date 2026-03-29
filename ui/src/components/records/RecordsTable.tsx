/**
 * Records table component
 * Dynamic table that renders columns based on collection schema
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Eye, Pencil, Pin, PinOff, Trash2 } from 'lucide-react';
import type { FieldDefinition } from '@/services/collections.service';
import type { RecordData, RecordListItem } from '@/types/records.types';
import { shouldMaskField, maskPiiValue } from '@/lib/form-helpers';
import { DataTable, type Column, type DispatchPagination, type DispatchSorting } from '@/components/common/DataTable';
import { useAuthStore } from '@/stores/auth.store';
import { cn } from '@/lib/utils';


interface RecordsTableProps {
	records: RecordListItem[];
	schema: FieldDefinition[];
	sortBy: string;
	sortOrder: 'asc' | 'desc';
	onSort: (column: string) => void;
	onView: (record: RecordListItem) => void;
	onEdit: (record: RecordListItem) => void;
	onDelete: (record: RecordListItem) => void;
	hasPiiAccess?: boolean;
	referenceRecords?: Record<string, RecordData[]>;

	// Multi-select
	selectedIds?: Set<string>;
	onSelectionChange?: (ids: Set<string>) => void;

	// Pagination props
	totalItems: number;
	page: number;
	pageSize: number;
	onPageChange: (page: number) => void;
	onPageSizeChange: (pageSize: number) => void;

	// Cursor pagination props
	paginationMode?: 'page' | 'scroll';
	onPaginationModeChange?: (mode: 'page' | 'scroll') => void;
	hasMore?: boolean;
	onLoadMore?: () => void;
	isLoadingMore?: boolean;
	autoLoad?: boolean;
	onAutoLoadChange?: (enabled: boolean) => void;
	maxTableHeight?: string;
}

/** Returns the best display value for a referenced record. */
function getRefDisplayValue(record: RecordData): string {
	if (typeof record['name'] === 'string' && record['name']) return record['name'];
	const systemKeys = ['id', 'account_id', 'created_at', 'updated_at', 'created_by', 'updated_by'];
	const key = Object.keys(record).find(
		(k) => !systemKeys.includes(k) && typeof record[k] === 'string' && record[k],
	);
	if (key) return String(record[key]);
	return String(record.id ?? '').slice(0, 8) + '…';
}

/** Non-system fields of a record, up to `limit`. */
function getUserFields(record: RecordData, limit = 4): [string, unknown][] {
	const systemKeys = ['id', 'account_id', 'created_at', 'updated_at', 'created_by', 'updated_by'];
	return Object.entries(record)
		.filter(([key]) => !systemKeys.includes(key))
		.slice(0, limit);
}

// ---------------------------------------------------------------------------
// ReferenceCell — renders a single reference field cell
// ---------------------------------------------------------------------------

interface ReferenceCellProps {
	id: string;
	refRecord: RecordData | null;
}

function ReferenceCell({ id, refRecord }: ReferenceCellProps) {
	const [open, setOpen] = useState(false);

	if (!refRecord) {
		return (
			<div className="flex items-center gap-1">
				<span className="text-muted-foreground font-mono text-xs">{id.slice(0, 8)}…</span>
				<Badge variant="secondary" className="text-xs">Deleted</Badge>
			</div>
		);
	}

	const displayValue = getRefDisplayValue(refRecord);

	return (
		<Popover open={open} onOpenChange={setOpen}>
			<PopoverTrigger asChild>
				<button
					className="text-sm text-primary underline-offset-2 hover:underline cursor-pointer truncate max-w-[160px] text-left"
					title={displayValue}
				>
					{displayValue}
				</button>
			</PopoverTrigger>
			<PopoverContent className="w-64" align="start">
				<div className="space-y-2">
					<p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
						Referenced Record
					</p>
					<p className="font-mono text-xs text-muted-foreground break-all">{refRecord.id as string}</p>
					<div className="space-y-1 pt-1 border-t">
						{getUserFields(refRecord).map(([key, val]) => (
							<div key={key} className="flex justify-between gap-2 text-sm">
								<span className="text-muted-foreground shrink-0">{key}:</span>
								<span className="font-medium truncate max-w-[130px]">
									{val === null || val === undefined ? (
										<span className="italic text-muted-foreground">null</span>
									) : (
										String(val)
									)}
								</span>
							</div>
						))}
					</div>
				</div>
			</PopoverContent>
		</Popover>
	);
}

// ---------------------------------------------------------------------------
// RecordsTable
// ---------------------------------------------------------------------------

export default function RecordsTable({
	records,
	schema,
	sortBy,
	sortOrder,
	onSort,
	onView,
	onEdit,
	onDelete,
	hasPiiAccess = false,
	referenceRecords = {},
	selectedIds,
	onSelectionChange,
	totalItems,
	page,
	pageSize,
	onPageChange,
	onPageSizeChange,
	paginationMode = 'page',
	onPaginationModeChange,
	hasMore = false,
	onLoadMore,
	isLoadingMore = false,
	autoLoad = false,
	onAutoLoadChange,
	maxTableHeight = 'calc(100vh - 280px)',
}: RecordsTableProps) {

	const [pinnedColumns, setPinnedColumns] = useState<Set<string>>(new Set());

	const togglePin = (fieldName: string) => {
		setPinnedColumns(prev => {
			const next = new Set(prev);
			if (next.has(fieldName)) next.delete(fieldName);
			else next.add(fieldName);
			return next;
		});
	};

	const formatDate = (dateString: string) => {
		return new Date(dateString).toLocaleString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
		});
	};

	const renderCellValue = (record: RecordListItem, field: FieldDefinition) => {
		const value = record[field.name];

		// Handle null/undefined
		if (value === null || value === undefined) {
			return <span className="text-muted-foreground italic">null</span>;
		}

		// Handle PII masking
		if (shouldMaskField(field, hasPiiAccess)) {
			const maskedValue = maskPiiValue(String(value), field.mask_type || 'full');
			return (
				<span className="text-muted-foreground" title="PII masked">
					{maskedValue}
				</span>
			);
		}

		// Handle boolean
		if (field.type === 'boolean') {
			return value ? (
				<Badge variant="default">Yes</Badge>
			) : (
				<Badge variant="secondary">No</Badge>
			);
		}

		// Handle reference fields — show display value from cache
		if (field.type === 'reference') {
			const id = String(value);
			const collectionCache = referenceRecords[field.collection || ''] ?? [];
			const refRecord = collectionCache.find((r) => r.id === id) ?? null;
			return <ReferenceCell id={id} refRecord={refRecord} />;
		}

		// Handle JSON
		if (field.type === 'json') {
			const jsonStr = typeof value === 'string' ? value : JSON.stringify(value);
			const truncated = jsonStr.length > 50 ? jsonStr.slice(0, 50) + '...' : jsonStr;
			return <span className="font-mono text-xs">{truncated}</span>;
		}

		// Handle datetime
		if (field.type === 'datetime') {
			return <span className="text-sm">{formatDate(value as string)}</span>;
		}

		// Handle number
		if (field.type === 'number') {
			return <span className="font-mono">{value as React.ReactNode}</span>;
		}

		// Handle long text
		if (field.type === 'text' && String(value).length > 50) {
			return (
				<span className="text-sm" title={String(value)}>
					{String(value).slice(0, 50)}...
				</span>
			);
		}

		// Default text rendering
		return <span className="text-sm">{String(value)}</span>;
	};

	// Fixed width (px) for pinned columns — required for predictable sticky offsets
	const PINNED_COL_WIDTH = 160;
	// Width of the checkbox column when multi-select is active
	const CHECKBOX_COL_WIDTH = 44;

	// Multi-select derived state
	const isAllSelected = records.length > 0 && selectedIds !== undefined && selectedIds.size === records.length;
	const isIndeterminate = (selectedIds?.size ?? 0) > 0 && !isAllSelected;

	// Pinned fields in original schema order
	const pinnedFields = schema.filter(f => pinnedColumns.has(f.name));
	// Unpinned fields in original schema order
	const unpinnedFields = schema.filter(f => !pinnedColumns.has(f.name));
	// Render order: pinned first (original order), then unpinned
	const orderedFields = [...pinnedFields, ...unpinnedFields];

	// Extra left offset for pinned schema columns when the checkbox column is present
	const checkboxOffset = onSelectionChange ? CHECKBOX_COL_WIDTH : 0;

	// Build dynamic columns — all schema fields visible, pinned ones frozen left
	const columns: Column<RecordListItem>[] = orderedFields.map((field) => {
		const isPinned = pinnedColumns.has(field.name);
		const pinnedIndex = pinnedFields.findIndex(f => f.name === field.name);
		const isLastPinned = isPinned && pinnedIndex === pinnedFields.length - 1;

		return {
			header: field.name,
			accessorKey: field.name as keyof RecordListItem,
			sortable: true,
			frozen: isPinned ? 'left' : undefined,
			frozenOffset: isPinned ? checkboxOffset + pinnedIndex * PINNED_COL_WIDTH : undefined,
			frozenBorderRight: isLastPinned,
			style: isPinned
				? { minWidth: PINNED_COL_WIDTH, maxWidth: PINNED_COL_WIDTH }
				: { minWidth: 140 },
			headerSuffix: (
				<button
					onClick={(e) => { e.stopPropagation(); togglePin(field.name); }}
					className={cn(
						'ml-1 rounded p-0.5 transition-opacity',
						isPinned
							? 'text-primary opacity-100'
							: 'text-muted-foreground opacity-0 group-hover:opacity-100 hover:text-foreground'
					)}
					title={isPinned ? 'Unpin column' : 'Pin column'}
				>
					{isPinned ? <PinOff className="h-3 w-3" /> : <Pin className="h-3 w-3" />}
				</button>
			),
			render: (record: RecordListItem) => renderCellValue(record, field),
		};
	});

	const { account } = useAuthStore();
	const isSuperadmin = account?.id === '00000000-0000-0000-0000-000000000000';

	if (isSuperadmin) {
		columns.unshift({
			header: 'Account',
			accessorKey: 'account_name',
			render: (record) => <span className="text-sm font-medium">{record.account_name || 'System'}</span>,
		});
	}

	// Multi-select checkbox column — prepended as the very first column
	if (onSelectionChange) {
		columns.unshift({
			header: (
				<Checkbox
					checked={isIndeterminate ? 'indeterminate' : isAllSelected}
					onCheckedChange={(checked) => {
						onSelectionChange(checked ? new Set(records.map(r => r.id)) : new Set());
					}}
					aria-label="Select all"
				/>
			),
			frozen: 'left',
			frozenOffset: 0,
			frozenBorderRight: false,
			style: { minWidth: CHECKBOX_COL_WIDTH, maxWidth: CHECKBOX_COL_WIDTH, padding: '0 8px' },
			render: (record) => (
				<Checkbox
					checked={selectedIds?.has(record.id) ?? false}
					onCheckedChange={(checked) => {
						const next = new Set(selectedIds);
						if (checked) next.add(record.id);
						else next.delete(record.id);
						onSelectionChange(next);
					}}
					onClick={(e) => e.stopPropagation()}
					aria-label={`Select record ${record.id}`}
				/>
			),
		});
	}

	columns.push({
		header: 'Created',
		accessorKey: 'created_at',
		sortable: true,
		render: (record) => <span className="text-sm text-muted-foreground">{formatDate(record.created_at)}</span>,
	});

	columns.push({
		header: 'Actions',
		className: 'text-right',
		frozen: 'right',
		render: (record) => (
			<div className="flex justify-end gap-2">
				<Button
					variant="ghost"
					size="sm"
					onClick={() => onView(record)}
					title="View record"
				>
					<Eye className="h-4 w-4" />
				</Button>
				<Button
					variant="ghost"
					size="sm"
					onClick={() => onEdit(record)}
					title="Edit record"
				>
					<Pencil className="h-4 w-4" />
				</Button>
				<Button
					variant="ghost"
					size="sm"
					onClick={() => onDelete(record)}
					title="Delete record"
				>
					<Trash2 className="h-4 w-4 text-destructive" />
				</Button>
			</div>
		),
	});

	const pagination: DispatchPagination = {
		page,
		pageSize,
		onPageChange,
		onPageSizeChange,
	};

	const sorting: DispatchSorting = {
		sortBy,
		sortOrder,
		onSort,
	};

	return (
		<DataTable
			data={records}
			columns={columns}
			keyExtractor={(item) => item.id}
			pagination={pagination}
			sorting={sorting}
			totalItems={totalItems}
			noDataMessage="No records found. Create your first record to get started."
			paginationMode={paginationMode}
			onPaginationModeChange={onPaginationModeChange}
			hasMore={hasMore}
			onLoadMore={onLoadMore}
			isLoadingMore={isLoadingMore}
			autoLoad={autoLoad}
			onAutoLoadChange={onAutoLoadChange}
			showModeToggle={true}
			maxTableHeight={maxTableHeight}
		/>
	);
}
