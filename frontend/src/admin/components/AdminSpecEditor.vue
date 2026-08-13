<template>
  <section v-if="creating" class="pending-specs-panel">
    <div class="recognition-preview-head">
      <b>待创建规格参数</b>
      <span class="hint">这些参数会在点击“创建型号”时随新型号一起入库，可继续编辑或删除。</span>
    </div>
    <SpecRows
      :specs-form="specsForm"
      :spec-definition-options-for="specDefinitionOptionsFor"
      :definition-option-key="definitionOptionKey"
      :definition-option-label="definitionOptionLabel"
      :is-legacy-spec-definition="isLegacySpecDefinition"
      :show-advanced="false"
      :display-spec-sort-order="displaySpecSortOrder"
      @definition-change="$emit('definition-change', $event)"
      @remove-spec="$emit('remove-spec', $event)"
    />
  </section>

  <section v-else class="editor-panel specs-panel">
    <div class="panel-head compact">
      <div>
        <p class="admin-kicker">Specifications</p>
        <h2>规格参数</h2>
      </div>
      <div class="panel-actions">
        <button type="button" class="ghost" @click="$emit('add-spec')">新增参数</button>
        <button type="button" :disabled="!hasApiKey || savingSpecs || isDeletedDetail" @click="$emit('save-specs')">保存规格</button>
      </div>
    </div>

    <details v-if="storagePreviewText" class="storage-readonly">
      <summary>storage_sheet_preview 只读预览，保存规格时原样保留</summary>
      <pre>{{ storagePreviewText }}</pre>
    </details>

    <SpecRows
      :specs-form="specsForm"
      :spec-definition-options-for="specDefinitionOptionsFor"
      :definition-option-key="definitionOptionKey"
      :definition-option-label="definitionOptionLabel"
      :is-legacy-spec-definition="isLegacySpecDefinition"
      :show-advanced="true"
      :display-spec-sort-order="displaySpecSortOrder"
      @definition-change="$emit('definition-change', $event)"
      @remove-spec="$emit('remove-spec', $event)"
    />
  </section>
</template>

<script setup lang="ts">
import SpecRows from './SpecRows.vue'
import type { SpecDefinition, SpecInput } from '../adminApi'

type SpecDefinitionOption = SpecDefinition & { is_legacy?: boolean }

defineProps<{
  creating: boolean
  specsForm: SpecInput[]
  storagePreviewText: string
  hasApiKey: boolean
  savingSpecs: boolean
  isDeletedDetail: boolean
  specDefinitionOptionsFor: (spec: SpecInput) => SpecDefinitionOption[]
  definitionOptionKey: (definition: SpecDefinitionOption) => string
  definitionOptionLabel: (definition: SpecDefinitionOption) => string
  isLegacySpecDefinition: (definition: SpecDefinitionOption) => boolean
  displaySpecSortOrder: (spec: SpecInput) => string
}>()

defineEmits<{
  'definition-change': [payload: { spec: SpecInput; event: Event }]
  'remove-spec': [index: number]
  'add-spec': []
  'save-specs': []
}>()
</script>
