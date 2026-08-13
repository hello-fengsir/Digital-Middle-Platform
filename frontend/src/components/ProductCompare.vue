<template>
  <div v-if="compareIds.length" class="compare-dock">
    <div>
      <b>产品参数对比</b>
      <span>已选 {{ compareIds.length }} / 4 个型号 · 支持跨品牌</span>
    </div>
    <div class="compare-dock-actions">
      <button type="button" class="ghost" @click="$emit('clear')">清空</button>
      <button type="button" :disabled="compareBusy || compareIds.length < 2" @click="$emit('open')">
        {{ compareBusy ? '加载中...' : '开始对比' }}
      </button>
    </div>
  </div>

  <div v-if="compareOpen" ref="modal" class="compare-modal" role="dialog" aria-modal="true" aria-label="产品参数对比" @keydown="onKeydown">
    <div class="compare-panel">
      <div class="compare-head">
        <div>
          <p class="compare-kicker">PRODUCT COMPARE</p>
          <h2>产品参数对比</h2>
          <p>支持跨品牌/跨品类对比，基于本地已入库参数横向对比，空值显示 “—”。</p>
        </div>
        <button ref="closeButton" type="button" class="ghost" @click="$emit('close')">关闭</button>
      </div>
      <div class="compare-toolbar">
        <label>
          <input :checked="compareOnlyDiff" type="checkbox" @change="updateOnlyDiff" />
          仅看差异
        </label>
        <span>{{ compareRowsFiltered.length }} 个参数项</span>
      </div>
      <div class="compare-table-wrap">
        <table class="compare-table">
          <thead>
            <tr>
              <th>参数项</th>
              <th v-for="model in compareDetails" :key="model.id">
                <div class="compare-model-head">
                  <b>{{ model.model_name }} <ProductBadges :model="model" /></b>
                  <span class="compare-model-brand">{{ model.brand_name }} · {{ model.product_type }} · {{ model.series }}</span>
                  <span>{{ model.title }}</span>
                  <button type="button" class="ghost mini" @click="$emit('remove', model.id)">移除</button>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in compareRowsFiltered" :key="row.key" :class="{ diff: row.isDiff }">
              <td class="compare-param"><span>{{ row.group }}</span><b>{{ row.label }}</b></td>
              <td v-for="model in compareDetails" :key="`${row.key}-${model.id}`">
                <div class="compare-value">{{ row.values[model.id] || '—' }}</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import type { ModelDetail } from '../api'
import ProductBadges from './ProductBadges.vue'

interface CompareRow {
  key: string
  group: string
  label: string
  values: Record<number, string>
  isDiff: boolean
}

const props = defineProps<{
  compareIds: number[]
  compareDetails: ModelDetail[]
  compareOpen: boolean
  compareOnlyDiff: boolean
  compareBusy: boolean
  compareRowsFiltered: CompareRow[]
}>()

const emit = defineEmits<{
  clear: []
  open: []
  close: []
  remove: [id: number]
  'update:compareOnlyDiff': [value: boolean]
}>()

const modal = ref<HTMLElement | null>(null)
const closeButton = ref<HTMLButtonElement | null>(null)
let compareHeadObserver: ResizeObserver | null = null

function updateCompareViewport() {
  const viewport = window.visualViewport
  document.documentElement.style.setProperty('--compare-vvh', `${viewport?.height ?? window.innerHeight}px`)
  document.documentElement.style.setProperty('--compare-vv-top', `${viewport?.offsetTop ?? 0}px`)
}

function bindCompareViewport(bind: boolean) {
  const viewport = window.visualViewport
  if (!viewport) return
  const action = bind ? 'addEventListener' : 'removeEventListener'
  viewport[action]('resize', updateCompareViewport)
  viewport[action]('scroll', updateCompareViewport)
}

function bindCompareHead(bind: boolean) {
  compareHeadObserver?.disconnect()
  compareHeadObserver = null
  if (!bind || !modal.value || typeof ResizeObserver === 'undefined') return
  const head = modal.value.querySelector<HTMLElement>('.compare-head')
  if (!head) return
  const update = () => modal.value?.style.setProperty('--compare-head-height', `${head.getBoundingClientRect().height}px`)
  compareHeadObserver = new ResizeObserver(update)
  compareHeadObserver.observe(head)
  update()
}

watch(() => props.compareOpen, (open) => {
  const mobile = matchMedia('(max-width:1024px)').matches
  document.body.classList.toggle('mobile-overlay-locked', open && mobile)
  if (mobile) {
    bindCompareViewport(open)
    updateCompareViewport()
    nextTick(() => {
      bindCompareHead(open)
      if (open) closeButton.value?.focus()
    })
  }
})
onBeforeUnmount(() => {
  bindCompareViewport(false)
  bindCompareHead(false)
  document.body.classList.remove('mobile-overlay-locked')
  document.documentElement.style.removeProperty('--compare-vvh')
  document.documentElement.style.removeProperty('--compare-vv-top')
})

function onKeydown(event: KeyboardEvent) {
  if (!matchMedia('(max-width:1024px)').matches) return
  if (event.key === 'Escape') { event.preventDefault(); emit('close'); return }
  if (event.key !== 'Tab' || !modal.value) return
  const nodes = [...modal.value.querySelectorAll<HTMLElement>('button,input,[tabindex]:not([tabindex="-1"])')].filter((el) => !el.hasAttribute('disabled'))
  if (!nodes.length) return
  const first = nodes[0], last = nodes[nodes.length - 1]
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
}

function updateOnlyDiff(event: Event) {
  emit('update:compareOnlyDiff', (event.target as HTMLInputElement).checked)
}
</script>
