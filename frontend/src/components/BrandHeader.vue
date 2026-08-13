<template>
  <header class="header">
    <div class="header-inner">
      <div class="header-main">
        <h1><span class="red">天枢 TenSpur</span> · {{ currentBrandName }} · {{ pageProductTitle }}</h1>
        <div class="sub">
          企业产品库
          <span class="summary-pill">{{ currentCount }} 款产品 · 实时读取</span>
        </div>
      </div>
      <div class="header-actions">
        <div class="generic-logo text-brand" aria-label="天枢 TenSpur">TS</div>
        <div class="brand-switch" aria-label="品牌切换">
          <el-segmented :model-value="selectedBrand" :options="brandOptions" @update:model-value="updateBrand" />
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">

defineProps<{
  selectedBrand: string
  brandOptions: { label: string; value: string }[]
  currentBrandName: string
  pageProductTitle: string
  currentCount: number
}>()

const emit = defineEmits<{
  'update:selectedBrand': [value: string]
}>()

function updateBrand(value: string | number) {
  emit('update:selectedBrand', String(value))
}
</script>
