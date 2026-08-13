import { describe, expect, it } from 'vitest'
import { validatedPdfViewerNext } from './adminRedirect'

const origin = 'https://example.com'

describe('validatedPdfViewerNext', () => {
  it('accepts only same-origin pdf-viewer paths and preserves query/hash', () => {
    expect(validatedPdfViewerNext('?next=%2Fpdf-viewer%2Fweb%2Fviewer.html%3Ffile%3Da.pdf%23page%3D2', origin))
      .toBe('/pdf-viewer/web/viewer.html?file=a.pdf#page=2')
    expect(validatedPdfViewerNext('?next=https%3A%2F%2Fexample.com%2Fpdf-viewer%2F', origin))
      .toBe('/pdf-viewer/')
  })

  it.each([
    '?next=https%3A%2F%2Fevil.example%2Fpdf-viewer%2F',
    '?next=%2F%2Fevil.example%2Fpdf-viewer%2F',
    '?next=%2Fadmin%2F',
    '?next=%2Fpdf-viewer-evil%2F',
    '?next=javascript%3Aalert(1)',
    '',
  ])('rejects unsafe next: %s', (search) => {
    expect(validatedPdfViewerNext(search, origin)).toBeNull()
  })
})
