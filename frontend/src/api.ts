export interface Brand {
  id: number
  code: string
  name: string
  source_name: string
  model_count: number
}

export interface Series {
  id: number
  brand_code: string
  product_type: string
  name: string
  model_count: number
}

export interface ProductType {
  id: number
  code: string
  name: string
}

export type LifecycleStatus = 'npi' | 'rts' | 'rtq' | 'eos' | 'eol'
export type BusinessTag = 'featured'
export interface ModelBadge { kind: 'lifecycle' | 'business'; code: string; label?: string }

export interface ModelSummary {
  id: number
  brand_code: string
  brand_name: string
  product_type: string
  series: string
  model_name: string
  title: string
  platform_vendor?: string | null
  generation?: string | null
  status?: string
  deleted_at?: string | null
  gpu_slot_width?: string | null
  gpu_cooling_type?: string | null
  lifecycle_status?: LifecycleStatus | string | null
  business_tags?: Array<BusinessTag | string> | null
  badges?: ModelBadge[] | null
}

export interface CompatibleGpu {
  id: number
  model_name: string
  title: string
  brand_code: string
  product_type: string
  series: string
  memory?: string | null
  display_name: string
}

export interface SpecValue {
  group_code: string
  group_name: string
  field_key: string
  label: string
  value: string
  raw_label: string
  source_ref: string
  confidence: string
}

export interface ModelDetail extends ModelSummary {
  source_ref: string
  raw_source_id?: string | null
  specifications: SpecValue[]
  compatible_gpus: CompatibleGpu[]
}

export interface AiConditionResult {
  condition_id: string
  kind: string
  label: string
  satisfied: boolean
  status?: 'satisfied' | 'unsatisfied' | 'unknown'
  verification_status?: 'confirmed' | 'conflict' | 'unknown'
  generation?: number | null
  lanes?: number | null
  actual?: unknown
  evidence?: string | null
}

export interface AiBrandCoverage {
  brand_code: string
  brand_name: string
  status: 'covered' | 'uncovered'
  candidate_count: number
  message: string
}

export interface AiCoverage {
  requested_brands: string[]
  covered_brands: string[]
  uncovered_brands: string[]
  brand_results: AiBrandCoverage[]
}

export interface AiRecommendModel {
  id: number
  model_name: string
  brand_code: string
  brand_name: string
  product_type: string
  series: string
  reason: string
  evidence: string[]
  fully_matched?: boolean
  condition_results?: AiConditionResult[]
  lifecycle_status?: LifecycleStatus | string | null
  business_tags?: Array<BusinessTag | string> | null
  badges?: ModelBadge[] | null
}

export interface AiRecommendOut {
  answer: string
  models: AiRecommendModel[]
  source: string
  warning?: string | null
  provenance?: 'ai_used_with_evidence' | 'ai_used_no_evidence_refusal' | 'ai_provider_failed' | 'ai_not_available' | string
  match_status?: 'matched' | 'partial_match' | 'no_match' | string
  hard_conditions?: Array<{ id: string; kind: string; operator: string; value: unknown; unit?: string | null; generation?: number | null; lanes?: number | null; label: string }>
  coverage?: AiCoverage
  selected_model_ids?: number[]
  match_basis?: 'hard_conditions' | 'catalog_match' | 'none' | string
  catalog_match?: boolean
  unparsed_conditions?: string[]
  recommended_model_ids?: number[]
  selected_ids?: number[]
  recommended_ids?: number[]
}

export function publicApiError(status: number, payload?: unknown) {
  if (status === 504) return 'AI 分析等待超时，请稍后重试或精简需求'
  if (status === 502 || status === 503) return '服务暂时不可用，请稍后重试'
  if (payload && typeof payload === 'object' && 'detail' in payload && typeof payload.detail === 'string') return payload.detail
  return '请求失败，请稍后重试'
}

async function safeErrorPayload(response: Response) {
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.toLowerCase().includes('application/json')) return undefined
  try {
    return await response.json() as unknown
  } catch {
    return undefined
  }
}

async function api<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<T>
}

export const getBrands = () => api<Brand[]>('/api/v1/brands')
export const getProductTypes = () => api<ProductType[]>('/api/v1/product-types')
export const getSeries = (brand: string) => api<Series[]>(`/api/v1/series?brand=${encodeURIComponent(brand)}`)
export const getModels = (brand: string, keyword = '') => {
  const params = new URLSearchParams({ brand })
  if (keyword.trim()) params.set('keyword', keyword.trim())
  return api<ModelSummary[]>(`/api/v1/models?${params.toString()}`)
}
export const searchModels = (brand: string, q: string) => {
  const params = new URLSearchParams({ brand, q: q.trim() })
  return api<ModelSummary[]>(`/api/v1/search?${params.toString()}`)
}
export const getModel = (id: number) => api<ModelDetail>(`/api/v1/models/${id}`)
export async function recommendModels(message: string) {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), 90000)
  try {
    const response = await fetch('/api/v1/ai/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
      signal: controller.signal,
    })
    if (!response.ok) throw new Error(publicApiError(response.status, await safeErrorPayload(response)))
    return response.json() as Promise<AiRecommendOut>
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw new Error('AI 请求超过 90 秒未返回，请检查模型配置或稍后重试')
    throw error
  } finally {
    window.clearTimeout(timer)
  }
}
