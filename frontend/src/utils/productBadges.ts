import type { BusinessTag, LifecycleStatus, ModelBadge } from '../api'

export interface BadgeView { kind: 'lifecycle' | 'business'; code: LifecycleStatus | BusinessTag; label: string; tone: string }

const lifecycle = {
  npi: { label: '新品', tone: 'npi' }, rts: { label: '在售', tone: 'rts' },
  rtq: { label: '可报价', tone: 'rtq' }, eos: { label: '停止接单', tone: 'eos' },
  eol: { label: '停售', tone: 'eol' },
} as const
const business = { featured: { label: '主推', tone: 'featured' } } as const

type BadgeSource = { lifecycle_status?: unknown; business_tags?: unknown; badges?: unknown }

export function normalizeProductBadges(source: BadgeSource | null | undefined): BadgeView[] {
  if (!source || typeof source !== 'object') return []
  const values: Array<{ kind: 'lifecycle' | 'business'; code: unknown }> = [{ kind: 'lifecycle', code: source.lifecycle_status }]
  if (Array.isArray(source.business_tags)) source.business_tags.forEach((code) => values.push({ kind: 'business', code }))
  if (Array.isArray(source.badges)) source.badges.forEach((raw) => {
    if (!raw || typeof raw !== 'object') return
    const badge = raw as Partial<ModelBadge>
    if (badge.kind === 'lifecycle' || badge.kind === 'business') values.push({ kind: badge.kind, code: badge.code })
  })
  const seen = new Set<string>()
  return values.flatMap(({ kind, code }) => {
    if (typeof code !== 'string') return []
    const definition = kind === 'lifecycle' ? lifecycle[code as keyof typeof lifecycle] : business[code as keyof typeof business]
    const key = `${kind}:${code}`
    if (!definition || seen.has(key)) return []
    seen.add(key)
    return [{ kind, code: code as LifecycleStatus | BusinessTag, label: definition.label, tone: definition.tone }]
  })
}

export const LIFECYCLE_OPTIONS = Object.entries(lifecycle).map(([value, item]) => ({ value: value as LifecycleStatus, label: item.label }))
