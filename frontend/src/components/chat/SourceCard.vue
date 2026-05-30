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
  background: #ecf5ff;
  border-radius: 4px;
  font-size: 12px;
  color: #409eff;
  cursor: pointer;
  transition: background 0.2s;
}
.source-item:hover {
  background: #d9ecff;
}
.source-item .score {
  color: #909399;
}
</style>
