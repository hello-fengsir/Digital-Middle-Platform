<template>
  <section class="editor-panel compatible-gpu-panel">
    <div class="panel-head compact">
      <div>
        <p class="admin-kicker">GPU Compatibility</p>
        <h2>兼容显卡</h2>
      </div>
      <span class="hint">数据源：配件 · 显卡；需在本面板独立保存</span>
    </div>
    <input v-model.trim="keyword" class="gpu-search" placeholder="搜索显卡型号 / 显存，例如：4090、48GB" />
    <div class="compatible-gpu-select">
      <label v-for="gpu in visibleOptions" :key="gpu.id" class="gpu-option">
        <input type="checkbox" :checked="selectedIds.includes(gpu.id)" :disabled="disabled || saving" @change="toggle(gpu.id, ($event.target as HTMLInputElement).checked)" />
        <span>{{ gpu.display_name }}</span>
      </label>
      <div v-if="!filteredOptions.length" class="empty-hint">没有匹配的显卡</div>
    </div>
    <div v-if="isCompact && filteredOptions.length > 12" class="mobile-gpu-controls">
      <span aria-live="polite">已显示 {{ visibleOptions.length }} / {{ filteredOptions.length }}</span>
      <button type="button" class="ghost" :aria-expanded="gpuExpanded" @click="gpuExpanded = !gpuExpanded">{{ gpuExpanded ? '收起显卡' : '展开全部显卡' }}</button>
    </div>
    <div class="compatible-gpu-actions">
      <span class="hint" :class="{ 'gpu-dirty-hint': dirty }">{{ dirty ? '选择已变化，尚未保存' : '当前选择已保存' }}</span>
      <button type="button" :disabled="disabled || saving || !dirty" data-testid="save-compatible-gpus" @click="$emit('save')">
        {{ saving ? '保存中…' : '保存兼容显卡' }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { CompatibleGpu } from '../adminApi'

const props = defineProps<{
  gpuOptions: CompatibleGpu[]
  selectedIds: number[]
  disabled: boolean
  saving: boolean
  dirty: boolean
}>()

const emit = defineEmits<{
  'update:selectedIds': [value: number[]]
  save: []
}>()

const keyword = ref('')
const isCompact = ref(false)
const gpuExpanded = ref(false)
let compactMedia: MediaQueryList | null = null
const filteredOptions = computed(() => {
  const q = keyword.value.toLowerCase()
  if (!q) return props.gpuOptions
  return props.gpuOptions.filter((gpu) => [gpu.model_name, gpu.display_name, gpu.memory || '', gpu.series].join(' ').toLowerCase().includes(q))
})
const visibleOptions = computed(() => isCompact.value && !gpuExpanded.value ? filteredOptions.value.slice(0, 12) : filteredOptions.value)

function syncCompact(event?: MediaQueryListEvent) {
  isCompact.value = event ? event.matches : Boolean(compactMedia?.matches)
  if (!isCompact.value) gpuExpanded.value = false
}

watch(keyword, () => { gpuExpanded.value = false })
onMounted(() => {
  compactMedia = window.matchMedia('(max-width: 1024px)')
  syncCompact()
  compactMedia.addEventListener('change', syncCompact)
})
onBeforeUnmount(() => compactMedia?.removeEventListener('change', syncCompact))

function toggle(id: number, checked: boolean) {
  const next = checked ? [...props.selectedIds, id] : props.selectedIds.filter((item) => item !== id)
  emit('update:selectedIds', [...new Set(next)])
}
</script>
