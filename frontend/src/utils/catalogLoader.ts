import type { ModelDetail, ModelSummary, Series } from '../api'

export interface CatalogRequestResult {
  models: ModelSummary[]
  selectedModelId: number | null
  detail: ModelDetail | null
}

export function reconcileSelectedType(models: ModelSummary[], selectedType: string): string {
  if (selectedType === '全部' || models.length === 0) return selectedType
  return models.some((model) => model.product_type === selectedType) ? selectedType : '全部'
}

export function catalogPageProductTitle(_brand: string, _productTypes: string[]): string {
  return '产品规格'
}

export interface CatalogRequestCoordinator {
  begin: () => number
  isCurrent: (requestId: number) => boolean
}

export interface CatalogJumpResult {
  target: ModelDetail
  models: ModelSummary[] | null
}

interface RunCatalogJumpOptions {
  id: number
  currentBrand: string
  coordinator: CatalogRequestCoordinator
  getModel: (id: number) => Promise<ModelDetail>
  getModels: (brand: string, keyword?: string) => Promise<ModelSummary[]>
  setLoading: (loading: boolean) => void
  apply: (result: CatalogJumpResult) => void
}

export function createCatalogRequestCoordinator(): CatalogRequestCoordinator {
  let latestRequestId = 0
  return {
    begin: () => ++latestRequestId,
    isCurrent: (requestId) => requestId === latestRequestId,
  }
}

interface RunCatalogRequestOptions {
  brand: string
  keyword: string
  coordinator: CatalogRequestCoordinator
  loadSeries?: boolean
  getSeries: (brand: string) => Promise<Series[]>
  getModels: (brand: string, keyword?: string) => Promise<ModelSummary[]>
  setLoading: (loading: boolean) => void
  apply: (result: CatalogRequestResult) => void
}

export async function runCatalogJump(options: RunCatalogJumpOptions) {
  const requestId = options.coordinator.begin()
  options.setLoading(true)
  try {
    const target = await options.getModel(options.id)
    if (!options.coordinator.isCurrent(requestId)) return false
    const models = target.brand_code === options.currentBrand ? null : await options.getModels(target.brand_code, '')
    if (!options.coordinator.isCurrent(requestId)) return false
    options.apply({ target, models })
    return true
  } finally {
    if (options.coordinator.isCurrent(requestId)) options.setLoading(false)
  }
}

export async function runCatalogRequest(options: RunCatalogRequestOptions) {
  const requestId = options.coordinator.begin()
  const keyword = options.keyword.trim()
  options.setLoading(true)

  try {
    if (options.loadSeries) await options.getSeries(options.brand)
    const models = await options.getModels(options.brand, keyword)
    if (!options.coordinator.isCurrent(requestId)) return false

    options.apply({
      models,
      selectedModelId: null,
      detail: null,
    })
    return true
  } finally {
    if (options.coordinator.isCurrent(requestId)) options.setLoading(false)
  }
}
