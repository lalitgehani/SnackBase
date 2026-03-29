import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { server } from '@/test/mocks/server'
import { http, HttpResponse } from 'msw'
import { uploadFile, getFileDownloadUrl } from '../files.service'
import * as apiModule from '@/lib/api'
import type { FileMetadata, FileUploadResponse } from '../files.service'

const mockFileMetadata: FileMetadata = {
  filename: 'photo.jpg',
  size: 204800,
  mime_type: 'image/jpeg',
  path: 'uploads/photo.jpg',
}

const mockUploadResponse: FileUploadResponse = {
  success: true,
  file: mockFileMetadata,
  message: 'File uploaded successfully',
}

// ─────────────────────────────────────────────────────────────────────────────
// uploadFile()
//
// uploadFile() sends FormData (multipart/form-data). We mock apiClient.post
// directly to avoid jsdom limitations with binary FormData inspection.
// ─────────────────────────────────────────────────────────────────────────────

describe('Files Service', () => {
  describe('uploadFile()', () => {
    let apiPostSpy: ReturnType<typeof vi.spyOn>

    beforeEach(() => {
      apiPostSpy = vi.spyOn(apiModule.apiClient, 'post').mockResolvedValue({
        data: mockUploadResponse,
      })
    })

    afterEach(() => {
      vi.restoreAllMocks()
    })

    it('calls POST /files/upload', async () => {
      const file = new File(['content'], 'photo.jpg', { type: 'image/jpeg' })
      await uploadFile(file)

      expect(apiPostSpy).toHaveBeenCalledWith(
        '/files/upload',
        expect.any(FormData),
        expect.any(Object)
      )
    })

    it('sends request with multipart/form-data content type', async () => {
      const file = new File(['content'], 'photo.jpg', { type: 'image/jpeg' })
      await uploadFile(file)

      expect(apiPostSpy).toHaveBeenCalledWith(
        '/files/upload',
        expect.any(FormData),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'multipart/form-data',
          }),
        })
      )
    })

    it('appends file to FormData with key "file"', async () => {
      const file = new File(['content'], 'photo.jpg', { type: 'image/jpeg' })
      await uploadFile(file)

      const [, formData] = apiPostSpy.mock.calls[0]
      expect(formData instanceof FormData).toBe(true)
      expect((formData as FormData).get('file')).toBe(file)
    })

    it('returns file metadata from response', async () => {
      const file = new File(['content'], 'photo.jpg', { type: 'image/jpeg' })
      const result = await uploadFile(file)

      expect(result).toEqual(mockFileMetadata)
    })

    it('returns correct filename and mime_type', async () => {
      const file = new File(['content'], 'photo.jpg', { type: 'image/jpeg' })
      const result = await uploadFile(file)

      expect(result.filename).toBe('photo.jpg')
      expect(result.mime_type).toBe('image/jpeg')
    })

    it('propagates API errors on upload failure', async () => {
      apiPostSpy.mockRejectedValue(new Error('Upload failed'))

      const file = new File(['content'], 'photo.jpg', { type: 'image/jpeg' })
      await expect(uploadFile(file)).rejects.toThrow('Upload failed')
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // getFileDownloadUrl()
  // ─────────────────────────────────────────────────────────────────────────────

  describe('getFileDownloadUrl()', () => {
    it('returns a URL containing the file path', () => {
      const url = getFileDownloadUrl('uploads/photo.jpg')
      expect(url).toContain('uploads/photo.jpg')
    })

    it('returns a URL containing /files/ prefix', () => {
      const url = getFileDownloadUrl('uploads/photo.jpg')
      expect(url).toContain('/files/')
    })

    it('returns a URL containing /api/v1 base path when no env var is set', () => {
      const url = getFileDownloadUrl('uploads/photo.jpg')
      expect(url).toContain('/api/v1')
    })

    it('constructs correct download URL from a nested path', () => {
      const url = getFileDownloadUrl('2024/01/document.pdf')
      expect(url).toContain('/files/2024/01/document.pdf')
    })
  })
})
