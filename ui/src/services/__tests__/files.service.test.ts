import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'
import { uploadFile, getFileDownloadUrl, type FileMetadata } from '../files.service'

const mockFileMetadata: FileMetadata = {
  filename: 'photo.jpg',
  size: 204800,
  mime_type: 'image/jpeg',
  path: 'uploads/photo.jpg',
}

describe('Files Service', () => {
  describe('uploadFile()', () => {
    it('returns file metadata from SDK upload response', async () => {
      server.use(
        http.post('http://localhost/api/v1/files/upload', async () =>
          HttpResponse.json({
            success: true,
            file: mockFileMetadata,
            message: 'File uploaded successfully',
          }),
        ),
      )

      const file = new File(['content'], 'photo.jpg', { type: 'image/jpeg' })
      const result = await uploadFile(file)

      expect(result).toEqual(mockFileMetadata)
    })
  })

  describe('getFileDownloadUrl()', () => {
    it('returns a URL containing the file path', () => {
      const url = getFileDownloadUrl('uploads/photo.jpg')
      expect(url).toContain('uploads/photo.jpg')
    })

    it('returns a URL containing /files/ prefix', () => {
      const url = getFileDownloadUrl('uploads/photo.jpg')
      expect(url).toContain('/files/')
    })

    it('returns a URL containing /api/v1 base path', () => {
      const url = getFileDownloadUrl('uploads/photo.jpg')
      expect(url).toContain('/api/v1')
    })
  })
})
