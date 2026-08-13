import { describe, expect, it } from 'vitest'
import { normalizeProductBadges } from './productBadges'

describe('normalizeProductBadges', () => {
  it('uses the closed lifecycle and featured allowlists', () => {
    expect(normalizeProductBadges({ lifecycle_status: 'npi', business_tags: ['featured'] })).toMatchObject([
      { code: 'npi', label: '新品', tone: 'npi' }, { code: 'featured', label: '主推', tone: 'featured' },
    ])
  })
  it('ignores backend labels, unknown values, null and malformed data silently', () => {
    expect(normalizeProductBadges({ lifecycle_status: 'mystery', business_tags: null, badges: [null, 'bad', { kind: 'lifecycle', code: 'eol', label: '伪造文案' }] })).toEqual([
      { kind: 'lifecycle', code: 'eol', label: '停售', tone: 'eol' },
    ])
    expect(normalizeProductBadges(undefined)).toEqual([])
  })
  it('deduplicates compatibility fields and structured badges', () => {
    expect(normalizeProductBadges({ lifecycle_status: 'rts', business_tags: ['featured'], badges: [{ kind: 'lifecycle', code: 'rts' }, { kind: 'business', code: 'featured' }] })).toHaveLength(2)
  })
})
