<template>
  <aside class="side-panel">
    <div class="side-head">
      <div class="side-eyebrow">PRODUCT NAVIGATOR</div>
      <div class="side-title">按品类 / 系列 / 型号选择</div>
      <div class="type-filters" aria-label="产品类型筛选">
        <button
          v-for="type in typeFilters"
          :key="type.value"
          class="type-chip"
          :class="{ active: selectedType === type.value }"
          type="button"
          @click="$emit('select-type', type.value)"
        >
          {{ type.label }} <span>{{ type.count }}</span>
        </button>
      </div>
      <input :value="keyword" class="side-search" type="search" placeholder="型号 / CPU / GPU，空格分词 AND" @input="updateKeyword" />
    </div>
    <div class="side-body">
      <section v-for="typeGroup in navigationGroups" :key="typeGroup.type" class="side-category">
        <button class="side-category-title" type="button" @click="$emit('toggle-type', typeGroup.type)">
          <span>{{ typeGroup.type }}</span>
          <span class="side-count">{{ typeGroup.count }}</span>
        </button>
        <div v-if="isTypeOpen(typeGroup.type)" class="side-series-list">
          <section v-for="series in typeGroup.series" :key="series.key" class="side-series">
            <button class="side-series-title" type="button" @click="$emit('toggle-series', series.key)">
              <span>{{ series.name }}</span>
              <span>{{ series.items.length }}</span>
            </button>
            <div v-if="isSeriesOpen(series)" class="side-models">
              <button
                v-for="model in series.items"
                :key="model.id"
                class="side-model"
                :class="{ active: selectedModelId === model.id }"
                type="button"
                @click="$emit('select-model', model.id)"
              >
                <span class="side-model-name">{{ model.model_name }} <ProductBadges :model="model" /></span>
                <span class="side-model-group">{{ model.title }}</span>
                <span v-if="model.gpu_slot_width || model.gpu_cooling_type" class="side-model-gpu-tags">
                  <span v-if="model.gpu_slot_width" class="gpu-mini-tag">{{ model.gpu_slot_width }}</span>
                  <span v-if="model.gpu_cooling_type" class="gpu-mini-tag">{{ model.gpu_cooling_type }}</span>
                </span>
              </button>
            </div>
          </section>
        </div>
      </section>
      <div v-if="!loading && navigationGroups.length === 0" class="side-empty">没有匹配型号</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { ModelSummary } from '../api'
import ProductBadges from './ProductBadges.vue'

interface TypeFilter {
  value: string
  label: string
  count: number
}

interface NavigationSeries {
  key: string
  name: string
  items: ModelSummary[]
}

interface NavigationGroup {
  type: string
  count: number
  series: NavigationSeries[]
}

defineProps<{
  keyword: string
  selectedType: string
  selectedModelId: number | null
  loading: boolean
  typeFilters: TypeFilter[]
  navigationGroups: NavigationGroup[]
  isTypeOpen: (type: string) => boolean
  isSeriesOpen: (series: NavigationSeries) => boolean
}>()

const emit = defineEmits<{
  'update:keyword': [value: string]
  'select-type': [value: string]
  'toggle-type': [value: string]
  'toggle-series': [value: string]
  'select-model': [id: number]
}>()

function updateKeyword(event: Event) {
  emit('update:keyword', (event.target as HTMLInputElement).value)
}
</script>
