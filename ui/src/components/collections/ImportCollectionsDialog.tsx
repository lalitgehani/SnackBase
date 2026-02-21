/**
 * Import Collections Dialog Component
 * Multi-step dialog for importing collections from JSON export file
 */

import { useState, useCallback } from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Upload, FileJson, CheckCircle2, XCircle, AlertCircle, SkipForward } from 'lucide-react';
import {
    importCollections,
    IMPORT_STRATEGY_OPTIONS,
    type CollectionExportData,
    type ImportStrategy,
    type CollectionImportResult,
} from '@/services/collections.service';
import { handleApiError } from '@/lib/api';

interface ImportCollectionsDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess: () => void;
}

type DialogStep = 'upload' | 'preview' | 'importing' | 'results';

export default function ImportCollectionsDialog({
    open,
    onOpenChange,
    onSuccess,
}: ImportCollectionsDialogProps) {
    const [step, setStep] = useState<DialogStep>('upload');
    const [exportData, setExportData] = useState<CollectionExportData | null>(null);
    const [strategy, setStrategy] = useState<ImportStrategy>('error');
    const [isImporting, setIsImporting] = useState(false);
    const [importResult, setImportResult] = useState<CollectionImportResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [dragActive, setDragActive] = useState(false);

    const resetState = useCallback(() => {
        setStep('upload');
        setExportData(null);
        setStrategy('error');
        setIsImporting(false);
        setImportResult(null);
        setError(null);
        setDragActive(false);
    }, []);

    const handleOpenChange = (newOpen: boolean) => {
        if (!newOpen) {
            resetState();
        }
        onOpenChange(newOpen);
    };

    const handleFileSelect = async (file: File) => {
        setError(null);

        if (!file.name.endsWith('.json')) {
            setError('Please select a JSON file');
            return;
        }

        try {
            const text = await file.text();
            const data = JSON.parse(text) as CollectionExportData;

            // Validate basic structure
            if (!data.version || !data.collections || !Array.isArray(data.collections)) {
                setError('Invalid export file format');
                return;
            }

            setExportData(data);
            setStep('preview');
        } catch (err) {
            setError('Failed to parse JSON file');
        }
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        const file = e.dataTransfer.files?.[0];
        if (file) {
            handleFileSelect(file);
        }
    };

    const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            handleFileSelect(file);
        }
    };

    const handleImport = async () => {
        if (!exportData) return;

        setStep('importing');
        setIsImporting(true);
        setError(null);

        try {
            const result = await importCollections(exportData, strategy);
            setImportResult(result);
            setStep('results');

            if (result.imported_count > 0 || result.updated_count > 0) {
                onSuccess();
            }
        } catch (err) {
            setError(handleApiError(err));
            setStep('preview');
        } finally {
            setIsImporting(false);
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'imported':
                return <CheckCircle2 className="h-4 w-4 text-green-500" />;
            case 'updated':
                return <CheckCircle2 className="h-4 w-4 text-blue-500" />;
            case 'skipped':
                return <SkipForward className="h-4 w-4 text-yellow-500" />;
            case 'error':
                return <XCircle className="h-4 w-4 text-red-500" />;
            default:
                return <AlertCircle className="h-4 w-4 text-muted-foreground" />;
        }
    };

    const description =
        step === 'upload' ? 'Upload a collections export JSON file' :
        step === 'preview' ? 'Review collections and select import options' :
        step === 'importing' ? 'Importing collections...' :
        'Import completed';

    const footer =
        step === 'upload' ? (
            <Button variant="outline" onClick={() => handleOpenChange(false)}>
                Cancel
            </Button>
        ) : step === 'preview' ? (
            <>
                <Button variant="outline" onClick={() => setStep('upload')}>
                    Back
                </Button>
                <Button onClick={handleImport} disabled={isImporting}>
                    Import Collections
                </Button>
            </>
        ) : step === 'results' ? (
            <>
                <Button variant="outline" onClick={resetState}>
                    Import Another
                </Button>
                <Button onClick={() => handleOpenChange(false)}>
                    Done
                </Button>
            </>
        ) : undefined;

    return (
        <AppDialog
            open={open}
            onOpenChange={handleOpenChange}
            title="Import Collections"
            description={description}
            className="max-w-xl"
            footer={footer}
        >
            {/* Upload Step */}
            {step === 'upload' && (
                <div className="space-y-4">
                    <div
                        className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${dragActive
                            ? 'border-primary bg-primary/5'
                            : 'border-muted-foreground/25 hover:border-muted-foreground/50'
                            }`}
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                    >
                        <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                        <p className="text-lg font-medium mb-2">
                            Drop your export file here
                        </p>
                        <p className="text-sm text-muted-foreground mb-4">
                            or click to browse
                        </p>
                        <input
                            type="file"
                            accept=".json"
                            onChange={handleFileInput}
                            className="hidden"
                            id="import-file-input"
                        />
                        <Button
                            variant="outline"
                            onClick={() => document.getElementById('import-file-input')?.click()}
                        >
                            <FileJson className="h-4 w-4 mr-2" />
                            Select JSON File
                        </Button>
                    </div>

                    {error && (
                        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                            <p className="text-destructive text-sm">{error}</p>
                        </div>
                    )}
                </div>
            )}

            {/* Preview Step */}
            {step === 'preview' && exportData && (
                <div className="space-y-6">
                    {/* Export Info */}
                    <div className="bg-muted rounded-lg p-4 space-y-2">
                        <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Version:</span>
                            <span className="font-mono">{exportData.version}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Exported:</span>
                            <span>{new Date(exportData.exported_at).toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">By:</span>
                            <span>{exportData.exported_by}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">Collections:</span>
                            <span className="font-semibold">{exportData.collections.length}</span>
                        </div>
                    </div>

                    {/* Collection List */}
                    <div>
                        <Label className="text-sm font-medium mb-2 block">Collections to Import</Label>
                        <ScrollArea className="h-40 border rounded-lg">
                            <div className="p-3 space-y-2">
                                {exportData.collections.map((collection) => (
                                    <div
                                        key={collection.name}
                                        className="flex justify-between items-center text-sm py-1"
                                    >
                                        <span className="font-medium">{collection.name}</span>
                                        <span className="text-muted-foreground">
                                            {collection.schema.length} fields
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>
                    </div>

                    {/* Strategy Selection */}
                    <div>
                        <Label className="text-sm font-medium mb-3 block">Conflict Strategy</Label>
                        <Select value={strategy} onValueChange={(value: ImportStrategy) => setStrategy(value)}>
                            <SelectTrigger className="w-full">
                                <SelectValue placeholder="Select a strategy" />
                            </SelectTrigger>
                            <SelectContent>
                                {IMPORT_STRATEGY_OPTIONS.map((option) => (
                                    <SelectItem key={option.value} value={option.value}>
                                        <div className="flex flex-col">
                                            <span className="font-medium">{option.label}</span>
                                            <span className="text-xs text-muted-foreground">{option.description}</span>
                                        </div>
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {error && (
                        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                            <p className="text-destructive text-sm">{error}</p>
                        </div>
                    )}
                </div>
            )}

            {/* Importing Step */}
            {step === 'importing' && (
                <div className="py-12 text-center">
                    <div className="animate-spin h-12 w-12 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4" />
                    <p className="text-lg font-medium">Importing collections...</p>
                    <p className="text-sm text-muted-foreground mt-2">
                        This may take a moment
                    </p>
                </div>
            )}

            {/* Results Step */}
            {step === 'results' && importResult && (
                <div className="space-y-6">
                    {/* Summary */}
                    <div className="grid grid-cols-4 gap-4">
                        <div className="bg-green-50 dark:bg-green-950/20 rounded-lg p-4 text-center">
                            <p className="text-2xl font-bold text-green-600">{importResult.imported_count}</p>
                            <p className="text-sm text-muted-foreground">Imported</p>
                        </div>
                        <div className="bg-blue-50 dark:bg-blue-950/20 rounded-lg p-4 text-center">
                            <p className="text-2xl font-bold text-blue-600">{importResult.updated_count}</p>
                            <p className="text-sm text-muted-foreground">Updated</p>
                        </div>
                        <div className="bg-yellow-50 dark:bg-yellow-950/20 rounded-lg p-4 text-center">
                            <p className="text-2xl font-bold text-yellow-600">{importResult.skipped_count}</p>
                            <p className="text-sm text-muted-foreground">Skipped</p>
                        </div>
                        <div className="bg-red-50 dark:bg-red-950/20 rounded-lg p-4 text-center">
                            <p className="text-2xl font-bold text-red-600">{importResult.failed_count}</p>
                            <p className="text-sm text-muted-foreground">Failed</p>
                        </div>
                    </div>

                    {/* Per-collection results */}
                    <div>
                        <Label className="text-sm font-medium mb-2 block">Details</Label>
                        <ScrollArea className="h-48 border rounded-lg">
                            <div className="p-3 space-y-2">
                                {importResult.collections.map((result, index) => (
                                    <div
                                        key={index}
                                        className="flex items-center justify-between py-2 border-b last:border-0"
                                    >
                                        <div className="flex items-center gap-2">
                                            {getStatusIcon(result.status)}
                                            <span className="font-medium">{result.name}</span>
                                        </div>
                                        <span className="text-sm text-muted-foreground">{result.message}</span>
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>
                    </div>

                    {importResult.migrations_created.length > 0 && (
                        <div className="text-sm text-muted-foreground">
                            {importResult.migrations_created.length} migration(s) created
                        </div>
                    )}
                </div>
            )}
        </AppDialog>
    );
}
