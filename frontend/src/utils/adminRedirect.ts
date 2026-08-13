export function validatedPdfViewerNext(
  search: string,
  origin: string,
): string | null {
  const raw = new URLSearchParams(search).get('next')
  if (!raw) return null
  try {
    const target = new URL(raw, origin)
    if (target.origin !== origin) return null
    if (!target.pathname.startsWith('/pdf-viewer/')) return null
    return `${target.pathname}${target.search}${target.hash}`
  } catch {
    return null
  }
}
