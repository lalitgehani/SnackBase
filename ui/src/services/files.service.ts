/**
 * Files API service
 * Handles file upload and download operations
 */

import { apiClient } from '@/lib/api';

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

/**
 * Upload a file to storage
 */
export const uploadFile = async (file: File): Promise<FileMetadata> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<FileUploadResponse>('/files/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data.file;
};

/**
 * Get file download URL
 */
export const getFileDownloadUrl = (filePath: string): string => {
  // Use the API client's base URL
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
  // Ensure we have the full URL for file downloads
  const apiUrl = baseUrl.startsWith('http') ? baseUrl : `${window.location.origin}${baseUrl}`;
  return `${apiUrl}/files/${filePath}`;
};
