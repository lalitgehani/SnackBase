/**
 * Files API service
 */
import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

export interface FileMetadata {
  filename: string;
  size: number;
  mime_type: string;
  path: string;
}

export interface FileUploadResponse {
  success: boolean;
  file: FileMetadata;
  message: string;
}

export function createFilesService(client: SnackBaseClient) {
  return {
    uploadFile: async (file: File): Promise<FileMetadata> => client.files.upload(file),
    getFileDownloadUrl: (filePath: string): string => client.files.getDownloadUrl(filePath),
  };
}

export const useFilesService = createServiceHook(createFilesService);

const filesService = bindService(createFilesService);
export const uploadFile = filesService.uploadFile;
export const getFileDownloadUrl = filesService.getFileDownloadUrl;
