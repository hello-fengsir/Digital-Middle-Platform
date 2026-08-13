import { describe, expect, it, vi } from 'vitest'
import type { ModelSummary } from '../api'
import { catalogPageProductTitle, createCatalogRequestCoordinator, runCatalogRequest } from './catalogLoader'

const model: ModelSummary = {
  id: 7,
  brand_code: 'generic',
  brand_name: '示例品牌',
  product_type: '服务器',
  series: '测试系列',
  model_name: 'TS-7',
  title: '测试型号',
}

describe('首页新手 UX 合同', () => {
  it('所有品牌统一使用简洁的“产品规格”标题', () => {
    expect(catalogPageProductTitle('generic', ['服务器', '存储', '工作站', '停止接单'])).toBe('产品规格')
    expect(catalogPageProductTitle('inspur', ['服务器', '存储'])).toBe('产品规格')
    expect(catalogPageProductTitle('lenovo', ['服务器', '工作站'])).toBe('产品规格')
    expect(catalogPageProductTitle('dell', ['服务器', '工作站'])).toBe('产品规格')
    expect(catalogPageProductTitle('accessory', ['显卡', '硬盘'])).toBe('产品规格')
  })

  it.each(['首次加载', '刷新', '切换品牌', '输入搜索词', '清空搜索'])(
    '%s只更新目录，selectedModelId/detail 保持 null',
    async () => {
      const apply = vi.fn()
      await runCatalogRequest({
        brand: 'generic',
        keyword: 'TS',
        coordinator: createCatalogRequestCoordinator(),
        getSeries: vi.fn(async () => []),
        getModels: vi.fn(async () => [model]),
        setLoading: vi.fn(),
        apply,
      })
      expect(apply).toHaveBeenCalledWith({ models: [model], selectedModelId: null, detail: null })
    },
  )

  it('目录 loading 只更新目录合同，不读取具体型号详情', async () => {
    const events: boolean[] = []
    const apply = vi.fn()
    await runCatalogRequest({
      brand: 'generic',
      keyword: '',
      coordinator: createCatalogRequestCoordinator(),
      getSeries: vi.fn(async () => []),
      getModels: vi.fn(async () => [model]),
      setLoading: (value) => events.push(value),
      apply,
    })
    expect(events).toEqual([true, false])
    expect(apply).toHaveBeenCalledWith({ models: [model], selectedModelId: null, detail: null })
  })
})
