<template>
  <section class="editor-panel ai-agent-rule-panel" :class="{ 'mobile-rule-fullscreen': isCompact && editorFullscreen }" aria-labelledby="ai-agent-rule-title">
    <div class="panel-head compact">
      <div>
        <p class="admin-kicker">Runtime Policy</p>
        <h2 id="ai-agent-rule-title">智能体规则</h2>
      </div>
    </div>

    <p class="ai-agent-rule-meta" aria-label="规则元数据">
      <span>固定文件：AI_SELECTION_AGENT.md</span>
      <span>来源：{{ metadata?.source === 'runtime' ? '运行时文件' : '内置默认' }}</span>
      <span>更新时间：{{ formattedUpdatedAt }}</span>
      <span>SHA：{{ metadata?.sha256.slice(0, 12) || '—' }}</span>
    </p>

    <p class="ai-agent-rule-security">安全边界：此 Markdown 仅指导问诊、解释与风险提示；候选型号、匹配状态、兼容关系和 BOM 事实仍只由本地证据与后端确定性逻辑决定。</p>

    <textarea
      v-model="content"
      class="ai-agent-rule-editor"
      maxlength="20000"
      aria-label="智能体 Markdown 规则"
      :disabled="loading || saving"
      @input="message = ''"
    />

    <div class="ai-agent-rule-toolbar">
      <span class="ai-agent-rule-count" :class="{ over: content.length > MAX_LENGTH }">{{ content.length }} / {{ MAX_LENGTH }}<template v-if="dirty"> · 未保存</template></span>
      <div ref="ruleActions" class="panel-actions">
        <button type="button" class="ghost" :disabled="!dirty || saving" @click="discard">撤销未保存修改</button>
        <button type="button" :disabled="!canSave" @click="save">{{ saving ? '保存中…' : '保存规则' }}</button>
      </div>
    </div>

    <p v-if="loading" class="ai-agent-rule-status">正在加载规则…</p>
    <p v-else-if="message" class="ai-agent-rule-status" :class="{ error: messageType === 'error' }" role="status">{{ message }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getAiAgentRule, saveAiAgentRule, type AiAgentRule } from '../adminApi'

const MAX_LENGTH = 20000
const props = defineProps<{ token: string }>()
const emit = defineEmits<{ saved: [rule: AiAgentRule] }>()
const content = ref('')
const serverContent = ref('')
const metadata = ref<AiAgentRule | null>(null)
const loading = ref(true)
const saving = ref(false)
const message = ref('')
const messageType = ref<'ok' | 'error'>('ok')
const compactQuery = window.matchMedia('(max-width: 1024px)')
const isCompact = ref(compactQuery.matches)
const editorFullscreen = ref(false)
const ruleActions = ref<HTMLElement | null>(null)
let expandButton: HTMLButtonElement | null = null

function syncExpandButton() {
  if (!isCompact.value) {
    expandButton?.remove()
    expandButton = null
    return
  }
  if (!expandButton) {
    expandButton = document.createElement('button')
    expandButton.type = 'button'
    expandButton.className = 'mobile-rule-expand'
    expandButton.addEventListener('click', toggleEditorFullscreen)
    ruleActions.value?.prepend(expandButton)
  }
  expandButton.setAttribute('aria-expanded', String(editorFullscreen.value))
  expandButton.textContent = editorFullscreen.value ? '退出全屏' : '全屏编辑'
}

function toggleEditorFullscreen() {
  if (!isCompact.value) return
  editorFullscreen.value = !editorFullscreen.value
  syncExpandButton()
}

function onCompactChange(event: MediaQueryListEvent) {
  isCompact.value = event.matches
  if (!event.matches) editorFullscreen.value = false
  syncExpandButton()
}
const dirty = computed(() => content.value !== serverContent.value)
const canSave = computed(() => dirty.value && content.value.trim().length > 0 && content.value.length <= MAX_LENGTH && !loading.value && !saving.value)
const formattedUpdatedAt = computed(() => metadata.value?.updated_at ? new Date(metadata.value.updated_at).toLocaleString('zh-CN') : '—')

function adopt(rule: AiAgentRule) {
  metadata.value = rule
  content.value = rule.content
  serverContent.value = rule.content
}

async function load() {
  loading.value = true
  message.value = ''
  try {
    adopt(await getAiAgentRule(props.token))
  } catch (error) {
    messageType.value = 'error'
    message.value = `规则加载失败：${error instanceof Error ? error.message : String(error)}`
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!canSave.value) return
  saving.value = true
  message.value = ''
  try {
    const saved = await saveAiAgentRule(props.token, content.value)
    adopt(saved)
    messageType.value = 'ok'
    message.value = '规则已保存并立即生效'
    emit('saved', saved)
  } catch (error) {
    messageType.value = 'error'
    message.value = `保存失败，编辑内容已保留：${error instanceof Error ? error.message : String(error)}`
  } finally {
    saving.value = false
  }
}

function discard() {
  content.value = serverContent.value
  message.value = '已撤销未保存修改'
  messageType.value = 'ok'
}

function beforeUnload(event: BeforeUnloadEvent) {
  if (!dirty.value) return
  event.preventDefault()
  event.returnValue = ''
}

onMounted(() => {
  window.addEventListener('beforeunload', beforeUnload)
  compactQuery.addEventListener('change', onCompactChange)
  syncExpandButton()
  void load()
})
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', beforeUnload)
  compactQuery.removeEventListener('change', onCompactChange)
  expandButton?.removeEventListener('click', toggleEditorFullscreen)
  expandButton?.remove()
})
defineExpose({ isDirty: () => dirty.value })
</script>
