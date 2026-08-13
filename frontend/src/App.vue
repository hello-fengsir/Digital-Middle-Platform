<template>
  <BrandHeader
    v-model:selected-brand="selectedBrand"
    :brand-options="brandOptions"
    :current-brand-name="currentBrandName"
    :page-product-title="pageProductTitle"
    :current-count="currentCount"
  />

  <main class="page-shell">
    <ModelNavigator
      :class="{ 'mobile-nav-hidden': !mobileNavigatorOpen && !!detail }"
      v-model:keyword="keyword"
      :selected-type="selectedType"
      :selected-model-id="selectedModelId"
      :loading="catalogLoading"
      :type-filters="typeFilters"
      :navigation-groups="navigationGroups"
      :is-type-open="isTypeOpen"
      :is-series-open="isSeriesOpen"
      @select-type="selectType"
      @toggle-type="toggleType"
      @toggle-series="toggleSeries"
      @select-model="selectModel"
    />

    <ModelDetail
      :detail="detail"
      :loading="detailLoading"
      :selection-notes-text="selectionNotesText"
      :summary-cards="summaryCards"
      :grouped-specs="groupedSpecs"
      :is-compare-selected="isCompareSelected"
      @toggle-compare="toggleCompareModel"
      @jump-model="jumpToModel"
      @refresh-detail="refreshCurrentDetail"
    />
  </main>

  <ProductCompare
    v-model:compare-only-diff="compareOnlyDiff"
    :compare-ids="compareIds"
    :compare-details="compareDetails"
    :compare-open="compareOpen"
    :compare-busy="compareBusy"
    :compare-rows-filtered="compareRowsFiltered"
    @clear="clearCompare"
    @open="openCompare"
    @close="closeCompare"
    @remove="removeCompare"
  />

  <AiAssistant :brand-code="selectedBrand" :force-close="isMobileViewport && (compareOpen || mobileOverlayOpen)" @jump-model="jumpToModel" @open-change="onAiOpenChange" />

  <footer class="footer">Product Hub · 产品资料与选型平台，页面实时读取已结构化的产品规格。</footer>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import './styles/mobile-public.css'
import { getBrands, getModel, getModels, getSeries, type Brand, type ModelDetail, type ModelSummary } from './api'
import BrandHeader from './components/BrandHeader.vue'
import ModelDetailView from './components/ModelDetail.vue'
import ModelNavigator from './components/ModelNavigator.vue'
import ProductCompare from './components/ProductCompare.vue'
import AiAssistant from './components/AiAssistant.vue'
import {
  displayProductType,
  displaySeriesName,
  EMPTY_HIDDEN_SPEC_KEYS,
  seriesSort,
  SPEC_GROUP_ORDER,
  summarizeSpec,
  typeSort,
} from './utils/displayRules'
import { catalogPageProductTitle, createCatalogRequestCoordinator, reconcileSelectedType, runCatalogJump, runCatalogRequest } from './utils/catalogLoader'
import { buildDisplaySpecGroups, comparisonSpecs } from './utils/gpuDisplay'

const ModelDetail = ModelDetailView

const brands = ref<Brand[]>([])
const models = ref<ModelSummary[]>([])
const detail = ref<ModelDetail | null>(null)
const requestedBrand = new URLSearchParams(window.location.search).get('brand')
const selectedBrand = ref(requestedBrand || 'generic')
const selectedModelId = ref<number | null>(null)
const keyword = ref('')
const catalogLoading = ref(true)
const detailLoading = ref(false)
const selectedType = ref('全部')
const collapsedTypes = ref(new Set<string>())
const collapsedSeries = ref(new Set<string>())
const compareIds = ref<number[]>([])
const compareDetails = ref<ModelDetail[]>([])
const compareOpen = ref(false)
const compareOnlyDiff = ref(false)
const compareBusy = ref(false)
const mobileNavigatorOpen = ref(true)
const mobileOverlayOpen = ref(false)
const browseScrollY = ref(0)
const jumpSource = ref<{ id: number; modelName: string } | null>(null)
const isMobileViewport = ref(window.matchMedia('(max-width: 1024px)').matches)
const suppressBrandWatch = ref(false)
const suppressKeywordWatch = ref(false)
const catalogRequests = createCatalogRequestCoordinator()
let detailRequestId = 0

const brandOptions = computed(() => brands.value.map((brand) => ({ label: brand.name, value: brand.code })))
const selectionNotesText = computed(() => detail.value?.specifications.find((item) => item.field_key === 'selection_notes')?.value?.trim() || '')
const currentBrandName = computed(() => brands.value.find((brand) => brand.code === selectedBrand.value)?.name || '示例品牌')
const currentCount = computed(() => brands.value.find((brand) => brand.code === selectedBrand.value)?.model_count || models.value.length)
const pageProductTitle = computed(() => {
  const types = [...new Set(models.value.map((model) => displayProductType(model)))].sort(typeSort)
  return catalogPageProductTitle(selectedBrand.value, types)
})

const filteredModels = computed(() => models.value)
const typeFilteredModels = computed(() => {
  if (selectedType.value === '全部') return filteredModels.value
  return filteredModels.value.filter((model) => displayProductType(model) === selectedType.value)
})
const typeFilters = computed(() => {
  const counts = new Map<string, number>()
  for (const model of models.value) {
    const type = displayProductType(model)
    counts.set(type, (counts.get(type) || 0) + 1)
  }
  const items = [...counts.entries()]
    .sort(([a], [b]) => typeSort(a, b))
    .map(([value, count]) => ({ value, label: value, count }))
  return [{ value: '全部', label: '全部', count: models.value.length }, ...items]
})
const navigationGroups = computed(() => {
  const typeMap = new Map<string, Map<string, ModelSummary[]>>()
  for (const model of typeFilteredModels.value) {
    const type = displayProductType(model)
    if (!typeMap.has(type)) typeMap.set(type, new Map())
    const seriesMap = typeMap.get(type)!
    const seriesName = displaySeriesName(model)
    seriesMap.set(seriesName, [...(seriesMap.get(seriesName) || []), model])
  }
  return [...typeMap.entries()].sort(([a], [b]) => typeSort(a, b)).map(([type, seriesMap]) => {
    const series = [...seriesMap.entries()]
      .sort(([a], [b]) => seriesSort(a, b, type))
      .map(([name, items]) => ({ key: `${type}::${name}`, name, items }))
    return { type, count: series.reduce((sum, item) => sum + item.items.length, 0), series }
  })
})
const groupedSpecs = computed(() => buildDisplaySpecGroups(detail.value, EMPTY_HIDDEN_SPEC_KEYS)
  .sort((a, b) => groupOrderIndex(a.name) - groupOrderIndex(b.name)))
const summaryCards = computed(() => {
  if (!detail.value) return []
  const productForm = findSpecValue(['rack_height', 'product_form'])
  return [
    { label: '品牌', value: detail.value.brand_name },
    { label: '型号', value: detail.value.model_name },
    { label: '产品类型', value: detail.value.product_type },
    { label: '系列/平台', value: [displaySeriesName(detail.value), detail.value.platform_vendor].filter(Boolean).join(' / ') || '待补充' },
    { label: '产品形态', value: productForm || '待补充' },
    { label: '来源状态', value: detail.value.source_ref ? '已结构化入库' : '待补充' },
  ]
})

type CompareRow = { key: string; group: string; label: string; values: Record<number, string>; isDiff: boolean }
const compareRows = computed<CompareRow[]>(() => {
  const rowMap = new Map<string, { key: string; group: string; label: string; values: Record<number, string> }>()
  for (const model of compareDetails.value) {
    for (const spec of comparisonSpecs(model)) {
      if (spec.field_key === 'selection_notes') continue
      if (EMPTY_HIDDEN_SPEC_KEYS.has(spec.field_key) && !spec.value.trim()) continue
      const key = spec.field_key || `${spec.group_name}:${spec.label}`
      if (!rowMap.has(key)) rowMap.set(key, { key, group: spec.group_name, label: spec.label, values: {} })
      rowMap.get(key)!.values[model.id] = summarizeSpec(spec.value, spec.field_key, 6)
    }
  }
  return [...rowMap.values()].map((row) => {
    const normalized = compareDetails.value.map((model) => (row.values[model.id] || '').trim())
    return { ...row, isDiff: new Set(normalized).size > 1 }
  }).sort((a, b) => groupOrderIndex(a.group) - groupOrderIndex(b.group) || a.label.localeCompare(b.label, 'zh-CN'))
})
const compareRowsFiltered = computed(() => compareOnlyDiff.value ? compareRows.value.filter((row) => row.isDiff) : compareRows.value)

function groupOrderIndex(group: string) {
  const index = SPEC_GROUP_ORDER.indexOf(group)
  return index === -1 ? 99 : index
}

function findSpecValue(keys: string[]) {
  const spec = detail.value?.specifications.find((item) => keys.includes(item.field_key))
  return spec ? summarizeSpec(spec.value, spec.field_key, 1) : ''
}

function isCompareSelected(id: number) {
  return compareIds.value.includes(id)
}

function toggleCompareModel(model: ModelSummary | ModelDetail) {
  if (isCompareSelected(model.id)) {
    removeCompare(model.id)
    return
  }
  if (compareIds.value.length >= 4) {
    window.alert('最多同时对比 4 个型号')
    return
  }
  compareIds.value = [...compareIds.value, model.id]
}

function removeCompare(id: number) {
  compareIds.value = compareIds.value.filter((item) => item !== id)
  compareDetails.value = compareDetails.value.filter((item) => item.id !== id)
  if (compareIds.value.length < 2) compareOpen.value = false
}

function clearCompare() {
  compareIds.value = []
  compareDetails.value = []
  compareOpen.value = false
}

async function openCompare() {
  if (compareIds.value.length < 2) return
  compareBusy.value = true
  try {
    compareDetails.value = await Promise.all(compareIds.value.map((id) => getModel(id)))
    mobileOverlayOpen.value = false
    compareOpen.value = true
  } finally {
    compareBusy.value = false
  }
}

function closeCompare() { compareOpen.value = false }

function showMobileNavigator() {
  browseScrollY.value = window.scrollY
  compareOpen.value = false
  mobileOverlayOpen.value = true
  mobileNavigatorOpen.value = true
  nextTick(() => document.querySelector<HTMLElement>('.side-search')?.focus())
}

function onAiOpenChange(open: boolean) {
  if (open && isMobileViewport.value) { compareOpen.value = false; mobileOverlayOpen.value = false }
}

let mobileContextBar: HTMLDivElement | null = null
function syncMobileContextBar() {
  if (!isMobileViewport.value) { mobileContextBar?.remove(); mobileContextBar = null; return }
  if (!mobileContextBar) {
    const shell = document.querySelector('.page-shell')
    if (!shell) return
    mobileContextBar = document.createElement('div')
    mobileContextBar.className = 'mobile-context-bar'
    mobileContextBar.setAttribute('aria-label', '移动端产品导航')
    shell.prepend(mobileContextBar)
  }
  mobileContextBar.replaceChildren()
  if (detail.value) {
    const back = document.createElement('button'); back.type = 'button'; back.className = 'mobile-back-models'; back.textContent = '← 返回型号列表'; back.addEventListener('click', showMobileNavigator); mobileContextBar.append(back)
  }
  const change = document.createElement('button'); change.type = 'button'; change.className = 'mobile-change-model'; change.textContent = detail.value ? '更换型号' : '浏览型号'; change.addEventListener('click', showMobileNavigator); mobileContextBar.append(change)
}
watch([isMobileViewport, detail], syncMobileContextBar, { flush: 'post', immediate: true })
onBeforeUnmount(() => { mobileContextBar?.remove(); mobileContextBar = null })

let gpuReturnButton: HTMLButtonElement | null = null
function syncGpuReturnButton() {
  gpuReturnButton?.remove(); gpuReturnButton = null
  if (!isMobileViewport.value || !jumpSource.value) return
  const anchor = document.querySelector('.content-panel .selection-tip')
  if (!anchor) return
  gpuReturnButton = document.createElement('button')
  gpuReturnButton.type = 'button'; gpuReturnButton.className = 'gpu-return-source'; gpuReturnButton.textContent = `← 返回来源 ${jumpSource.value.modelName}`
  gpuReturnButton.addEventListener('click', returnToJumpSource)
  anchor.before(gpuReturnButton)
}
watch([isMobileViewport, jumpSource, detail], syncGpuReturnButton, { flush: 'post' })
onBeforeUnmount(() => { gpuReturnButton?.remove(); gpuReturnButton = null })

function selectType(type: string) {
  selectedType.value = type
  clearSelection()
}

function toggleType(type: string) {
  const next = new Set(collapsedTypes.value)
  next.has(type) ? next.delete(type) : next.add(type)
  collapsedTypes.value = next
}

function isTypeOpen(type: string) {
  return keyword.value.trim() !== '' || !collapsedTypes.value.has(type)
}

function toggleSeries(key: string) {
  const next = new Set(collapsedSeries.value)
  next.has(key) ? next.delete(key) : next.add(key)
  collapsedSeries.value = next
}

function isSeriesOpen(series: { key: string; items: ModelSummary[] }) {
  return keyword.value.trim() !== '' || !collapsedSeries.value.has(series.key)
}

function resetCollapsedSeries() {
  const next = new Set<string>()
  for (const group of navigationGroups.value) {
    for (const series of group.series) {
      if (!series.items.some((model) => model.id === selectedModelId.value)) next.add(series.key)
    }
  }
  collapsedSeries.value = next
}

async function selectModel(id: number) {
  const requestId = ++detailRequestId
  selectedModelId.value = id
  detail.value = null
  detailLoading.value = true
  try {
    const target = await getModel(id)
    if (requestId !== detailRequestId) return
    detail.value = target
    resetCollapsedSeries()
    if (window.matchMedia('(max-width: 1024px)').matches) {
      mobileNavigatorOpen.value = false
      mobileOverlayOpen.value = false
      detailLoading.value = false
      await nextTick()
      await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
      const detailHeading = document.querySelector<HTMLElement>('.content-panel .product-name')
      detailHeading?.scrollIntoView({ block: 'start', behavior: 'auto' })
      if (detailHeading) {
        const stickyOffset = 104
        window.scrollBy({ top: detailHeading.getBoundingClientRect().top - stickyOffset, behavior: 'auto' })
        await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))
        const finalTop = detailHeading.getBoundingClientRect().top
        if (finalTop > 120) {
          const shell = document.querySelector<HTMLElement>('.page-shell')
          const oldPadding = shell?.style.paddingTop || ''
          if (shell) shell.style.paddingTop = '0px'
          window.scrollBy({ top: detailHeading.getBoundingClientRect().top - 104, behavior: 'auto' })
          if (shell) requestAnimationFrame(() => { shell.style.paddingTop = oldPadding })
        }
      }
    }
  } finally {
    if (requestId === detailRequestId) detailLoading.value = false
  }
}

async function refreshCurrentDetail() {
  const id = selectedModelId.value
  if (id == null) return
  const requestId = ++detailRequestId
  detailLoading.value = true
  try {
    const target = await getModel(id)
    if (requestId !== detailRequestId) return
    detail.value = target
    resetCollapsedSeries()
  } finally {
    if (requestId === detailRequestId) detailLoading.value = false
  }
}

function clearSelection() {
  detailRequestId += 1
  selectedModelId.value = null
  detail.value = null
  detailLoading.value = false
}

async function jumpToModel(id: number) {
  const source = isMobileViewport.value && detail.value ? { id: detail.value.id, modelName: detail.value.model_name } : null
  suppressBrandWatch.value = true
  suppressKeywordWatch.value = true
  keyword.value = ''
  try {
    await runCatalogJump({
      id,
      currentBrand: selectedBrand.value,
      coordinator: catalogRequests,
      getModel,
      getModels,
      setLoading: (value) => { detailLoading.value = value },
      apply: ({ target, models: targetModels }) => {
        if (target.brand_code !== selectedBrand.value) {
          selectedBrand.value = target.brand_code
          window.history.replaceState({}, '', `?brand=${encodeURIComponent(target.brand_code)}`)
          models.value = targetModels || []
          collapsedTypes.value = new Set()
          collapsedSeries.value = new Set()
          selectedType.value = '全部'
        }
        selectedModelId.value = target.id
        detail.value = target
        if (source && source.id !== target.id) jumpSource.value = source
        mobileNavigatorOpen.value = false
        resetCollapsedSeries()
      },
    })
  } finally {
    suppressBrandWatch.value = false
    suppressKeywordWatch.value = false
  }
}

async function returnToJumpSource() {
  const source = jumpSource.value
  if (!source) return
  jumpSource.value = null
  await jumpToModel(source.id)
  jumpSource.value = null
}

async function loadCatalog(keywordValue: string, loadSeries = false) {
  const brand = selectedBrand.value
  return runCatalogRequest({
    brand,
    keyword: keywordValue,
    coordinator: catalogRequests,
    loadSeries,
    getSeries,
    getModels,
    setLoading: (value) => { catalogLoading.value = value },
    apply: (result) => {
      models.value = result.models
      // 先修复类型筛选，再应用详情和折叠状态，避免旧类型制造假空侧栏。
      selectedType.value = reconcileSelectedType(result.models, selectedType.value)
      selectedModelId.value = result.selectedModelId
      detail.value = result.detail
      resetCollapsedSeries()
    },
  })
}

async function loadBrand() {
  clearSelection()
  collapsedTypes.value = new Set()
  collapsedSeries.value = new Set()
  selectedType.value = '全部'
  await loadCatalog(keyword.value.trim(), true)
}

watch(selectedBrand, () => {
  if (suppressBrandWatch.value) return
  loadBrand()
})

watch(keyword, () => {
  if (suppressKeywordWatch.value) return
  clearSelection()
  loadCatalog(keyword.value.trim())
})

onMounted(async () => {
  syncMobileContextBar()
  brands.value = await getBrands()
  if (!brands.value.some((brand) => brand.code === selectedBrand.value)) {
    selectedBrand.value = brands.value.find((brand) => brand.code === 'generic')?.code || brands.value[0]?.code || 'generic'
  }
  await loadBrand()
})
</script>
