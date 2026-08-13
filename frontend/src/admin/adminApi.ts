import { getBrands, getModel, getModels, getProductTypes, getSeries, type Brand, type BusinessTag, type CompatibleGpu, type LifecycleStatus, type ModelDetail, type ModelSummary, type ProductType, type Series, type SpecValue } from '../api'

export { getBrands, getModel, getModels, getProductTypes, getSeries, type Brand, type CompatibleGpu, type ModelDetail, type ModelSummary, type ProductType, type Series, type SpecValue }

export interface AdminSession {
  token: string
  username: string
  expires_at: string
}

export interface SpecDefinition {
  id: number
  group_code?: string
  group_name: string
  field_key: string
  label: string
  group_sort_order?: number
  sort_order: number
}

export interface ImportPreviewOut { total_rows: number; valid_rows: number; invalid_rows: number; errors: string[]; rows: any[]; sheet_rows: any[] }

export interface SpecInput {
  field_key: string
  label: string
  group: string
  sort_order?: number | null
  value: string
  raw_label?: string | null
  source_ref?: string
}

export interface ModelWritePayload {
  brand_code: string
  brand_name?: string | null
  product_type: string
  series: string
  model_name: string
  title?: string
  platform_vendor?: string | null
  generation?: string | null
  source_ref?: string
  raw_source_id?: string | null
  specifications?: SpecInput[]
  compatible_gpu_ids?: number[]
  lifecycle_status: LifecycleStatus
  business_tags?: BusinessTag[]
}

export type ModelPatchPayload = Partial<Omit<ModelWritePayload, 'specifications'>> & {
  status?: string | null
  specifications?: SpecInput[]
}

export interface AiConfig {
  base_url: string
  model: string
  temperature: number
  max_tokens: number
  enabled: boolean
  has_api_key: boolean
}

export interface AiConfigPayload {
  base_url: string
  api_key?: string | null
  model: string
  temperature: number
  max_tokens: number
  enabled: boolean
}

async function publicRequest<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<T>
}

export const getSpecDefinitions = () => publicRequest<SpecDefinition[]>('/api/v1/spec-definitions')

export const getAdminModels = (token: string, brand: string, status = 'active', keyword = '') => {
  const params = new URLSearchParams()
  if (brand) params.set('brand', brand)
  if (status) params.set('status', status)
  if (keyword.trim()) params.set('keyword', keyword.trim())
  return adminRequest<ModelSummary[]>(`/api/v1/admin/models?${params.toString()}`, token, { method: 'GET' })
}

export const getAdminModel = (token: string, modelId: number) =>
  adminRequest<ModelDetail>(`/api/v1/admin/models/${modelId}`, token, { method: 'GET' })

async function authRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
  })
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<T>
}

export const loginAdmin = (username: string, password: string) =>
  authRequest<AdminSession>('/api/v1/admin/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) })

export const getAdminMe = (token: string) =>
  authRequest<{ username: string; expires_at: string }>('/api/v1/admin/auth/me', { headers: { Authorization: `Bearer ${token}` } })

export const logoutAdmin = () =>
  authRequest<{ ok: boolean }>('/api/v1/admin/auth/logout', { method: 'POST' })

async function adminRequest<T>(path: string, token: string, init: RequestInit, apiKey = ''): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(apiKey ? { 'X-API-Key': apiKey } : {}),
      'Authorization': `Bearer ${token}`,
      ...(init.headers || {}),
    },
  })
  if (!response.ok) {
    const body = await response.text()
    throw new Error(body || `${response.status} ${response.statusText}`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const createModel = (token: string, payload: ModelWritePayload, apiKey = '') =>
  adminRequest<ModelDetail>('/api/v1/admin/models', token, { method: 'POST', body: JSON.stringify(payload) }, apiKey)

export const patchModel = (token: string, modelId: number, payload: ModelPatchPayload, apiKey = '') =>
  adminRequest<ModelDetail>(`/api/v1/admin/models/${modelId}`, token, { method: 'PATCH', body: JSON.stringify(payload) }, apiKey)

export const deleteModel = (token: string, modelId: number, apiKey = '') =>
  adminRequest<void>(`/api/v1/admin/models/${modelId}`, token, { method: 'DELETE' }, apiKey)

export const deleteSeries = (token: string, seriesId: number) =>
  adminRequest<void>(`/api/v1/admin/series/${seriesId}`, token, { method: 'DELETE' })

export const replaceSpecifications = (token: string, modelId: number, payload: SpecInput[], apiKey = '') =>
  adminRequest<SpecValue[]>(`/api/v1/admin/models/${modelId}/specifications`, token, { method: 'PUT', body: JSON.stringify(payload) }, apiKey)

export type CompatibleGpuSaveResult = CompatibleGpu[] | { compatible_gpus: CompatibleGpu[] }
export const replaceCompatibleGpus = (token: string, modelId: number, compatibleGpuIds: number[], apiKey = '') =>
  adminRequest<CompatibleGpuSaveResult>(`/api/v1/admin/models/${modelId}/compatible-gpus`, token, {
    method: 'PUT', body: JSON.stringify({ compatible_gpu_ids: compatibleGpuIds }),
  }, apiKey)

export const getGpuOptions = (token: string) =>
  adminRequest<CompatibleGpu[]>('/api/v1/admin/gpu-options', token, { method: 'GET' })
export const getAiConfig = (token: string) =>
  adminRequest<AiConfig>('/api/v1/admin/ai-config', token, { method: 'GET' })
export const saveAiConfig = (token: string, payload: AiConfigPayload) =>
  adminRequest<AiConfig>('/api/v1/admin/ai-config', token, { method: 'PUT', body: JSON.stringify(payload) })
export const deleteAiConfigApiKey = (token: string) =>
  adminRequest<AiConfig>('/api/v1/admin/ai-config/api-key', token, { method: 'DELETE' })
export const testAiConfig = (token: string, payload: Partial<AiConfigPayload>) =>
  adminRequest<{ ok: boolean; message: string }>('/api/v1/admin/ai-config/test', token, { method: 'POST', body: JSON.stringify(payload) })

export interface AiAgentRule {
  content: string
  sha256: string
  updated_at: string | null
  source: 'runtime' | 'default'
}

export const getAiAgentRule = (token: string) =>
  adminRequest<AiAgentRule>('/api/v1/admin/ai-agent-rule', token, { method: 'GET' })
export const saveAiAgentRule = (token: string, content: string) =>
  adminRequest<AiAgentRule>('/api/v1/admin/ai-agent-rule', token, { method: 'PUT', body: JSON.stringify({ content }) })

export interface SpecRecognitionPreviewItem {
  raw_label: string
  value: string
  matched_field_key?: string | null
  matched_label?: string | null
  group_code?: string | null
  group_name?: string | null
  confidence: number
  note: string
}

export interface SpecRecognitionPreviewOut { items: SpecRecognitionPreviewItem[] }

export const previewSpecRecognition = (token: string, payload: { raw_text: string; brand_code?: string; product_type?: string; series?: string; model_name?: string }, apiKey = '') =>
  adminRequest<SpecRecognitionPreviewOut>('/api/v1/admin/spec-recognition/preview', token, { method: 'POST', body: JSON.stringify(payload) }, apiKey)

export interface SpecDefinitionUpdatePayload {
  group_code?: string
  group_name?: string
  label?: string
  sort_order?: number | null
}

export const updateSpecDefinition = (token: string, fieldKey: string, payload: SpecDefinitionUpdatePayload, apiKey = '') =>
  adminRequest<SpecDefinition>(`/api/v1/admin/spec-definitions/${encodeURIComponent(fieldKey)}`, token, { method: 'PATCH', body: JSON.stringify(payload) }, apiKey)

export const downloadImportTemplate = (token: string) => fetch('/api/v1/admin/import/template', { headers: { Authorization: 'Bearer ' + token } })
export const previewImportWorkbook = (token: string, file: File) => { const form = new FormData(); form.append('file', file); return fetch('/api/v1/admin/import/preview', { method: 'POST', headers: { Authorization: 'Bearer ' + token }, body: form }) }
export const runImportWorkbook = (token: string, file: File) => { const form = new FormData(); form.append('file', file); return fetch('/api/v1/admin/import/run', { method: 'POST', headers: { Authorization: 'Bearer ' + token }, body: form }) }

export const previewMarkdownImport = (token: string, rawText: string) =>
  adminRequest<ImportPreviewOut>('/api/v1/admin/import/markdown/preview', token, { method: 'POST', body: JSON.stringify({ raw_text: rawText }) })
export const runMarkdownImport = (token: string, rawText: string) =>
  adminRequest<{ created: number; updated: number; errors: string[]; sheet_rows: number }>('/api/v1/admin/import/markdown/run', token, { method: 'POST', body: JSON.stringify({ raw_text: rawText }) })
