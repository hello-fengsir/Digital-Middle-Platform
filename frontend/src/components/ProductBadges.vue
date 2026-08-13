<template>
  <span v-if="items.length" class="product-badges" aria-label="产品状态标签">
    <span v-for="badge in items" :key="`${badge.kind}-${badge.code}`" class="product-badge" :class="`badge-${badge.tone}`">{{ badge.label }}</span>
  </span>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { normalizeProductBadges } from '../utils/productBadges'
const props = defineProps<{ model: { lifecycle_status?: unknown; business_tags?: unknown; badges?: unknown } | null | undefined }>()
const items = computed(() => normalizeProductBadges(props.model))
</script>
