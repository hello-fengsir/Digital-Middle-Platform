<template>
  <section class="editor-panel">
    <div class="panel-head">
      <div>
        <p class="admin-kicker">{{ creating ? 'Create' : 'Detail' }}</p>
        <h2>{{ creating ? '新增型号' : detailModelName || '选择型号' }}</h2>
      </div>
      <div v-if="detailModelName && !creating" class="panel-actions">
        <span v-if="isDeletedDetail" class="status-badge deleted">已下架</span>
        <button type="button" class="danger" :disabled="!hasApiKey" @click="$emit('remove-current')">{{ isDeletedDetail ? '永久删除' : '软删除/下架' }}</button>
      </div>
    </div>

    <form class="basic-form" @submit.prevent="$emit('save-basic')">
      <label>
        <span>品牌代码</span>
        <select v-model="basicForm.brand_code" required>
          <option value="">选择品牌</option>
          <option v-for="brand in brands" :key="brand.code" :value="brand.code">{{ brand.name }} / {{ brand.code }}</option>
        </select>
      </label>
      <label><span>品牌名称</span><input :value="basicForm.brand_name" readonly placeholder="选择品牌后自动显示" /></label>
      <label>
        <span>产品类型</span>
        <select v-model="basicForm.product_type" required>
          <option value="">选择产品类型</option>
          <option v-for="type in productTypeOptions" :key="type.code" :value="type.name">{{ type.name }}</option>
        </select>
      </label>
      <SeriesSelector
        v-model:new-series-name="newSeriesNameProxy"
        :basic-form="basicForm"
        :creating="creating"
        :form-series-loading="formSeriesLoading"
        :form-series-options="formSeriesOptions"
        :selected-form-series="selectedFormSeries"
        :form-series-placeholder="formSeriesPlaceholder"
        :form-series-message="formSeriesMessage"
        :has-api-key="hasApiKey"
        @remove-selected-series="$emit('remove-selected-series')"
      />
      <label><span>型号</span><input v-model.trim="basicForm.model_name" required placeholder="NF5280M7" /></label>
      <label><span>标题</span><input v-model.trim="basicForm.title" placeholder="展示标题" /></label>
      <label><span>平台厂商</span><input v-model.trim="basicForm.platform_vendor" placeholder="Intel / AMD" /></label>
      <label><span>代际</span><input v-model.trim="basicForm.generation" placeholder="G7" /></label>
      <label>
        <span>生命周期（必选）</span>
        <select v-model="basicForm.lifecycle_status" required>
          <option value="" disabled>请选择生命周期</option>
          <option value="npi">新品</option>
          <option value="rts">在售</option>
          <option value="rtq">可报价</option>
          <option value="eos">停止接单</option>
          <option value="eol">停售</option>
        </select>
      </label>
      <label class="business-tag-control">
        <span>业务标签</span>
        <span class="checkbox-line"><input v-model="basicForm.featured" type="checkbox" /> 主推</span>
      </label>
      <div class="form-actions">
        <button type="submit" :disabled="!hasApiKey || savingBasic || isDeletedDetail">{{ creating ? '创建型号' : '保存基础信息' }}</button>
        <span v-if="!hasApiKey" class="hint">请先登录后台</span>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Brand, ProductType, Series } from '../adminApi'
import SeriesSelector from './SeriesSelector.vue'

interface BasicForm {
  brand_code: string
  brand_name: string
  product_type: string
  series: string
  model_name: string
  title: string
  platform_vendor: string
  generation: string
  lifecycle_status: '' | 'npi' | 'rts' | 'rtq' | 'eos' | 'eol'
  featured: boolean
}

const props = defineProps<{
  basicForm: BasicForm
  brands: Brand[]
  productTypeOptions: ProductType[]
  creating: boolean
  detailModelName: string
  isDeletedDetail: boolean
  hasApiKey: boolean
  savingBasic: boolean
  newSeriesName: string
  formSeriesLoading: boolean
  formSeriesOptions: Series[]
  selectedFormSeries: Series | null
  formSeriesPlaceholder: string
  formSeriesMessage: string
}>()

const emit = defineEmits<{
  'update:newSeriesName': [value: string]
  'save-basic': []
  'remove-current': []
  'remove-selected-series': []
}>()

const newSeriesNameProxy = computed({
  get: () => props.newSeriesName,
  set: (value: string) => emit('update:newSeriesName', value),
})
</script>
