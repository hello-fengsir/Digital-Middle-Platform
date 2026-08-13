<template>
  <aside v-if="isResponsive" class="admin-sidebar" :class="{ 'navigator-collapsed': !navigatorOpen }">
    <div class="sidebar-head">
      <div>
        <p class="admin-kicker">Model Navigator</p>
        <h2>型号列表</h2>
      </div>
      <button type="button" class="ghost navigator-toggle" :aria-expanded="navigatorOpen" aria-controls="admin-model-navigator" @click="navigatorOpen = !navigatorOpen">{{ navigatorOpen ? '收起' : '更换' }}</button>
    </div>
    <div v-if="!navigatorOpen && currentModel" class="navigator-current" role="status">
      <span>当前型号</span><b>{{ currentModel.model_name }}</b>
      <small>{{ currentModel.brand_name }} · {{ currentModel.product_type }} · {{ currentModel.series }}</small>
    </div>
    <div id="admin-model-navigator" class="navigator-body">
      <ModelFilters />
      <ModelButtons :responsive="true" />
    </div>
  </aside>

  <!-- Preserve the formal 1366+ structure: no responsive-only nodes/classes enter desktop DOM. -->
  <aside v-else class="admin-sidebar">
    <div class="sidebar-head">
      <p class="admin-kicker">Model Navigator</p>
      <h2>型号列表</h2>
    </div>
    <section class="filter-panel">
      <div class="filter-row"><label>品牌</label><select :value="selectedBrand" @change="updateSelectedBrand"><option value="">全部品牌</option><option v-for="brand in brands" :key="brand.code" :value="brand.code">{{ brand.name }} / {{ brand.code }}</option></select></div>
      <div class="filter-row"><label>产品类型</label><select :value="selectedType" @change="updateSelectedType"><option value="">全部类型</option><option v-for="type in productTypes" :key="type" :value="type">{{ type }}</option></select></div>
      <div class="filter-row"><label>系列</label><select :value="selectedSeries" @change="updateSelectedSeries"><option value="">全部系列</option><option v-for="series in seriesOptions" :key="series" :value="series">{{ series }}</option></select></div>
      <div class="filter-row"><label>型号状态</label><select :value="statusFilter" @change="updateStatusFilter"><option value="active">在架型号</option><option value="deleted">已下架型号</option><option value="all">全部型号</option></select></div>
      <div class="filter-row"><label>型号关键字</label><input :value="keyword" type="search" placeholder="型号 / 标题" @input="updateKeyword" /></div>
      <div class="filter-actions"><button type="button" @click="$emit('start-create')">新增型号</button><button type="button" class="ghost" @click="$emit('refresh')">刷新</button></div>
    </section>
    <section class="model-list" aria-label="型号列表">
      <button v-for="model in filteredModels" :key="model.id" type="button" class="model-item" :class="{ active: detailId === model.id && !creating, deleted: model.status === 'deleted' || Boolean(model.deleted_at) }" @click="$emit('select-model', model.id)">
        <span class="model-name">{{ model.model_name }} <ProductBadges :model="model" /> <em v-if="model.status === 'deleted' || model.deleted_at" class="status-badge deleted">已下架</em></span>
        <span class="model-meta">{{ model.brand_name }} · {{ model.product_type }} · {{ model.series }}</span>
      </button>
      <div v-if="!loading && filteredModels.length === 0" class="empty-list">没有匹配型号</div>
    </section>
  </aside>
</template>

<script setup lang="ts">
import { Comment, computed, defineComponent, h, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Brand, ModelSummary } from '../adminApi'
import ProductBadges from '../../components/ProductBadges.vue'

const props = defineProps<{
  brands: Brand[]
  productTypes: string[]
  seriesOptions: string[]
  filteredModels: ModelSummary[]
  selectedBrand: string
  selectedType: string
  selectedSeries: string
  statusFilter: 'active' | 'deleted' | 'all'
  keyword: string
  loading: boolean
  creating: boolean
  detailId: number | null
}>()

const emit = defineEmits<{
  'update:selectedBrand': [value: string]
  'update:selectedType': [value: string]
  'update:selectedSeries': [value: string]
  'update:statusFilter': [value: 'active' | 'deleted' | 'all']
  'update:keyword': [value: string]
  refresh: []
  'start-create': []
  'select-model': [id: number]
}>()

const navigatorOpen = ref(true)
const isResponsive = ref(false)
const visibleCount = ref(20)
const currentModel = computed(() => props.filteredModels.find((model) => model.id === props.detailId) || null)
const visibleModels = computed(() => isResponsive.value ? props.filteredModels.slice(0, visibleCount.value) : props.filteredModels)
const hasMoreModels = computed(() => isResponsive.value && visibleCount.value < props.filteredModels.length)
const canCollapseModels = computed(() => isResponsive.value && visibleCount.value > 20)
let responsiveMedia: MediaQueryList | null = null

watch(() => [props.selectedBrand, props.selectedType, props.selectedSeries, props.statusFilter, props.keyword], () => {
  visibleCount.value = 20
})
watch(() => props.filteredModels.length, () => {
  visibleCount.value = Math.max(20, Math.min(visibleCount.value, props.filteredModels.length || 20))
})

function syncResponsive(event?: MediaQueryListEvent) {
  isResponsive.value = event ? event.matches : Boolean(responsiveMedia?.matches)
  if (!isResponsive.value) navigatorOpen.value = true
}

onMounted(() => {
  responsiveMedia = window.matchMedia('(max-width: 1024px)')
  syncResponsive()
  responsiveMedia.addEventListener('change', syncResponsive)
})

onBeforeUnmount(() => responsiveMedia?.removeEventListener('change', syncResponsive))

function selectModel(id: number, responsive: boolean) {
  emit('select-model', id)
  if (responsive) navigatorOpen.value = false
}

function updateSelectedBrand(event: Event) {
  emit('update:selectedBrand', (event.target as HTMLSelectElement).value)
  emit('refresh')
}
function updateSelectedType(event: Event) { emit('update:selectedType', (event.target as HTMLSelectElement).value) }
function updateSelectedSeries(event: Event) { emit('update:selectedSeries', (event.target as HTMLSelectElement).value) }
function updateStatusFilter(event: Event) {
  emit('update:statusFilter', (event.target as HTMLSelectElement).value as 'active' | 'deleted' | 'all')
  emit('refresh')
}
function updateKeyword(event: Event) { emit('update:keyword', (event.target as HTMLInputElement).value) }

const ModelFilters = defineComponent(() => () => h('section', { class: 'filter-panel' }, [
  h('div', { class: 'filter-row' }, [h('label', '品牌'), h('select', { value: props.selectedBrand, onChange: updateSelectedBrand }, [h('option', { value: '' }, '全部品牌'), ...props.brands.map((brand) => h('option', { value: brand.code, key: brand.code }, `${brand.name} / ${brand.code}`))])]),
  h('div', { class: 'filter-row' }, [h('label', '产品类型'), h('select', { value: props.selectedType, onChange: updateSelectedType }, [h('option', { value: '' }, '全部类型'), ...props.productTypes.map((type) => h('option', { value: type, key: type }, type))])]),
  h('div', { class: 'filter-row' }, [h('label', '系列'), h('select', { value: props.selectedSeries, onChange: updateSelectedSeries }, [h('option', { value: '' }, '全部系列'), ...props.seriesOptions.map((series) => h('option', { value: series, key: series }, series))])]),
  h('div', { class: 'filter-row' }, [h('label', '型号状态'), h('select', { value: props.statusFilter, onChange: updateStatusFilter }, [h('option', { value: 'active' }, '在架型号'), h('option', { value: 'deleted' }, '已下架型号'), h('option', { value: 'all' }, '全部型号')])]),
  h('div', { class: 'filter-row' }, [h('label', '型号关键字'), h('input', { value: props.keyword, type: 'search', placeholder: '型号 / 标题', onInput: updateKeyword })]),
  h('div', { class: 'filter-actions' }, [h('button', { type: 'button', onClick: () => emit('start-create') }, '新增型号'), h('button', { type: 'button', class: 'ghost', onClick: () => emit('refresh') }, '刷新')])
]))

const ModelButtons = defineComponent({
  props: { responsive: { type: Boolean, required: true } },
  setup(localProps) {
    return () => h('section', { class: 'model-list', 'aria-label': '型号列表' }, [
      ...visibleModels.value.map((model) => h('button', {
        key: model.id, type: 'button', class: ['model-item', { active: props.detailId === model.id && !props.creating, deleted: model.status === 'deleted' || Boolean(model.deleted_at) }],
        onClick: () => selectModel(model.id, localProps.responsive)
      }, [
        h('span', { class: 'model-name' }, [model.model_name, ' ', h(ProductBadges, { model }), ' ', ...(model.status === 'deleted' || model.deleted_at ? [h('em', { class: 'status-badge deleted' }, '已下架')] : [])]),
        h('span', { class: 'model-meta' }, `${model.brand_name} · ${model.product_type} · ${model.series}`)
      ])),
      ...(!props.loading && props.filteredModels.length === 0 ? [h('div', { class: 'empty-list' }, '没有匹配型号')] : []),
      ...(localProps.responsive && props.filteredModels.length ? [h('div', { class: 'mobile-list-controls', role: 'group', 'aria-label': '型号分页控制' }, [
        h('span', { class: 'mobile-list-count', 'aria-live': 'polite' }, `已显示 ${visibleModels.value.length} / ${props.filteredModels.length}`),
        ...(hasMoreModels.value ? [h('button', { type: 'button', class: 'ghost mobile-load-more', onClick: () => { visibleCount.value += 20 } }, '加载更多')] : []),
        ...(canCollapseModels.value ? [h('button', { type: 'button', class: 'ghost mobile-collapse-list', onClick: () => { visibleCount.value = 20 } }, '收起到首批')] : [])
      ])] : [])
    ])
  }
})
</script>
