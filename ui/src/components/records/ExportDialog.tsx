/**
 * Bulk export dialog
 * Exports current filtered or all records as a JSON file
 */

import { useState } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';
import { getRecords } from '@/services/records.service';

interface ExportDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	collection: string;
	filterExpression: string;
	total: number;
}

export default function ExportDialog({
	open,
	onOpenChange,
	collection,
	filterExpression,
	total,
}: ExportDialogProps) {
	const [exportAll, setExportAll] = useState(false);
	const [isExporting, setIsExporting] = useState(false);

	const handleClose = (open: boolean) => {
		if (!open) {
			setExportAll(false);
			setIsExporting(false);
		}
		onOpenChange(open);
	};

	const handleExport = async () => {
		setIsExporting(true);
		try {
			const allRecords = [];
			let skip = 0;
			const pageSize = 100; // API max is 100 (le=100 in backend)
			const filterToUse = exportAll ? '' : filterExpression;

			while (true) {
				const res = await getRecords({
					collection,
					skip,
					limit: pageSize,
					...(filterToUse ? { filter: filterToUse } : {}),
				});
				allRecords.push(...res.items);
				skip += res.items.length;
				if (skip >= res.total) break;
			}

			const blob = new Blob([JSON.stringify(allRecords, null, 2)], {
				type: 'application/json',
			});
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `${collection}-export-${new Date().toISOString().slice(0, 10)}.json`;
			a.click();
			URL.revokeObjectURL(url);
			handleClose(false);
		} finally {
			setIsExporting(false);
		}
	};

	const hasFilter = Boolean(filterExpression);
	const exportCount = exportAll || !hasFilter ? total : total;

	return (
		<AppDialog
			open={open}
			onOpenChange={handleClose}
			title="Export Records"
			footer={
				<>
					<Button variant="outline" onClick={() => handleClose(false)} disabled={isExporting}>
						Cancel
					</Button>
					<Button onClick={handleExport} disabled={isExporting} className="gap-2">
						<Download className="h-4 w-4" />
						{isExporting ? 'Exporting…' : `Export ${exportCount} Record${exportCount === 1 ? '' : 's'}`}
					</Button>
				</>
			}
		>
			<div className="space-y-4">
				<p className="text-sm text-muted-foreground">
					Export records from <strong>{collection}</strong> as a JSON file.
				</p>

				{hasFilter ? (
					<div className="space-y-2">
						<p className="text-sm font-medium">What to export:</p>
						<label className="flex items-center gap-3 cursor-pointer rounded-lg border p-3 hover:bg-muted/50 transition-colors">
							<input
								type="radio"
								name="export-scope"
								checked={!exportAll}
								onChange={() => setExportAll(false)}
								className="accent-primary"
							/>
							<div>
								<p className="text-sm font-medium">Filtered records ({total})</p>
								<p className="text-xs text-muted-foreground font-mono truncate max-w-xs">
									{filterExpression}
								</p>
							</div>
						</label>
						<label className="flex items-center gap-3 cursor-pointer rounded-lg border p-3 hover:bg-muted/50 transition-colors">
							<input
								type="radio"
								name="export-scope"
								checked={exportAll}
								onChange={() => setExportAll(true)}
								className="accent-primary"
							/>
							<div>
								<p className="text-sm font-medium">All records</p>
								<p className="text-xs text-muted-foreground">
									Ignore the current filter and export everything
								</p>
							</div>
						</label>
					</div>
				) : (
					<p className="text-sm">
						All <strong>{total}</strong> record{total === 1 ? '' : 's'} will be exported.
					</p>
				)}

				<p className="text-xs text-muted-foreground">
					The file will be saved as{' '}
					<span className="font-mono">{collection}-export-{new Date().toISOString().slice(0, 10)}.json</span>
				</p>
			</div>
		</AppDialog>
	);
}
