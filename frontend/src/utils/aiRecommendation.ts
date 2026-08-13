import type { AiRecommendModel, AiRecommendOut } from '../api'

export type MatchStatus = 'matched' | 'partial_match' | 'no_match'

export function recommendationSourceNote(source: string, warning?: string | null, provenance?: string): string {
  if (provenance === 'ai_used_with_evidence') return 'AI 已调用，并基于天枢本地证据补充风险提示'
  if (provenance === 'ai_used_no_evidence_refusal') return 'AI 已调用，但本地无可核验证据；仅返回拒答或澄清'
  if (provenance === 'ai_provider_failed') return 'AI provider 调用失败，已回退本地资料库结果'
  if (source === 'ai') return '来源：AI + 天枢本地资料库证据'
  if (warning?.trim()) return 'AI调用失败，已使用天枢本地资料库证据结果'
  return 'AI 未启用或配置不完整，仅使用本地资料库结果'
}

export function recommendationLabel(result: AiRecommendOut): string {
  if ((result.unparsed_conditions?.length ?? 0) > 0) return '未解析，待核验'
  if (result.models.some((model) => model.condition_results?.some((item) => item.status === 'unknown'))) return '存在未知条件，待核验'
  if (result.match_basis === 'catalog_match' || result.catalog_match) return '目录候选'
  return normalizeMatchStatus(result.match_status) === 'partial_match' ? '待核验候选' : '推荐型号'
}

export function normalizeMatchStatus(value: string | undefined): MatchStatus {
  return value === 'partial_match' || value === 'no_match' ? value : 'matched'
}

export function visibleRecommendationModels(result: AiRecommendOut): AiRecommendModel[] {
  if (normalizeMatchStatus(result.match_status) === 'no_match') return []
  if ((result.unparsed_conditions?.length ?? 0) > 0) return []

  const structuredIds = result.selected_model_ids
    ?? result.recommended_model_ids
    ?? result.selected_ids
    ?? result.recommended_ids

  // An explicitly empty structured selection means the answer selected nothing.
  // When old backends omit all ID fields, preserve the legacy models[] behavior.
  if (structuredIds !== undefined) {
    const ids = new Set(structuredIds.map(Number).filter(Number.isFinite))
    return result.models.filter((model) => ids.has(model.id) && model.condition_results?.every((item) => {
      const status = item.status ?? (item.satisfied ? 'satisfied' : 'unknown')
      return status === 'satisfied' && !item.evidence?.startsWith('排除冲突：')
    }) !== false)
  }
  return result.models
}
