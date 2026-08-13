import { describe, expect, it } from 'vitest'
import { publicApiError } from '../src/api'

describe('publicApiError', () => {
  it('hides nginx html for 502/504 responses', () => {
    const html = '<html><title>504 Gateway Time-out</title><hr><center>nginx</center></html>'
    expect(publicApiError(504, html)).toBe('AI 分析等待超时，请稍后重试或精简需求')
    expect(publicApiError(502, html)).toBe('服务暂时不可用，请稍后重试')
  })

  it('uses safe json details for other statuses', () => {
    expect(publicApiError(422, { detail: '需求内容过长' })).toBe('需求内容过长')
  })
})
