<template>
  <section class="content-panel">
    <div v-if="loading" class="detail-loading-state" role="status" aria-live="polite">
      <span class="detail-loading-dot"></span>
      <span>正在读取产品规格…</span>
    </div>
    <div v-else-if="!detail" class="detail-empty-state">
      <div class="detail-empty-icon" aria-hidden="true">⌕</div>
      <h2>选择产品，查看详细参数</h2>
      <p>可在左侧切换品牌与分类，或搜索型号、CPU、GPU，然后点击具体型号查看规格。</p>
      <div class="detail-empty-steps" aria-label="查看产品规格的步骤">
        <span><b>1</b> 选择品牌分类</span>
        <span><b>2</b> 搜索或浏览型号</span>
        <span><b>3</b> 点击查看规格</span>
      </div>
    </div>
    <template v-else>
    <div class="selection-tip">
      <div class="selection-tip-copy">
        <b>{{ detail.model_name }} <ProductBadges :model="detail" /></b>
        <span>{{ detail.title }} · {{ displaySeriesName(detail) }}</span>
      </div>
      <button class="detail-refresh-btn" type="button" :disabled="loading" data-testid="refresh-model-detail" @click="$emit('refresh-detail')">{{ loading ? '刷新中…' : '刷新详情' }}</button>
    </div>
    <article class="product-card open selected">
      <div class="product-header">
        <span class="product-name">{{ detail.model_name }} <ProductBadges :model="detail" /></span>
        <span class="product-title">{{ detail.title }}</span>
        <button class="compare-inline-btn" type="button" @click="$emit('toggle-compare', detail)">{{ isCompareSelected(detail.id) ? '移出对比' : '加入对比' }}</button>
        <span class="toggle-icon">▼</span>
      </div>
      <div class="product-body">
        <div class="summary-grid">
          <div v-for="item in summaryCards" :key="item.label" class="summary-card" :class="{ 'brand-summary-card': item.label === '品牌' }">
            <span>{{ item.label }}</span>
            <b v-if="item.label === '品牌'" class="brand-card-value">
              <span class="brand-card-name">{{ item.value }}</span>
              <span class="brand-card-logo" :class="`brand-card-logo-${detail.brand_code}`">{{ brandLogoText(detail.brand_code) }}</span>
            </b>
            <b v-else>{{ item.value }}</b>
          </div>
        </div>

        <section v-if="selectionNotesText" class="spec-group fixed-selection-note-group">
          <div class="spec-group-title">选型注意事项</div>
          <table class="spec-table normalized">
            <tbody>
              <tr>
                <td class="spec-key">选型注意事项</td>
                <td class="spec-val selection-note-cell">
                  <div class="selection-note-text-main">{{ selectionNotesText }}</div>
                </td>
              </tr>
            </tbody>
          </table>
        </section>


        <section v-for="(group, groupIndex) in groupedSpecs" :key="group.name" class="spec-group" :class="{ 'is-collapsed': isGroupCollapsed(group.name, groupIndex) }">
          <div class="spec-group-title" :class="{ 'mobile-spec-group-title': isMobileViewport }" :role="isMobileViewport ? 'button' : undefined" :tabindex="isMobileViewport ? 0 : undefined" :aria-expanded="isMobileViewport ? !isGroupCollapsed(group.name, groupIndex) : undefined" @click="toggleGroup(group.name, groupIndex)" @keydown.enter.prevent="toggleGroup(group.name, groupIndex)" @keydown.space.prevent="toggleGroup(group.name, groupIndex)">{{ group.name }}</div>
          <table class="spec-table normalized">
            <tbody>
              <tr v-for="spec in group.items" :key="spec.field_key">
                <td class="spec-key">{{ spec.label }}</td>
                <td class="spec-val">
                  <div v-if="spec.compatibleGpus?.length" class="compatible-gpu-row">
                    <button v-for="gpu in spec.compatibleGpus" :key="gpu.id" type="button" class="compatible-gpu-link" @click="$emit('jump-model', gpu.id)">{{ gpu.display_name }}</button>
                  </div>
                  <div v-else-if="isLinkSpec(spec)" class="link-spec-row">
                    <span class="link-spec-url">{{ spec.value }}</span>
                    <a class="selection-note-btn link-spec-btn" :href="spec.value" target="_blank" rel="noreferrer">打开链接</a>
                  </div>
                  <div v-else :class="['spec-lines', { 'cpu-lines': isCpuSpec(spec) }]">
                    <span v-for="(line, index) in displaySpecLines(spec)" :key="`${spec.field_key}-${index}`" :class="specLineClass(line, spec)">{{ line }}</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
    </article>
    </template>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { ModelDetail } from '../api'
import type { DisplaySpec, DisplaySpecGroup } from '../utils/gpuDisplay'
import ProductBadges from './ProductBadges.vue'
import { brandLogoText, displaySeriesName, isCpuSpec, isLinkSpec, specLineClass, splitSpecValue } from '../utils/displayRules'

defineProps<{
  detail: ModelDetail | null
  loading: boolean
  selectionNotesText: string
  summaryCards: { label: string; value: string }[]
  groupedSpecs: DisplaySpecGroup[]
  isCompareSelected: (id: number) => boolean
}>()

defineEmits<{
  'toggle-compare': [model: ModelDetail]
  'jump-model': [id: number]
  'refresh-detail': []
}>()

const collapsedGroups = ref(new Set<string>())
const isMobileViewport = window.matchMedia('(max-width: 1024px)').matches
const CORE_GROUP = /CPU|处理器|GPU|显卡|内存|存储|硬盘/

function isGroupCollapsed(name: string, index: number) {
  if (!window.matchMedia('(max-width: 1024px)').matches) return false
  return collapsedGroups.value.has(name) || (index > 0 && !CORE_GROUP.test(name) && !collapsedGroups.value.has(`opened:${name}`))
}

function toggleGroup(name: string, index: number) {
  if (!window.matchMedia('(max-width: 1024px)').matches) return
  const next = new Set(collapsedGroups.value)
  if (isGroupCollapsed(name, index)) { next.delete(name); next.add(`opened:${name}`) }
  else { next.add(name); next.delete(`opened:${name}`) }
  collapsedGroups.value = next
}

function displaySpecLines(spec: DisplaySpec) {
  return splitSpecValue(spec.value, spec.field_key, isCpuSpec(spec))
}
</script>
