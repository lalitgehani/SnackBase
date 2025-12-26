/**
 * Delete record dialog component
 * Confirmation dialog for deleting a record
 */

import { useState } from 'react';
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { AlertTriangle } from 'lucide-react';
import type { FieldDefinition } from '@/services/collections.service';
import type { RecordData } from '@/types/records.types';
import { formatFieldValue } from '@/lib/form-helpers';

interface DeleteRecordDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	onConfirm: (recordId: string) => Promise<void>;
	schema: FieldDefinition[];
	collectionName: string;
	record: RecordData | null;
	recordId: string;
}

export default function DeleteRecordDialog({
	open,
	onOpenChange,
	onConfirm,
	schema,
	collectionName,
	record,
	recordId,
}: DeleteRecordDialogProps) {
	const [isDeleting, setIsDeleting] = useState(false);

	const handleConfirm = async () => {
		setIsDeleting(true);
		try {
			await onConfirm(recordId);
			onOpenChange(false);
		} finally {
			setIsDeleting(false);
		}
	};

	// Get a summary of the record (first few fields)
	const recordSummary = record ? (
		<div className="space-y-1">
			{schema.slice(0, 4).map((field) => (
				<div key={field.name} className="text-sm">
					<span className="text-muted-foreground">{field.name}:</span>{' '}
					<span className="font-medium">
						{formatFieldValue(record[field.name], field.type)}
					</span>
				</div>
			))}
			{schema.length > 4 && (
				<div className="text-sm text-muted-foreground italic">
					...and {schema.length - 4} more fields
				</div>
			)}
		</div>
	) : null;

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="max-w-md">
				<DialogHeader>
					<DialogTitle>Delete Record</DialogTitle>
					<DialogDescription>
						Are you sure you want to delete this record from{' '}
						<strong>{collectionName}</strong>? This action cannot be undone.
					</DialogDescription>
				</DialogHeader>

				<div className="space-y-4">
					<div className="flex items-start gap-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900 rounded-lg p-4">
						<AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-500 flex-shrink-0 mt-0.5" />
						<div className="text-sm text-amber-900 dark:text-amber-200">
							<strong>Warning:</strong> Deleting this record will permanently remove it from the
							database. If other records reference this record, they may be affected depending
							on the cascade delete settings.
						</div>
					</div>

					{recordSummary && (
						<div className="bg-muted rounded-lg p-4">
							<p className="text-xs text-muted-foreground mb-2 uppercase font-semibold">
								Record to delete:
							</p>
							{recordSummary}
							<div className="mt-2 text-xs text-muted-foreground font-mono">
								ID: {recordId.slice(0, 16)}...
							</div>
						</div>
					)}
				</div>

				<DialogFooter>
					<Button
						type="button"
						variant="outline"
						onClick={() => onOpenChange(false)}
						disabled={isDeleting}
					>
						Cancel
					</Button>
					<Button variant="destructive" onClick={handleConfirm} disabled={isDeleting}>
						{isDeleting ? 'Deleting...' : 'Delete Record'}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
