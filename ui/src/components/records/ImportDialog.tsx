/**
 * Bulk import dialog
 * Imports records from a JSON file with preview, validation, and progress tracking
 */

import { useRef, useState } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { AlertTriangle, CheckCircle2, Upload, XCircle } from 'lucide-react';
import type { FieldDefinition } from '@/services/collections.service';
import type { RecordData, BatchValidationError } from '@/types/records.types';
import { batchCreateRecords } from '@/services/records.service';

type Stage = 'idle' | 'preview' | 'importing' | 'done' | 'error';

const CHUNK_SIZE = 100;

interface ImportDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	collection: string;
	schema: FieldDefinition[];
	onSuccess: (count: number) => void;
}

export default function ImportDialog({
	open,
	onOpenChange,
	collection,
	schema,
	onSuccess,
}: ImportDialogProps) {
	const fileInputRef = useRef<HTMLInputElement>(null);
	const [stage, setStage] = useState<Stage>('idle');
	const [records, setRecords] = useState<RecordData[]>([]);
	const [parseError, setParseError] = useState<string | null>(null);
	const [progress, setProgress] = useState(0);
	const [importedCount, setImportedCount] = useState(0);
	const [batchError, setBatchError] = useState<BatchValidationError | null>(null);

	const resetState = () => {
		setStage('idle');
		setRecords([]);
		setParseError(null);
		setProgress(0);
		setImportedCount(0);
		setBatchError(null);
		if (fileInputRef.current) fileInputRef.current.value = '';
	};

	const handleClose = (open: boolean) => {
		if (!open) resetState();
		onOpenChange(open);
	};

	const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const file = e.target.files?.[0];
		if (!file) return;

		setParseError(null);
		const reader = new FileReader();
		reader.onload = (ev) => {
			try {
				const parsed = JSON.parse(ev.target?.result as string);
				if (!Array.isArray(parsed)) {
					setParseError('File must contain a JSON array of records.');
					return;
				}
				setRecords(parsed as RecordData[]);
				setStage('preview');
			} catch {
				setParseError('Invalid JSON file. Please check the file format.');
			}
		};
		reader.readAsText(file);
	};

	const handleImport = async () => {
		setStage('importing');
		setProgress(0);
		setBatchError(null);

		const chunks: RecordData[][] = [];
		for (let i = 0; i < records.length; i += CHUNK_SIZE) {
			chunks.push(records.slice(i, i + CHUNK_SIZE));
		}

		let imported = 0;
		try {
			for (const chunk of chunks) {
				const result = await batchCreateRecords(collection, chunk);
				imported += result.count;
				setProgress(imported / records.length);
			}
			setImportedCount(imported);
			setStage('done');
			onSuccess(imported);
		} catch (err: unknown) {
			const data = (err as { response?: { data?: BatchValidationError } })?.response?.data;
			if (data && typeof data === 'object' && 'index' in data) {
				setBatchError(data as BatchValidationError);
			}
			setStage('error');
		}
	};

	const schemaFieldNames = schema.map((f) => f.name);
	const previewRecords = records.slice(0, 5);

	return (
		<AppDialog
			open={open}
			onOpenChange={handleClose}
			title="Import Records"
			className="sm:max-w-2xl"
			footer={
				stage === 'idle' ? (
					<Button variant="outline" onClick={() => handleClose(false)}>
						Cancel
					</Button>
				) : stage === 'preview' ? (
					<>
						<Button variant="outline" onClick={resetState}>
							Back
						</Button>
						<Button onClick={handleImport} disabled={records.length === 0}>
							Import {records.length} Record{records.length === 1 ? '' : 's'}
						</Button>
					</>
				) : stage === 'done' || stage === 'error' ? (
					<Button onClick={() => handleClose(false)}>Close</Button>
				) : null
			}
		>
			{/* idle: file picker */}
			{stage === 'idle' && (
				<div className="space-y-4">
					<p className="text-sm text-muted-foreground">
						Upload a JSON file containing an array of records to import into{' '}
						<strong>{collection}</strong>. Each record should match the collection schema.
					</p>

					{parseError && (
						<div className="flex items-start gap-2 text-sm text-destructive bg-destructive/10 rounded-lg p-3">
							<XCircle className="h-4 w-4 mt-0.5 shrink-0" />
							{parseError}
						</div>
					)}

					<div
						className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
						onClick={() => fileInputRef.current?.click()}
					>
						<Upload className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
						<p className="text-sm font-medium">Click to select a JSON file</p>
						<p className="text-xs text-muted-foreground mt-1">Accepts .json files</p>
						<input
							ref={fileInputRef}
							type="file"
							accept=".json,application/json"
							className="hidden"
							onChange={handleFileChange}
						/>
					</div>

					<div className="bg-muted rounded-lg p-3 text-xs text-muted-foreground">
						<p className="font-semibold mb-1">Expected format:</p>
						<pre className="font-mono">{`[
  { "${schemaFieldNames[0] ?? 'field1'}": "value1", ... },
  { "${schemaFieldNames[0] ?? 'field1'}": "value2", ... }
]`}</pre>
					</div>
				</div>
			)}

			{/* preview */}
			{stage === 'preview' && (
				<div className="space-y-4">
					<div className="flex items-center gap-2 text-sm">
						<CheckCircle2 className="h-4 w-4 text-green-600" />
						<span>
							<strong>{records.length}</strong> record{records.length === 1 ? '' : 's'} ready to import
						</span>
					</div>

					{/* Field mapping */}
					<div>
						<p className="text-xs font-semibold uppercase text-muted-foreground mb-2">
							Field mapping ({collection})
						</p>
						<div className="flex flex-wrap gap-2">
							{schemaFieldNames.map((name) => (
								<span key={name} className="text-xs bg-muted rounded px-2 py-0.5 font-mono">
									{name}
								</span>
							))}
						</div>
					</div>

					{/* Preview of first 5 records */}
					<div>
						<p className="text-xs font-semibold uppercase text-muted-foreground mb-2">
							Preview (first {previewRecords.length} of {records.length})
						</p>
						<div className="space-y-2 max-h-48 overflow-y-auto">
							{previewRecords.map((rec, i) => (
								<div key={i} className="bg-muted rounded p-2 text-xs font-mono break-all">
									{JSON.stringify(rec, null, 2).slice(0, 200)}
									{JSON.stringify(rec).length > 200 ? '…' : ''}
								</div>
							))}
						</div>
					</div>

					<div className="flex items-start gap-2 text-sm text-muted-foreground bg-muted rounded-lg p-3">
						<AlertTriangle className="h-4 w-4 mt-0.5 shrink-0 text-amber-600" />
						All {records.length} records will be imported atomically per batch of {CHUNK_SIZE}.
						If any record in a batch fails validation, that batch will be rolled back.
					</div>
				</div>
			)}

			{/* importing */}
			{stage === 'importing' && (
				<div className="space-y-4 py-4">
					<p className="text-sm text-center font-medium">Importing records…</p>
					<div className="w-full bg-muted rounded-full h-2 overflow-hidden">
						<div
							className="bg-primary h-2 rounded-full transition-all duration-300"
							style={{ width: `${Math.round(progress * 100)}%` }}
						/>
					</div>
					<p className="text-xs text-center text-muted-foreground">
						{Math.round(progress * records.length)} / {records.length} records
					</p>
				</div>
			)}

			{/* done */}
			{stage === 'done' && (
				<div className="flex flex-col items-center gap-3 py-6">
					<CheckCircle2 className="h-10 w-10 text-green-600" />
					<p className="text-base font-semibold">Import complete</p>
					<p className="text-sm text-muted-foreground">
						{importedCount} record{importedCount === 1 ? '' : 's'} imported successfully into{' '}
						<strong>{collection}</strong>.
					</p>
				</div>
			)}

			{/* error */}
			{stage === 'error' && (
				<div className="space-y-4">
					<div className="flex items-start gap-2 bg-destructive/10 rounded-lg p-4">
						<XCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
						<div className="space-y-1">
							<p className="text-sm font-semibold text-destructive">Import failed</p>
							{batchError ? (
								<>
									<p className="text-xs text-muted-foreground">
										Validation error at record index <strong>{batchError.index}</strong>:
									</p>
									<ul className="list-disc list-inside space-y-0.5">
										{batchError.details.map((d, i) => (
											<li key={i} className="text-xs">
												<span className="font-mono font-medium">{d.field ?? 'unknown'}</span>:{' '}
												{d.message}
											</li>
										))}
									</ul>
								</>
							) : (
								<p className="text-xs text-muted-foreground">
									An unexpected error occurred. Please try again.
								</p>
							)}
						</div>
					</div>
					<Button variant="outline" size="sm" onClick={resetState} className="w-full">
						Try again
					</Button>
				</div>
			)}
		</AppDialog>
	);
}
