/**
 * Bulk delete confirmation dialog
 * Confirms deletion of multiple selected records
 */

import { useState } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { AlertTriangle } from 'lucide-react';

interface BulkDeleteConfirmDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	onConfirm: () => Promise<void>;
	count: number;
	collectionName: string;
}

export default function BulkDeleteConfirmDialog({
	open,
	onOpenChange,
	onConfirm,
	count,
	collectionName,
}: BulkDeleteConfirmDialogProps) {
	const [isDeleting, setIsDeleting] = useState(false);

	const handleConfirm = async () => {
		setIsDeleting(true);
		try {
			await onConfirm();
			onOpenChange(false);
		} finally {
			setIsDeleting(false);
		}
	};

	return (
		<AppDialog
			open={open}
			onOpenChange={onOpenChange}
			title={`Delete ${count} Record${count === 1 ? '' : 's'}`}
			description={
				<>
					Are you sure you want to delete {count} record{count === 1 ? '' : 's'} from{' '}
					<strong>{collectionName}</strong>? This action cannot be undone.
				</>
			}
			footer={
				<>
					<Button
						type="button"
						variant="outline"
						onClick={() => onOpenChange(false)}
						disabled={isDeleting}
					>
						Cancel
					</Button>
					<Button variant="destructive" onClick={handleConfirm} disabled={isDeleting}>
						{isDeleting ? 'Deleting...' : `Delete ${count} Record${count === 1 ? '' : 's'}`}
					</Button>
				</>
			}
		>
			<div className="flex items-start gap-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900 rounded-lg p-4">
				<AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-500 flex-shrink-0 mt-0.5" />
				<div className="text-sm text-amber-900 dark:text-amber-200">
					<strong>Warning:</strong> This will permanently delete{' '}
					<strong>{count} record{count === 1 ? '' : 's'}</strong> from{' '}
					<strong>{collectionName}</strong>. This operation is atomic — all records will be
					deleted together or none will be deleted if an error occurs.
				</div>
			</div>
		</AppDialog>
	);
}
