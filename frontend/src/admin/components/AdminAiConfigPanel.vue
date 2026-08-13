<template>
  <section class="editor-panel ai-config-panel">
    <div class="panel-head compact">
      <div>
        <p class="admin-kicker">OpenAI Compatible</p>
        <h2>OpenAI Compatible 模型配置</h2>
      </div>
      <span class="status-badge" :class="form.enabled ? 'active' : 'deleted'">{{ form.enabled ? '已启用' : '未启用' }}</span>
    </div>
    <form class="basic-form" @submit.prevent="$emit('save')">
      <label><span>API Base URL</span><input v-model.trim="form.base_url" placeholder="https://example.com" /></label>
      <label><span>API Key</span><input v-model.trim="form.api_key" type="password" :placeholder="hasApiKey ? '已保存 Key；留空表示不更新' : '请输入 API Key'" autocomplete="new-password" /></label>
      <p class="ai-config-hint">适用于 OpenAI Compatible 接口。测试连接会优先使用当前输入；Key 留空时使用已保存的 Key，且不会回显到浏览器。</p>
      <label><span>模型名称</span><input v-model.trim="form.model" placeholder="请输入兼容接口提供的模型名称" /></label>
      <label><span>Temperature</span><input v-model.number="form.temperature" type="number" min="0" max="2" step="0.1" /></label>
      <label><span>Max Tokens</span><input v-model.number="form.max_tokens" type="number" min="128" max="8000" step="128" /></label>
      <label class="toggle-row"><span>启用 AI 功能</span><input v-model="form.enabled" type="checkbox" /></label>
      <div class="form-actions">
        <button type="submit" :disabled="busy || deleting">{{ busy ? '保存中' : '保存 AI 配置' }}</button>
        <button type="button" class="ghost" :disabled="testing || deleting" @click="$emit('test')">{{ testing ? '测试中' : '测试连接' }}</button>
        <span class="hint">Key 不回显，前端不直接调用供应商。</span>
      </div>
      <div class="ai-key-danger-zone">
        <div>
          <b>模型 Key</b>
          <p v-if="hasApiKey">当前已保存模型 Key，可单独删除。</p>
          <p v-else class="ai-key-empty" role="status">当前未保存模型Key</p>
        </div>
        <button v-if="hasApiKey" type="button" class="danger" :disabled="deleting || busy || testing" @click="confirmDelete">
          {{ deleting ? '删除中' : '删除当前 Key' }}
        </button>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
import type { AiConfigPayload } from '../adminApi'

defineProps<{
  form: AiConfigPayload
  hasApiKey: boolean
  busy?: boolean
  testing?: boolean
  deleting?: boolean
}>()

const emit = defineEmits<{
  save: []
  test: []
  deleteKey: []
}>()

function confirmDelete() {
  const confirmed = window.confirm('确认删除当前模型 Key？此操作仅删除 Key，Base URL、模型和参数将保留，AI 功能会自动停用。')
  if (confirmed) emit('deleteKey')
}
</script>
