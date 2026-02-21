/**
 * View record dialog component
 * Read-only display of a single record
 */

import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { FieldDefinition } from '@/services/collections.service';
import type { RecordData } from '@/types/records.types';
import { shouldMaskField, maskPiiValue } from '@/lib/form-helpers';

interface ViewRecordDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	schema: FieldDefinition[];
	collectionName: string;
	record: RecordData | null;
	hasPiiAccess?: boolean;
}

export default function ViewRecordDialog({
	open,
	onOpenChange,
	schema,
	collectionName,
	record,
	hasPiiAccess = false,
}: ViewRecordDialogProps) {
	const formatDate = (dateString: string) => {
		return new Date(dateString).toLocaleString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit',
		});
	};

	const renderFieldValue = (field: FieldDefinition, value: unknown) => {
		if (value === null || value === undefined || value === '') {
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
					{String(value)}
				</Badge>
			);
		}

		// Handle JSON
		if (field.type === 'json') {
			const jsonStr = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
			return (
				<pre className="bg-muted p-2 rounded text-xs font-mono overflow-x-auto">
					{jsonStr}
				</pre>
			);
		}

		// Handle datetime
		if (field.type === 'datetime') {
			return <span className="text-sm">{typeof value === 'string' ? formatDate(value) : String(value)}</span>;
		}

		// Handle number
		if (field.type === 'number') {
			return <span className="font-mono">{String(value)}</span>;
		}

		// Default text rendering
		return <span className="text-sm break-all">{String(value)}</span>;
	};

	return (
		<AppDialog
			open={open}
			onOpenChange={onOpenChange}
			title="Record Details"
			description={
				<>
					Viewing record from <strong>{collectionName}</strong> collection
					{record && (
						<span className="ml-2 font-mono text-xs text-muted-foreground">
							(ID: {(record.id as string)?.slice(0, 8)}...)
						</span>
					)}
				</>
			}
			className="max-w-2xl"
			footer={<Button onClick={() => onOpenChange(false)}>Close</Button>}
		>
			{!record ? (
				<div className="py-8 text-center text-muted-foreground">
					No record data available
				</div>
			) : (
				<div className="max-h-[60vh] overflow-y-auto">
					{/* Schema Fields */}
					<div className="space-y-4 pb-4">
						{schema.map((field) => (
							<div key={field.name} className="border-b pb-3 last:border-0">
								<div className="flex items-center gap-2 mb-1">
									<span className="font-medium text-sm">{field.name}</span>
									{field.required && (
										<span className="text-destructive text-xs">*</span>
									)}
									{field.unique && (
										<Badge variant="outline" className="text-xs">
											Unique
										</Badge>
									)}
									{field.pii && (
										<Badge variant="secondary" className="text-xs">
											PII
										</Badge>
									)}
									<Badge variant="outline" className="text-xs">
										{field.type}
									</Badge>
								</div>
								<div className="pl-4">{renderFieldValue(field, record[field.name])}</div>
							</div>
						))}
					</div>

					{/* System Fields */}
					<div className="bg-muted/50 rounded-lg p-4 space-y-2">
						<p className="text-xs font-semibold text-muted-foreground uppercase">
							System Fields
						</p>
						<div className="grid grid-cols-2 gap-4 text-sm">
							<div>
								<span className="text-muted-foreground">ID:</span>{' '}
								<span className="font-mono text-xs">{record.id as React.ReactNode}</span>
							</div>
							<div>
								<span className="text-muted-foreground">Account ID:</span>{' '}
								<span className="font-mono text-xs">{record.account_id as React.ReactNode}</span>
							</div>
							<div>
								<span className="text-muted-foreground">Created:</span>{' '}
								<span>{formatDate(record.created_at as string)}</span>
							</div>
							<div>
								<span className="text-muted-foreground">Updated:</span>{' '}
								<span>{formatDate(record.updated_at as string)}</span>
							</div>
							<div>
								<span className="text-muted-foreground">Created By:</span>{' '}
								<span className="font-mono text-xs">{record.created_by as React.ReactNode}</span>
							</div>
							<div>
								<span className="text-muted-foreground">Updated By:</span>{' '}
								<span className="font-mono text-xs">{record.updated_by as React.ReactNode}</span>
							</div>
						</div>
					</div>
				</div>
			)}
		</AppDialog>
	);
}
