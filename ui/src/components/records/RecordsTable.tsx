/**
 * Records table component
 * Dynamic table that renders columns based on collection schema
 */

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Eye, Pencil, Trash2, ArrowUp, ArrowDown } from 'lucide-react';
import type { FieldDefinition } from '@/services/collections.service';
import type { RecordListItem } from '@/types/records.types';
import { shouldMaskField, maskPiiValue } from '@/lib/form-helpers';

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
}: RecordsTableProps) {
	const SortIcon = ({ column }: { column: string }) => {
		if (sortBy !== column) return null;
		return sortOrder === 'asc' ? (
			<ArrowUp className="h-3 w-3 inline ml-1" />
		) : (
			<ArrowDown className="h-3 w-3 inline ml-1" />
		);
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
			return <span className="text-sm">{formatDate(value)}</span>;
		}

		// Handle number
		if (field.type === 'number') {
			return <span className="font-mono">{value}</span>;
		}

		// Handle long text
		if (field.type === 'text' && String(value).length > 50) {
			return (
				<span className="text-sm" title={value}>
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

	return (
		<div className="border rounded-lg">
			<Table>
				<TableHeader>
					<TableRow>
						{visibleSchemaFields.map((field) => (
							<TableHead
								key={field.name}
								className="cursor-pointer hover:bg-muted/50"
								onClick={() => onSort(field.name)}
							>
								{field.name} <SortIcon column={field.name} />
							</TableHead>
						))}
						{remainingFieldsCount > 0 && (
							<TableHead className="text-muted-foreground text-xs">
								+{remainingFieldsCount} more
							</TableHead>
						)}
						<TableHead
							className="cursor-pointer hover:bg-muted/50"
							onClick={() => onSort('created_at')}
						>
							Created <SortIcon column="created_at" />
						</TableHead>
						<TableHead className="text-right">Actions</TableHead>
					</TableRow>
				</TableHeader>
				<TableBody>
					{records.length === 0 ? (
						<TableRow>
							<TableCell
								colSpan={visibleSchemaFields.length + (remainingFieldsCount > 0 ? 1 : 0) + 2}
								className="text-center text-muted-foreground py-8"
							>
								No records found. Create your first record to get started.
							</TableCell>
						</TableRow>
					) : (
						records.map((record) => (
							<TableRow key={record.id}>
								{visibleSchemaFields.map((field) => (
									<TableCell key={field.name}>
										{renderCellValue(record, field)}
									</TableCell>
								))}
								{remainingFieldsCount > 0 && (
									<TableCell className="text-muted-foreground text-xs">
										...
									</TableCell>
								)}
								<TableCell className="text-sm text-muted-foreground">
									{formatDate(record.created_at)}
								</TableCell>
								<TableCell className="text-right">
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
								</TableCell>
							</TableRow>
						))
					)}
				</TableBody>
			</Table>
		</div>
	);
}
