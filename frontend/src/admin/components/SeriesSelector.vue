<template>
  <label>
    <span>系列</span>
    <select v-model="basicForm.series" :required="seriesSelectRequired" :disabled="disabled">
      <option value="">{{ formSeriesPlaceholder }}</option>
      <option v-for="series in formSeriesOptions" :key="series.id" :value="series.name">{{ series.name }}</option>
    </select>
    <div v-if="selectedFormSeries" class="inline-actions series-actions">
      <button
        type="button"
        class="ghost mini"
        :disabled="!hasApiKey || selectedFormSeries.model_count > 0"
        @click="$emit('remove-selected-series')"
      >删除空系列</button>
      <small class="hint">{{ selectedFormSeries.model_count > 0 ? `该系列下有 ${selectedFormSeries.model_count } 个在架型号，不能删除` : '该系列暂无在架型号，可删除' }}</small>
    </div>
    <input
      v-if="creating"
      v-model.trim="newSeriesNameProxy"
      :disabled="!basicForm.brand_code || !basicForm.product_type || formSeriesLoading"
      placeholder="如需新增系列，在这里输入新系列名；填写后优先生效"
    />
    <small v-if="formSeriesMessage" class="hint">{{ formSeriesMessage }}</small>
  </label>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Series } from '../adminApi'

interface BasicForm {
  brand_code: string
  product_type: string
  series: string
}

const props = defineProps<{
  basicForm: BasicForm
  newSeriesName: string
  creating: boolean
  formSeriesLoading: boolean
  formSeriesOptions: Series[]
  selectedFormSeries: Series | null
  formSeriesPlaceholder: string
  formSeriesMessage: string
  hasApiKey: boolean
}>()

const emit = defineEmits<{
  'update:newSeriesName': [value: string]
  'remove-selected-series': []
}>()

const disabled = computed(() =>
  !props.basicForm.brand_code
  || !props.basicForm.product_type
  || props.formSeriesLoading
  || (!props.creating && props.formSeriesOptions.length === 0)
)

const seriesSelectRequired = computed(() => !props.creating || !props.newSeriesName.trim())

const newSeriesNameProxy = computed({
  get: () => props.newSeriesName,
  set: (value: string) => emit('update:newSeriesName', value),
})
</script>
