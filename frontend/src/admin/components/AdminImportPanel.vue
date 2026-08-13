<template>
  <section class="editor-panel import-panel">
    <div class="panel-head compact">
      <div><p class="admin-kicker">Bulk Import</p><h2>Excel 模板导入</h2></div>
      <div class="panel-actions">
        <button type="button" class="ghost" @click="$emit('download-template')">下载模板</button>
        <button type="button" :disabled="!importFile || importBusy" @click="$emit('preview-import')">预览导入</button>
        <button type="button" :disabled="!importFile || importBusy" @click="$emit('run-import')">执行导入</button>
      </div>
    </div>
    <div class="import-hint">固定模板导入：下载模板填写后上传，先预览再执行。</div>
    <input type="file" accept=".xlsx" @change="onImportFileChange" />

    <div class="markdown-import-box" :class="{ 'mobile-markdown-fullscreen': isCompact && markdownFullscreen }">
      <div class="panel-head compact nested">
        <div><p class="admin-kicker">Markdown Import</p><h2>Markdown 批量导入</h2></div>
        <div ref="markdownActions" class="panel-actions">
          <button type="button" class="ghost" @click="fillMarkdownExample">填入示例</button>
          <button type="button" :disabled="!markdownText.trim() || importBusy" @click="$emit('preview-markdown')">预览 Markdown</button>
          <button type="button" :disabled="!markdownText.trim() || importBusy" @click="$emit('run-markdown')">执行 Markdown 导入</button>
        </div>
      </div>
      <div class="import-hint">每个型号用一级标题 <code># 型号</code> 开始；基础字段用“品牌代码：/产品类型：/系列：/型号：”；规格字段按二级标题分组，逐行写“字段：值”。</div>
      <textarea
        class="markdown-import-textarea"
        :value="markdownText"
        placeholder="# NF5280M7
品牌代码：inspur
品牌名称：浪潮
产品类型：服务器
系列：NF5280
型号：NF5280M7
标题：浪潮 NF5280M7

## 处理器
- 处理器：Intel Xeon
- CPU路数：2"
        @input="onMarkdownInput"
      />
    </div>

    <div v-if="importPreview" class="import-preview">
      <div class="import-summary">{{ importPreview.total_rows }} 行 / 有效 {{ importPreview.valid_rows }} / 无效 {{ importPreview.invalid_rows }} / 规格 {{ importPreview.sheet_rows.length }}</div>
      <div v-if="importPreview.errors.length" class="import-errors"><div v-for="err in importPreview.errors" :key="err">{{ err }}</div></div>
      <div v-if="importPreview.rows.length" class="import-table-wrap">
        <table class="import-table"><thead><tr><th>品牌</th><th>类型</th><th>系列</th><th>型号</th><th>标题</th></tr></thead><tbody>
          <tr v-for="row in importPreview.rows.slice(0, 12)" :key="row.model_name + row.row_number"><td>{{ row.brand_code }}</td><td>{{ row.product_type }}</td><td>{{ row.series }}</td><td>{{ row.model_name }}</td><td>{{ row.title }}</td></tr>
        </tbody></table>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, watch, ref } from 'vue'
import type { ImportPreviewOut } from '../adminApi'

const props = defineProps<{
  importFile: File | null
  importBusy: boolean
  importPreview: ImportPreviewOut | null
  markdownText: string
}>()

const emit = defineEmits<{
  'update:importFile': [value: File | null]
  'update:markdownText': [value: string]
  'clear-preview': []
  'download-template': []
  'preview-import': []
  'run-import': []
  'preview-markdown': []
  'run-markdown': []
}>()

const compactQuery = window.matchMedia('(max-width: 1024px)')
const isCompact = ref(compactQuery.matches)
const markdownFullscreen = ref(false)
const markdownActions = ref<HTMLElement | null>(null)
let expandButton: HTMLButtonElement | null = null
let priorBodyOverflow = ''

function syncExpandButton() {
  if (!isCompact.value) {
    expandButton?.remove()
    expandButton = null
    return
  }
  if (!expandButton) {
    expandButton = document.createElement('button')
    expandButton.type = 'button'
    expandButton.className = 'ghost mobile-markdown-expand'
    expandButton.addEventListener('click', toggleMarkdownFullscreen)
    markdownActions.value?.prepend(expandButton)
  }
  expandButton.setAttribute('aria-expanded', String(markdownFullscreen.value))
  expandButton.textContent = markdownFullscreen.value ? '退出全屏' : '全屏编辑'
}

function toggleMarkdownFullscreen() {
  if (!isCompact.value) return
  markdownFullscreen.value = !markdownFullscreen.value
}

function onCompactChange(event: MediaQueryListEvent) {
  isCompact.value = event.matches
  if (!event.matches) markdownFullscreen.value = false
  syncExpandButton()
}

watch(markdownFullscreen, (expanded) => {
  syncExpandButton()
  if (expanded) {
    priorBodyOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = priorBodyOverflow
  }
})
onMounted(() => {
  compactQuery.addEventListener('change', onCompactChange)
  syncExpandButton()
})
onBeforeUnmount(() => {
  compactQuery.removeEventListener('change', onCompactChange)
  expandButton?.removeEventListener('click', toggleMarkdownFullscreen)
  expandButton?.remove()
  if (markdownFullscreen.value) document.body.style.overflow = priorBodyOverflow
})

function onImportFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  emit('update:importFile', input.files?.[0] || null)
  emit('clear-preview')
}

function onMarkdownInput(event: Event) {
  emit('update:markdownText', (event.target as HTMLTextAreaElement).value)
  emit('clear-preview')
}

function fillMarkdownExample() {
  emit('update:markdownText', `# NF5280M7
品牌代码：inspur
品牌名称：浪潮
产品类型：服务器
系列：NF5280
型号：NF5280M7
标题：浪潮 NF5280M7 双路服务器
平台厂商：Intel
代际：G7

## 处理器
- 处理器：Intel Xeon 可扩展处理器
- CPU路数：2

## 内存
- 内存：DDR5 ECC
- 最大内存容量：4TB

## 存储
- 硬盘：支持多种 2.5/3.5 英寸盘位配置

## 基础信息
- 官网参数链接：https://example.com/params
- 产品彩页：https://example.com/brochure.pdf`)
  emit('clear-preview')
}
</script>
