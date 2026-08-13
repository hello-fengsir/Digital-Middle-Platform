import { describe, expect, it } from 'vitest'
import type { CompatibleGpu, ModelDetail, SpecValue } from '../api'
import { buildDisplaySpecGroups, comparisonSpecs } from './gpuDisplay'

const hidden = new Set<string>()
const gpu = (id: number, display_name: string): CompatibleGpu => ({ id, display_name, model_name: display_name, title: display_name, brand_code: 'accessory', product_type: '显卡', series: 'GPU' })
const spec = (field_key: string, value: string, group_name = 'GPU', label = '显卡'): SpecValue => ({ field_key, value, group_name, label, group_code: group_name.toLowerCase(), raw_label: label, source_ref: '', confidence: '' })
const model = (specifications: SpecValue[], compatible_gpus: CompatibleGpu[]): ModelDetail => ({ id: 1, brand_code: 'x', brand_name: 'X', product_type: '服务器', series: 'S', model_name: 'M', title: 'M', source_ref: '', specifications, compatible_gpus })

function gpuRows(detail: ModelDetail) {
  return buildDisplaySpecGroups(detail, hidden).flatMap((group) => group.items).filter((item) => item.field_key === 'gpu_support')
}

describe('GPU display projection', () => {
  it('replaces the historic GPU row with clickable bound models', () => {
    const rows = gpuRows(model([spec('gpu_support', '历史静态型号')], [gpu(7, 'NVIDIA L20')]))
    expect(rows).toHaveLength(1)
    expect(rows[0].value).toBe('NVIDIA L20')
    expect(rows[0].compatibleGpus?.[0].id).toBe(7)
  })

  it('keeps the historic static value when no relation exists', () => {
    const rows = gpuRows(model([spec('gpu_support', '历史静态型号')], []))
    expect(rows).toHaveLength(1)
    expect(rows[0].value).toBe('历史静态型号')
    expect(rows[0].compatibleGpus).toBeUndefined()
  })

  it('creates a display-only GPU group and row when the source group is absent', () => {
    const groups = buildDisplaySpecGroups(model([spec('memory', '1TB', '内存', '内存')], [gpu(7, 'NVIDIA L20')]), hidden)
    expect(groups.find((group) => group.name === 'GPU')?.items[0]).toMatchObject({ field_key: 'gpu_support', label: '显卡', value: 'NVIDIA L20' })
  })

  it('renders multiple cards once and removes duplicate gpu_support rows', () => {
    const rows = gpuRows(model([spec('gpu_support', '旧一'), spec('gpu_support', '旧二')], [gpu(7, 'NVIDIA L20'), gpu(8, 'NVIDIA L40S')]))
    expect(rows).toHaveLength(1)
    expect(rows[0].compatibleGpus?.map((item) => item.id)).toEqual([7, 8])
    expect(rows[0].value).toBe('NVIDIA L20\nNVIDIA L40S')
  })

  it('projects relations into comparison and falls back to static values', () => {
    const bound = comparisonSpecs(model([spec('gpu_support', '历史静态型号')], [gpu(7, 'NVIDIA L20'), gpu(8, 'NVIDIA L40S')]))
    const unbound = comparisonSpecs(model([spec('gpu_support', '历史静态型号')], []))
    const generated = comparisonSpecs(model([spec('memory', '1TB', '内存', '内存')], [gpu(7, 'NVIDIA L20')]))
    expect(bound.find((item) => item.field_key === 'gpu_support')?.value).toBe('NVIDIA L20\nNVIDIA L40S')
    expect(unbound.find((item) => item.field_key === 'gpu_support')?.value).toBe('历史静态型号')
    expect(generated.find((item) => item.field_key === 'gpu_support')).toMatchObject({ group_name: 'GPU', label: '显卡', value: 'NVIDIA L20' })
  })
})
