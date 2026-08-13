import { describe, expect, it, vi } from 'vitest'
import type { ModelDetail, ModelSummary } from '../api'
import { createCatalogRequestCoordinator, reconcileSelectedType, runCatalogJump, runCatalogRequest, type CatalogRequestResult } from './catalogLoader'

const summary = (id: number, brand: string, name: string): ModelSummary => ({
  id,
  brand_code: brand,
  brand_name: brand,
  product_type: '服务器',
  series: '测试系列',
  model_name: name,
  title: name,
})

const detail = (model: ModelSummary): ModelDetail => ({
  ...model,
  source_ref: '',
  specifications: [],
  compatible_gpus: [],
})

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}

function harness() {
  const results: CatalogRequestResult[] = []
  const loading: boolean[] = []
  const modelMap = new Map<number, ModelSummary>()
  return {
    results,
    loading,
    modelMap,
    options: {
      coordinator: createCatalogRequestCoordinator(),
      getSeries: vi.fn(async () => []),
      getModel: vi.fn(async (id: number) => detail(modelMap.get(id)!)),
      setLoading: (value: boolean) => { loading.push(value) },
      apply: (result: CatalogRequestResult) => { results.push(result) },
    },
  }
}

describe('brand keyword catalog loading', () => {
  it('新结果不含旧产品类型时回到全部，仍包含时保留，空结果不擅自改类型', () => {
    const servers = [summary(1, 'inspur', 'NF5280M7')]
    expect(reconcileSelectedType(servers, '存储')).toBe('全部')
    expect(reconcileSelectedType(servers, '服务器')).toBe('服务器')
    expect(reconcileSelectedType(servers, '全部')).toBe('全部')
    expect(reconcileSelectedType([], '存储')).toBe('存储')
  })

  it('竞态只应用最新响应，迟到旧类型结果不能反向改变当前类型', async () => {
    const h = harness()
    const oldResponse = deferred<ModelSummary[]>()
    const storage = { ...summary(31, 'inspur', 'AS13000'), product_type: '存储' }
    const server = summary(32, 'inspur', 'NF5280M7')
    h.modelMap.set(server.id, server)
    let selectedType = '存储'
    const appliedTypes: string[] = []
    const apply = (result: CatalogRequestResult) => {
      selectedType = reconcileSelectedType(result.models, selectedType)
      appliedTypes.push(selectedType)
      h.results.push(result)
    }
    const getModels = vi.fn((_brand: string, keyword = '') => keyword === 'old' ? oldResponse.promise : Promise.resolve([server]))

    const oldRequest = runCatalogRequest({ ...h.options, apply, brand: 'inspur', keyword: 'old', getModels })
    await runCatalogRequest({ ...h.options, apply, brand: 'inspur', keyword: 'NF5280M7', getModels })
    oldResponse.resolve([storage])
    await oldRequest

    expect(appliedTypes).toEqual(['全部'])
    expect(h.results[0].models).toEqual([server])
  })

  it('保留 400W 切到联想零结果，再切回浪潮恢复 8 条但不自动选型', async () => {
    const h = harness()
    const inspur = Array.from({ length: 8 }, (_, index) => summary(index + 1, 'inspur', `浪潮-${index + 1}`))
    inspur.forEach((model) => h.modelMap.set(model.id, model))
    const getModels = vi.fn(async (brand: string, keyword = '') => brand === 'inspur' && keyword === '400W' ? inspur : [])

    await runCatalogRequest({ ...h.options, brand: 'lenovo', keyword: ' 400W ', loadSeries: true, getModels })
    expect(getModels).toHaveBeenLastCalledWith('lenovo', '400W')
    expect(h.results.at(-1)).toEqual({ models: [], selectedModelId: null, detail: null })

    await runCatalogRequest({ ...h.options, brand: 'inspur', keyword: '400W', loadSeries: true, getModels })
    expect(getModels).toHaveBeenLastCalledWith('inspur', '400W')
    expect(h.results.at(-1)?.models).toHaveLength(8)
    expect(h.results.at(-1)?.selectedModelId).toBeNull()
    expect(h.results.at(-1)?.detail).toBeNull()
    expect(h.options.getModel).not.toHaveBeenCalled()
    expect(h.loading.at(-1)).toBe(false)
  })

  it('空关键词仍请求品牌全量且 finally 关闭 loading', async () => {
    const h = harness()
    const all = [summary(9, 'inspur', '全量型号')]
    h.modelMap.set(9, all[0])
    const getModels = vi.fn(async () => all)

    await runCatalogRequest({ ...h.options, brand: 'inspur', keyword: '   ', getModels })

    expect(getModels).toHaveBeenCalledWith('inspur', '')
    expect(h.results.at(-1)?.models).toEqual(all)
    expect(h.results.at(-1)).toEqual({ models: all, selectedModelId: null, detail: null })
    expect(h.options.getModel).not.toHaveBeenCalled()
    expect(h.loading).toEqual([true, false])
  })

  it('快速切品牌时旧响应不能覆盖最新品牌，旧请求也不能提前关闭 loading', async () => {
    const h = harness()
    const oldResponse = deferred<ModelSummary[]>()
    const latest = [summary(22, 'lenovo', '联想最新结果')]
    h.modelMap.set(22, latest[0])
    const getModels = vi.fn((brand: string) => brand === 'inspur' ? oldResponse.promise : Promise.resolve(latest))

    const oldRequest = runCatalogRequest({ ...h.options, brand: 'inspur', keyword: '400W', getModels })
    const latestRequest = runCatalogRequest({ ...h.options, brand: 'lenovo', keyword: '400W', getModels })
    await latestRequest

    oldResponse.resolve([summary(11, 'inspur', '迟到旧结果')])
    await oldRequest

    expect(h.results).toHaveLength(1)
    expect(h.results[0].models).toEqual(latest)
    expect(h.loading).toEqual([true, true, false])
  })

  it('请求失败也通过 finally 关闭 loading', async () => {
    const h = harness()
    const getModels = vi.fn(async () => { throw new Error('network failed') })

    await expect(runCatalogRequest({ ...h.options, brand: 'inspur', keyword: '400W', getModels })).rejects.toThrow('network failed')
    expect(h.loading).toEqual([true, false])
  })

  it('0 结果搜索后 AI 跨品牌跳转使旧请求失效并明确展示点击目标', async () => {
    const h = harness()
    const stale = deferred<ModelSummary[]>()
    const targetSummary = summary(88, 'inspur', 'NF-AI-TARGET')
    const targetDetail = detail(targetSummary)
    const getModels = vi.fn((brand: string, keyword = '') => {
      if (brand === 'accessory' && keyword === 'NO-RESULT') return stale.promise
      return Promise.resolve([targetSummary])
    })
    const staleRequest = runCatalogRequest({ ...h.options, brand: 'accessory', keyword: 'NO-RESULT', getModels })
    let final = { brand: 'accessory', keyword: 'NO-RESULT', selectedId: null as number | null, detail: null as ModelDetail | null, models: [] as ModelSummary[] }

    final.keyword = ''
    await runCatalogJump({
      id: 88,
      currentBrand: final.brand,
      coordinator: h.options.coordinator,
      getModel: vi.fn(async () => targetDetail),
      getModels,
      setLoading: h.options.setLoading,
      apply: ({ target, models }) => {
        final = { brand: target.brand_code, keyword: final.keyword, selectedId: target.id, detail: target, models: models || [] }
      },
    })
    stale.resolve([])
    await staleRequest

    expect(getModels).toHaveBeenCalledWith('inspur', '')
    expect(final).toMatchObject({ brand: 'inspur', keyword: '', selectedId: 88, detail: { model_name: 'NF-AI-TARGET' } })
    expect(final.models).toEqual([targetSummary])
    expect(h.results).toEqual([])
  })
})
