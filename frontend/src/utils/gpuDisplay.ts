import type { CompatibleGpu, ModelDetail, SpecValue } from '../api'

export interface DisplaySpec extends SpecValue {
  compatibleGpus?: CompatibleGpu[]
}

export interface DisplaySpecGroup {
  name: string
  items: DisplaySpec[]
}

const GPU_FIELD_KEY = 'gpu_support'
const GPU_GROUP_NAME = 'GPU'

export function compatibleGpuNames(model: Pick<ModelDetail, 'compatible_gpus'>) {
  return (model.compatible_gpus || []).map((gpu) => gpu.display_name.trim()).filter(Boolean).join('\n')
}

export function buildDisplaySpecGroups(
  model: Pick<ModelDetail, 'specifications' | 'compatible_gpus'> | null,
  hiddenEmptyKeys: ReadonlySet<string>,
): DisplaySpecGroup[] {
  const groups = new Map<string, DisplaySpec[]>()
  const boundGpus = model?.compatible_gpus || []
  let gpuRowInserted = false

  for (const spec of model?.specifications || []) {
    if (spec.field_key === 'selection_notes') continue
    if (hiddenEmptyKeys.has(spec.field_key) && !spec.value.trim()) continue
    if (spec.field_key === GPU_FIELD_KEY) {
      if (gpuRowInserted) continue
      gpuRowInserted = true
      groups.set(spec.group_name, [
        ...(groups.get(spec.group_name) || []),
        boundGpus.length ? gpuDisplaySpec(spec, boundGpus) : spec,
      ])
      continue
    }
    groups.set(spec.group_name, [...(groups.get(spec.group_name) || []), spec])
  }

  if (boundGpus.length && !gpuRowInserted) {
    const generated = gpuDisplaySpec(undefined, boundGpus)
    groups.set(GPU_GROUP_NAME, [...(groups.get(GPU_GROUP_NAME) || []), generated])
  }
  return [...groups.entries()].map(([name, items]) => ({ name, items }))
}

export function comparisonSpecs(model: ModelDetail): SpecValue[] {
  const names = compatibleGpuNames(model)
  if (!names) return dedupeSpecs(model.specifications)
  let gpuRowInserted = false
  const specs: SpecValue[] = []
  for (const spec of model.specifications) {
    if (spec.field_key !== GPU_FIELD_KEY) {
      specs.push(spec)
      continue
    }
    if (gpuRowInserted) continue
    gpuRowInserted = true
    specs.push({ ...spec, value: names })
  }
  if (!gpuRowInserted) specs.push(gpuDisplaySpec(undefined, model.compatible_gpus))
  return dedupeSpecs(specs)
}

function gpuDisplaySpec(source: SpecValue | undefined, compatibleGpus: CompatibleGpu[]): DisplaySpec {
  return {
    group_code: source?.group_code || 'gpu',
    group_name: source?.group_name || GPU_GROUP_NAME,
    field_key: GPU_FIELD_KEY,
    label: source?.label || '显卡',
    value: compatibleGpus.map((gpu) => gpu.display_name.trim()).filter(Boolean).join('\n'),
    raw_label: source?.raw_label || source?.label || '显卡',
    source_ref: source?.source_ref || '',
    confidence: source?.confidence || '',
    compatibleGpus,
  }
}

function dedupeSpecs(specifications: SpecValue[]) {
  const seen = new Set<string>()
  return specifications.filter((spec) => {
    const key = spec.field_key || `${spec.group_name}:${spec.label}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}
