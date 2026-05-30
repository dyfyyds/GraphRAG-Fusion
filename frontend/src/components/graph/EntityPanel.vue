<template>
  <el-drawer :model-value="true" title="实体详情" @close="$emit('close')">
    <el-descriptions :column="1" border>
      <el-descriptions-item label="名称">{{ entity.name }}</el-descriptions-item>
      <el-descriptions-item label="类型">{{ entity.type }}</el-descriptions-item>
      <el-descriptions-item label="ID">{{ entity.id }}</el-descriptions-item>
    </el-descriptions>
  </el-drawer>
</template>

<script setup>
defineProps({ entity: Object })
defineEmits(['close'])
</script>
