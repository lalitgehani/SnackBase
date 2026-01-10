/**
 * Records table component
 * Dynamic table that renders columns based on collection schema
 */

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Eye, Pencil, Trash2 } from 'lucide-react';
import type { FieldDefinition } from '@/services/collections.service';
import type { RecordListItem } from '@/types/records.types';
import { shouldMaskField, maskPiiValue } from '@/lib/form-helpers';
import { DataTable, type Column, type DispatchPagination, type DispatchSorting } from '@/components/common/DataTable';
import { useAuthStore } from '@/stores/auth.store';


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

	// Pagination props
	totalItems: number;
	page: number;
	pageSize: number;
	onPageChange: (page: number) => void;
	onPageSizeChange: (pageSize: number) => void;
}

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
	totalItems,
	page,
	pageSize,
	onPageChange,
	onPageSizeChange,
}: RecordsTableProps) {

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

		// Handle reference fields
		if (field.type === 'reference') {
			return (
				<Badge variant="outline" className="font-mono text-xs">
					{String(value).slice(0, 8)}...
				</Badge>
			);
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

	// Limit number of visible columns to avoid horizontal scroll
	// Show first 5 schema fields plus system fields
	const MAX_SCHEMA_COLUMNS = 5;
	const visibleSchemaFields = schema.slice(0, MAX_SCHEMA_COLUMNS);
	const remainingFieldsCount = Math.max(0, schema.length - MAX_SCHEMA_COLUMNS);

	// Build dynamic columns
	const columns: Column<RecordListItem>[] = [
		...visibleSchemaFields.map((field) => ({
			header: field.name,
			accessorKey: field.name,
			sortable: true,
			render: (record: RecordListItem) => renderCellValue(record, field),
		})),
	];

	const { account } = useAuthStore();
	const isSuperadmin = account?.id === '00000000-0000-0000-0000-000000000000';

	if (isSuperadmin) {
		columns.unshift({
			header: 'Account',
			accessorKey: 'account_name',
			render: (record) => <span className="text-sm font-medium">{record.account_name || 'System'}</span>,
		});
	}


	if (remainingFieldsCount > 0) {
		columns.push({
			header: `+${remainingFieldsCount} more`,
			render: () => <span className="text-muted-foreground text-xs">...</span>,
			className: 'text-muted-foreground text-xs',
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
		/>
	);
}
