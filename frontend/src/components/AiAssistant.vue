<template>
  <div class="ai-assistant" :class="{ open }">
    <button ref="trigger" class="ai-fab" type="button" :aria-expanded="isMobileViewport ? open : undefined" @click="setOpen(!open)">{{ open ? '×' : 'AI选型' }}</button>
    <section v-if="open" ref="dialog" class="ai-chat-card" role="dialog" aria-modal="true" aria-label="天枢 AI 选型助手" @keydown="onDialogKeydown">
      <header>
        <div>
          <b>天枢 AI 选型助手</b>
          <span>刷新清空 · 不保存聊天记录</span>
        </div>
      </header>
      <div class="ai-chat-body">
        <div v-for="(msg, index) in messages" :key="index" :class="['ai-msg', msg.role]">
          <div class="ai-msg-text" v-html="formatMessage(msg.text)"></div>
          <div v-if="msg.coverage?.length" class="ai-brand-coverage" aria-label="品牌覆盖情况">
            <span v-for="brand in msg.coverage" :key="brand.brand_code" :class="brand.status">
              {{ brand.message }}
            </span>
          </div>
          <div v-if="msg.models?.length" class="ai-model-links" :class="{ pending: msg.matchStatus === 'partial_match' }">
            <strong class="ai-model-links-label">{{ msg.candidateLabel || (msg.matchStatus === 'partial_match' ? '待核验候选' : '推荐型号') }}</strong>
            <button v-for="model in msg.models" :key="model.id" type="button" @click="$emit('jump-model', model.id)">{{ model.model_name }} <ProductBadges :model="model" /></button>
          </div>
        </div>
      </div>
      <form class="ai-chat-input" @submit.prevent="send">
        <div v-if="busy" class="ai-busy-hint">正在调用 AI 并基于本地资料库生成建议，通常需要 10–30 秒，请勿重复点击。</div>
        <textarea
          v-model="input"
          :maxlength="MAX_INPUT_LENGTH"
          aria-describedby="ai-input-count"
          placeholder="粘贴客户需求，例如：2U、双L40S、512G内存、国产优先"
        />
        <span id="ai-input-count" class="ai-input-count" aria-live="polite">{{ input.length }} / {{ MAX_INPUT_LENGTH }} 字</span>
        <button type="submit" :disabled="busy || !input.trim()">{{ busy ? '分析中' : '推荐' }}</button>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { recommendModels, type AiBrandCoverage, type AiRecommendModel } from '../api'
import { normalizeMatchStatus, recommendationLabel, visibleRecommendationModels, type MatchStatus } from '../utils/aiRecommendation'
import ProductBadges from './ProductBadges.vue'

const MAX_INPUT_LENGTH = 2000
const isMobileViewport = window.matchMedia('(max-width: 1024px)').matches

const props = defineProps<{ brandCode: string; forceClose?: boolean }>()
const emit = defineEmits<{ 'jump-model': [id: number]; 'open-change': [open: boolean] }>()
const open = ref(false)
const trigger = ref<HTMLButtonElement | null>(null)
const dialog = ref<HTMLElement | null>(null)
const input = ref('')
const busy = ref(false)
type ChatMessage = { role: 'user' | 'assistant'; text: string; models?: AiRecommendModel[]; matchStatus?: MatchStatus; candidateLabel?: string; coverage?: AiBrandCoverage[] }

const messages = ref<ChatMessage[]>([
  { role: 'assistant', text: '把客户需求粘贴到这里，我会基于天枢库全品牌、全产品线已有数据匹配和推荐型号。' },
])

function updateVisualViewport() {
  const viewport = window.visualViewport
  document.documentElement.style.setProperty('--ai-vvh', `${viewport?.height ?? window.innerHeight}px`)
  document.documentElement.style.setProperty('--ai-vv-top', `${viewport?.offsetTop ?? 0}px`)
}

function bindVisualViewport(bind: boolean) {
  const viewport = window.visualViewport
  if (!viewport) return
  const action = bind ? 'addEventListener' : 'removeEventListener'
  viewport[action]('resize', updateVisualViewport)
  viewport[action]('scroll', updateVisualViewport)
}

function setOpen(value: boolean) {
  open.value = value
  emit('open-change', value)
  const mobile = matchMedia('(max-width:1024px)').matches
  document.body.classList.toggle('mobile-overlay-locked', value && mobile)
  if (mobile) {
    bindVisualViewport(value)
    updateVisualViewport()
    nextTick(() => value ? dialog.value?.querySelector<HTMLElement>('textarea,button')?.focus() : trigger.value?.focus())
  }
}

function onDialogKeydown(event: KeyboardEvent) {
  if (!matchMedia('(max-width:1024px)').matches) return
  if (event.key === 'Escape') { event.preventDefault(); setOpen(false); return }
  if (event.key !== 'Tab' || !dialog.value) return
  const nodes = [...dialog.value.querySelectorAll<HTMLElement>('button,textarea,a[href],[tabindex]:not([tabindex="-1"])')].filter((el) => !el.hasAttribute('disabled'))
  if (!nodes.length) return
  const first = nodes[0], last = nodes[nodes.length - 1]
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
}

watch(() => props.forceClose, (value) => { if (value && open.value) setOpen(false) })
onBeforeUnmount(() => {
  bindVisualViewport(false)
  document.body.classList.remove('mobile-overlay-locked')
  document.documentElement.style.removeProperty('--ai-vvh')
  document.documentElement.style.removeProperty('--ai-vv-top')
})


function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function isMarkdownSeparator(line: string) {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line)
}

function parseTableRow(line: string) {
  const trimmed = line.trim()
  if (!trimmed.includes('|')) return null
  const body = trimmed.replace(/^\|/, '').replace(/\|$/, '')
  const cells = body.split('|').map((cell) => cell.trim())
  return cells.length >= 2 ? cells : null
}

function formatInline(value: string) {
  return escapeHtml(value)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
}

function formatMessage(text: string) {
  const lines = text.split('\n')
  const parts: string[] = []
  for (let i = 0; i < lines.length; i += 1) {
    const row = parseTableRow(lines[i])
    const nextIsSep = i + 1 < lines.length && isMarkdownSeparator(lines[i + 1])
    if (row && nextIsSep) {
      const headers = row
      i += 2
      const bodyRows: string[][] = []
      while (i < lines.length) {
        const body = parseTableRow(lines[i])
        if (!body || isMarkdownSeparator(lines[i])) break
        bodyRows.push(body)
        i += 1
      }
      i -= 1
      parts.push(`<div class="ai-table-wrap"><table class="ai-config-table"><thead><tr>${headers.map((h) => `<th>${formatInline(h)}</th>`).join('')}</tr></thead><tbody>${bodyRows.map((cells) => `<tr>${headers.map((_, idx) => `<td>${formatInline(cells[idx] || '')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`)
      continue
    }
    const line = lines[i]
    if (!line.trim()) {
      parts.push('<br />')
    } else if (/^#{1,4}\s+/.test(line)) {
      parts.push(`<div class="ai-msg-heading">${formatInline(line.replace(/^#{1,4}\s+/, ''))}</div>`)
    } else if (/^\s*[-*]\s+/.test(line)) {
      parts.push(`<div class="ai-msg-bullet">• ${formatInline(line.replace(/^\s*[-*]\s+/, ''))}</div>`)
    } else {
      parts.push(`<div>${formatInline(line)}</div>`)
    }
  }
  return parts.join('')
}

async function send() {
  const text = input.value.trim()
  if (!text) return
  input.value = ''
  messages.value.push({ role: 'user', text })
  busy.value = true
  try {
    const result = await recommendModels(text)
    const matchStatus = normalizeMatchStatus(result.match_status)
    const sourceNote = result.source === 'ai' ? '\n\n来源：AI + 天枢本地资料库候选' : '\n\n来源：本地资料库候选（AI 未启用或调用失败）'
    const warn = result.warning ? `\n提示：${result.warning}` : ''
    messages.value.push({
      role: 'assistant',
      text: `${result.answer}${sourceNote}${warn}`,
      models: visibleRecommendationModels(result),
      matchStatus,
      candidateLabel: recommendationLabel(result),
      coverage: result.coverage?.brand_results,
    })
  } catch (error) {
    messages.value.push({ role: 'assistant', text: `推荐失败：${error instanceof Error ? error.message : String(error)}` })
  } finally {
    busy.value = false
  }
}
</script>
