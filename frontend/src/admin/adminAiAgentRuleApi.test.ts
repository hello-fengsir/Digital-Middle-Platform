import { afterEach, describe, expect, it, vi } from 'vitest'
import { getAiAgentRule, saveAiAgentRule } from './adminApi'

afterEach(() => vi.restoreAllMocks())

describe('AI agent rule API', () => {
  it('GET uses the fixed endpoint and Bearer token', async () => {
    const rule = { content: '# rule', sha256: 'a'.repeat(64), updated_at: null, source: 'runtime' }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(rule), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    await expect(getAiAgentRule('token-1')).resolves.toEqual(rule)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/admin/ai-agent-rule')
    expect(init).toMatchObject({ method: 'GET' })
    expect((init?.headers as Record<string, string>).Authorization).toBe('Bearer token-1')
  })

  it('PUT sends exactly content and no path or filename', async () => {
    const rule = { content: '# changed', sha256: 'b'.repeat(64), updated_at: '2026-08-12T10:00:00Z', source: 'runtime' }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(rule), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    await expect(saveAiAgentRule('token-2', '# changed')).resolves.toEqual(rule)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/admin/ai-agent-rule')
    expect(init).toMatchObject({ method: 'PUT', body: JSON.stringify({ content: '# changed' }) })
    expect(Object.keys(JSON.parse(String(init?.body)))).toEqual(['content'])
    expect((init?.headers as Record<string, string>).Authorization).toBe('Bearer token-2')
  })
})
