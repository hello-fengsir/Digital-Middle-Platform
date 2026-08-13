import { describe, expect, it, vi } from 'vitest'
import { deleteAiConfigApiKey, replaceCompatibleGpus } from './adminApi'

const gpu = { id: 7, model_name: 'RTX 6000', title: 'RTX 6000', brand_code: 'accessory', product_type: '显卡', series: 'GPU', display_name: 'RTX 6000 48GB' }

describe('compatible GPU API', () => {
  it('uses the dedicated PUT endpoint and exact payload', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify([gpu]), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    }))
    await expect(replaceCompatibleGpus('token-1', 42, [7, 9])).resolves.toEqual([gpu])
    expect(fetchMock).toHaveBeenCalledOnce()
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/admin/models/42/compatible-gpus')
    expect(init).toMatchObject({ method: 'PUT', body: JSON.stringify({ compatible_gpu_ids: [7, 9] }) })
    expect((init?.headers as Record<string, string>).Authorization).toBe('Bearer token-1')
    fetchMock.mockRestore()
  })

  it('surfaces failure so the UI can retain the current selection', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('save failed', { status: 500 }))
    const selectedIds = [7, 9]
    await expect(replaceCompatibleGpus('token-1', 42, selectedIds)).rejects.toThrow('save failed')
    expect(selectedIds).toEqual([7, 9])
    fetchMock.mockRestore()
  })
})

describe('AI config API Key deletion', () => {
  it('uses the exact DELETE endpoint with no request body', async () => {
    const result = { base_url: 'https://example.com', model: 'model-a', temperature: 0.2, max_tokens: 1200, enabled: false, has_api_key: false }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(result), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    }))
    await expect(deleteAiConfigApiKey('token-delete')).resolves.toEqual(result)
    expect(fetchMock).toHaveBeenCalledOnce()
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/admin/ai-config/api-key')
    expect(init).toMatchObject({ method: 'DELETE' })
    expect(init).not.toHaveProperty('body')
    expect((init?.headers as Record<string, string>).Authorization).toBe('Bearer token-delete')
  })
})
