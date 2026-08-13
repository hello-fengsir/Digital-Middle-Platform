<template>
  <section v-if="visible" class="recognition-panel" aria-label="型号参数文本识别录入">
    <div class="recognition-head">
      <div>
        <h3>参数文本识别录入</h3>
        <p>{{ creating ? 'AI/规则识别仅做录入辅助，需人工确认；应用后只写入新型号待创建规格表单，点击“创建型号”时随新型号一起提交数据库。' : 'AI/规则识别仅做录入辅助，需人工确认；应用后写入当前型号规格表单，确认后点击“保存规格”更新数据库。' }}</p>
      </div>
      <button type="button" class="ghost" :disabled="recognizingSpecs || !recognitionText.trim() || isDeletedDetail" @click="$emit('recognize')">{{ recognizingSpecs ? '识别中...' : '识别参数' }}</button>
    </div>
    <textarea :value="recognitionText" rows="7" placeholder="粘贴服务器参数、官网技术规格、白皮书片段或表格复制文本。支持“参数名：值”“参数名 值”等格式。" @input="updateRecognitionText"></textarea>
    <div v-if="recognitionMessage" class="hint">{{ recognitionMessage }}</div>
    <div v-if="recognizedSpecs.length" class="recognition-preview">
      <div class="recognition-preview-head">
        <b>识别预览</b>
        <button type="button" :disabled="!recognizedSpecs.some((row) => row.include)" @click="$emit('apply')">{{ creating ? '应用到新型号规格' : '应用到当前型号规格' }}</button>
      </div>
      <div class="recognition-table">
        <div class="recognition-row recognition-row-head">
          <span>入库</span><span>参数项</span><span>识别值</span><span>匹配字段</span><span>置信度/备注</span>
        </div>
        <div v-for="(row, index) in recognizedSpecs" :key="`${row.raw_label}-${index}`" class="recognition-row">
          <label class="recognition-check" data-label="入库"><input v-model="row.include" type="checkbox" /><span>纳入本次应用</span></label>
          <span class="recognition-label" data-label="参数项">{{ row.raw_label }}</span>
          <label class="recognition-value" data-label="识别值"><span class="recognition-mobile-label">识别值</span><textarea v-model="row.value" rows="2"></textarea></label>
          <label class="recognition-field" data-label="匹配字段"><span class="recognition-mobile-label">匹配字段</span><select v-model="row.field_key" @change="$emit('recognized-field-change', row)">
            <option value="">未匹配，需人工选择字段</option>
            <option v-for="definition in sortedSpecDefinitions" :key="definition.field_key" :value="definition.field_key">
              {{ definitionOptionLabel(definition) }}
            </option>
          </select></label>
          <span class="recognition-note" data-label="置信度/备注">{{ row.confidence }} / {{ row.remark }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { SpecDefinition } from '../adminApi'

export interface RecognizedSpecRow {
  raw_label: string
  value: string
  field_key: string
  confidence: string
  remark: string
  include: boolean
}

defineProps<{
  visible: boolean
  creating: boolean
  isDeletedDetail: boolean
  recognizingSpecs: boolean
  recognitionText: string
  recognitionMessage: string
  recognizedSpecs: RecognizedSpecRow[]
  sortedSpecDefinitions: SpecDefinition[]
  definitionOptionLabel: (definition: SpecDefinition) => string
}>()

const emit = defineEmits<{
  'update:recognitionText': [value: string]
  recognize: []
  apply: []
  'recognized-field-change': [row: RecognizedSpecRow]
}>()

function updateRecognitionText(event: Event) {
  emit('update:recognitionText', (event.target as HTMLTextAreaElement).value)
}
</script>
