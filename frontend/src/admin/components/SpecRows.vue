<template>
  <div class="spec-table-editor" :class="{ 'create-spec-preview': !showAdvanced }">
    <div class="spec-head-row">
      <span>参数项</span><span>值</span>
    </div>
    <div v-for="(spec, index) in specsForm" :key="`${spec.field_key}-${index}`" class="spec-edit-row">
      <div class="spec-field-editor">
        <select class="spec-definition-select" :value="spec.field_key" @change="$emit('definition-change', { spec, event: $event })">
          <option value="">选择参数项</option>
          <option
            v-for="definition in specDefinitionOptionsFor(spec)"
            :key="definitionOptionKey(definition)"
            :value="definition.field_key"
            :disabled="isLegacySpecDefinition(definition)"
          >
            {{ definitionOptionLabel(definition) }}
          </option>
        </select>
        <details v-if="showAdvanced" class="spec-advanced">
          <summary>高级信息</summary>
          <div class="spec-bound-grid">
            <label><span>字段分类</span><input :value="spec.group || '未绑定'" readonly /></label>
            <label><span>字段标签</span><input :value="spec.label || '未绑定'" readonly /></label>
            <label><span>字段名</span><input :value="spec.field_key || '未绑定'" readonly /></label>
            <label><span>分类内排序</span><input :value="displaySpecSortOrder(spec)" readonly /></label>
          </div>
        </details>
        <button type="button" class="icon-danger spec-delete-btn" title="删除此参数" @click="$emit('remove-spec', index)">×</button>
      </div>
      <textarea v-model="spec.value" rows="3" placeholder="规格值"></textarea>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SpecDefinition, SpecInput } from '../adminApi'

type SpecDefinitionOption = SpecDefinition & { is_legacy?: boolean }

defineProps<{
  specsForm: SpecInput[]
  showAdvanced: boolean
  specDefinitionOptionsFor: (spec: SpecInput) => SpecDefinitionOption[]
  definitionOptionKey: (definition: SpecDefinitionOption) => string
  definitionOptionLabel: (definition: SpecDefinitionOption) => string
  isLegacySpecDefinition: (definition: SpecDefinitionOption) => boolean
  displaySpecSortOrder: (spec: SpecInput) => string
}>()

defineEmits<{
  'definition-change': [payload: { spec: SpecInput; event: Event }]
  'remove-spec': [index: number]
}>()
</script>
