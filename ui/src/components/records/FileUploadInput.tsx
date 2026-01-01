/**
 * File upload input component
 * Handles file selection, drag-and-drop, and upload to API
 */

import { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Upload, X, File, Loader2 } from 'lucide-react';
import { uploadFile } from '@/services/files.service';
import type { FileMetadata } from '@/services/files.service';
import { handleApiError } from '@/lib/api';

interface FileUploadInputProps {
    value: FileMetadata | null;
    onChange: (value: FileMetadata | null) => void;
    disabled?: boolean;
    fieldName: string;
}

export default function FileUploadInput({
    value,
    onChange,
    disabled = false,
    fieldName,
}: FileUploadInputProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileSelect = async (file: File) => {
        setError(null);
        setIsUploading(true);

        try {
            const metadata = await uploadFile(file);
            onChange(metadata);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setIsUploading(false);
        }
    };

    const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            handleFileSelect(file);
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        if (!disabled && !isUploading) {
            setIsDragging(true);
        }
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        if (disabled || isUploading) return;

        const file = e.dataTransfer.files?.[0];
        if (file) {
            handleFileSelect(file);
        }
    };

    const handleRemove = () => {
        onChange(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const handleBrowseClick = () => {
        fileInputRef.current?.click();
    };

    // Parse value if it's a JSON string
    const fileMetadata = value
        ? typeof value === 'string'
            ? JSON.parse(value)
            : value
        : null;

    return (
        <div className="space-y-2">
            <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileInputChange}
                disabled={disabled || isUploading}
                className="hidden"
                aria-label={`Upload file for ${fieldName}`}
            />

            {fileMetadata ? (
                // Display uploaded file
                <div className="border rounded-lg p-3 bg-muted/50">
                    <div className="flex items-start justify-between gap-2">
                        <div className="flex items-start gap-3 flex-1 min-w-0">
                            <File className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                            <div className="text-sm space-y-1 flex-1 min-w-0">
                                <div className="font-medium truncate">{fileMetadata.filename}</div>
                                <div className="text-muted-foreground text-xs space-y-0.5">
                                    <div>Size: {(fileMetadata.size / 1024).toFixed(2)} KB</div>
                                    <div>Type: {fileMetadata.mime_type}</div>
                                </div>
                            </div>
                        </div>
                        {!disabled && (
                            <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={handleRemove}
                                className="shrink-0"
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
                </div>
            ) : (
                // Upload area
                <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className={`
						border-2 border-dashed rounded-lg p-6 text-center transition-colors
						${isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}
						${disabled || isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-primary/50'}
					`}
                    onClick={!disabled && !isUploading ? handleBrowseClick : undefined}
                >
                    {isUploading ? (
                        <div className="flex flex-col items-center gap-2">
                            <Loader2 className="h-8 w-8 text-primary animate-spin" />
                            <p className="text-sm text-muted-foreground">Uploading...</p>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center gap-2">
                            <Upload className="h-8 w-8 text-muted-foreground" />
                            <div className="space-y-1">
                                <p className="text-sm font-medium">
                                    Drop file here or click to browse
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    Max 10MB • Supported: Images, PDF, Text, JSON
                                </p>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {error && (
                <p className="text-sm text-destructive">{error}</p>
            )}
        </div>
    );
}
