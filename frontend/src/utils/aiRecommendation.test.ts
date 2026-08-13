import { describe, expect, it } from 'vitest'
import type { AiRecommendModel, AiRecommendOut } from '../api'
import { normalizeMatchStatus, recommendationLabel, recommendationSourceNote, visibleRecommendationModels } from './aiRecommendation'

const models: AiRecommendModel[] = [
  { id: 1, model_name: 'A', brand_code: 'a', brand_name: 'A', product_type: '服务器', series: 'S', reason: '', evidence: [] },
  { id: 2, model_name: 'B', brand_code: 'b', brand_name: 'B', product_type: '服务器', series: 'S', reason: '', evidence: [] },
]

function result(overrides: Partial<AiRecommendOut> = {}): AiRecommendOut {
  return { answer: 'answer', source: 'local', models, ...overrides }
}

describe('AI recommendation button contract', () => {
  it('hides all buttons for no_match even if a legacy backend sends models', () => {
    expect(visibleRecommendationModels(result({ match_status: 'no_match' }))).toEqual([])
  })

  it('only renders selected IDs when the backend provides structured selection', () => {
    expect(visibleRecommendationModels(result({ match_status: 'matched', selected_model_ids: [2] }))).toEqual([models[1]])
    expect(visibleRecommendationModels(result({ match_status: 'matched', recommended_ids: [] }))).toEqual([])
  })

  it('never renders buttons for unparsed exclusions or explicit exclusion conflicts', () => {
    expect(visibleRecommendationModels(result({ match_status: 'partial_match', unparsed_conditions: ['不要神秘拓扑'] }))).toEqual([])
    const conflicting = { ...models[0], condition_results: [{ condition_id: 'x', kind: 'gpu_model', label: '排除L40S', satisfied: false, evidence: '排除冲突：兼容L40S' }] }
    expect(visibleRecommendationModels(result({ match_status: 'partial_match', models: [conflicting], selected_model_ids: [1] }))).toEqual([])
  })

  it('never renders buttons for unknown conditions but accepts confirmed absence', () => {
    const unknown = { ...models[0], condition_results: [{ condition_id: 'x', kind: 'gpu_count', label: '排除3双宽', satisfied: false, status: 'unknown' as const, verification_status: 'unknown' as const }] }
    expect(visibleRecommendationModels(result({ match_status: 'partial_match', models: [unknown], selected_model_ids: [1] }))).toEqual([])
    expect(recommendationLabel(result({ match_status: 'partial_match', models: [unknown], selected_model_ids: [1] }))).toBe('存在未知条件，待核验')

    const confirmedAbsence = { ...models[0], condition_results: [{ condition_id: 'x', kind: 'gpu_count', label: '排除3双宽', satisfied: true, status: 'satisfied' as const, verification_status: 'confirmed' as const, actual: 'confirmed_absence' }] }
    expect(visibleRecommendationModels(result({ match_status: 'matched', models: [confirmedAbsence], selected_model_ids: [1] }))).toEqual([confirmedAbsence])
  })

  it('keeps old models[] responses backward compatible', () => {
    expect(visibleRecommendationModels(result({ match_status: 'partial_match' }))).toEqual(models)
    expect(visibleRecommendationModels(result())).toEqual(models)
  })

  it('normalizes partial/no match while defaulting old or unknown values to matched', () => {
    expect(normalizeMatchStatus('partial_match')).toBe('partial_match')
    expect(normalizeMatchStatus('no_match')).toBe('no_match')
    expect(normalizeMatchStatus(undefined)).toBe('matched')
    expect(normalizeMatchStatus('legacy')).toBe('matched')
  })

  it('labels no-hard-condition retrieval as catalog candidates', () => {
    expect(recommendationLabel(result({ match_status: 'matched', match_basis: 'catalog_match', catalog_match: true }))).toBe('目录候选')
    expect(recommendationLabel(result({ match_status: 'partial_match' }))).toBe('待核验候选')
  })
})

describe('AI recommendation source copy', () => {
  it('labels an AI call grounded by local evidence', () => {
    expect(recommendationSourceNote('ai', null, 'ai_used_with_evidence')).toBe('AI 已调用，并基于天枢本地证据补充风险提示')
  })

  it('labels an AI call that had no local evidence', () => {
    expect(recommendationSourceNote('ai', null, 'ai_used_no_evidence_refusal')).toBe('AI 已调用，但本地无可核验证据；仅返回拒答或澄清')
  })

  it('labels provider failure independently of warning text', () => {
    expect(recommendationSourceNote('local', '上游请求超时', 'ai_provider_failed')).toBe('AI provider 调用失败，已回退本地资料库结果')
    expect(recommendationSourceNote('local', null, 'ai_provider_failed')).toBe('AI provider 调用失败，已回退本地资料库结果')
  })

  it('keeps a backward-compatible fallback for legacy responses', () => {
    expect(recommendationSourceNote('ai', null)).toBe('来源：AI + 天枢本地资料库证据')
    expect(recommendationSourceNote('local', '上游请求超时')).toBe('AI调用失败，已使用天枢本地资料库证据结果')
    expect(recommendationSourceNote('local', null)).toBe('AI 未启用或配置不完整，仅使用本地资料库结果')
  })
})
