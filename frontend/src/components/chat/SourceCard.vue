<template>
  <span class="source-item" @click="$emit('click', source)">
    {{ source.document_name }}
    <span v-if="source.page_number"> - {{ source.page_number }}</span>
    <span class="score">相似度: {{ (source.score * 100).toFixed(0) / 100 }}</span>
  </span>
</template>

<script setup>
defineProps({ source: Object })
defineEmits(['click'])
</script>

<style scoped>
.source-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--color-primary-soft);
  border: 1px solid rgba(14, 165, 233, 0.2);
  border-radius: 999px;
  font-size: 12px;
  color: var(--color-primary);
  cursor: pointer;
  transition: all 0.2s;
}
.source-item:hover {
  background: rgba(14, 165, 233, 0.18);
  box-shadow: 0 0 8px rgba(14, 165, 233, 0.15);
}
.source-item .score {
  color: var(--color-text-subtle);
}
</style>
