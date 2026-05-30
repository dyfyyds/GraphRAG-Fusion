<template>
  <div class="graph-toolbar">
    <div class="left">
      <div class="search-box">
        <svg viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
        <input
          v-model="query"
          type="text"
          placeholder="搜索实体名称..."
          @keyup.enter="$emit('search', query)"
        >
      </div>
      <select
        class="filter-select"
        :value="typeFilter"
        @change="$emit('update:type-filter', $event.target.value)"
      >
        <option value="">全部类型</option>
        <option value="Product">产品</option>
        <option value="Department">部门</option>
        <option value="Person">人物</option>
        <option value="Concept">概念</option>
        <option value="Process">流程</option>
      </select>
    </div>
    <div class="right">
      <button class="btn btn-default" @click="$emit('add-relation')">
        <svg viewBox="0 0 24 24"><path d="M15 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm-9-2V7H4v3H1v2h3v3h2v-3h3v-2H6zm9 4c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
        添加关系
      </button>
      <button class="btn btn-primary" @click="$emit('add-entity')">
        <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
        添加实体
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const query = ref('')

defineProps({
  typeFilter: { type: String, default: '' }
})

defineEmits(['search', 'add-entity', 'add-relation', 'update:type-filter'])
</script>

<style scoped>
.graph-toolbar {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.right {
  display: flex;
  gap: 12px;
}

.search-box {
  display: flex;
  align-items: center;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 0 12px;
  height: 36px;
  background: #fff;
  width: 280px;
  transition: border-color 0.2s;
}

.search-box:focus-within {
  border-color: #667eea;
}

.search-box svg {
  width: 16px;
  height: 16px;
  fill: #c0c4cc;
  margin-right: 8px;
  flex-shrink: 0;
}

.search-box input {
  border: none;
  outline: none;
  flex: 1;
  font-size: 13px;
  color: #303133;
  background: transparent;
}

.search-box input::placeholder {
  color: #c0c4cc;
}

.filter-select {
  height: 36px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 0 12px;
  font-size: 13px;
  color: #606266;
  background: #fff;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}

.filter-select:focus {
  border-color: #667eea;
}

.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
  font-family: inherit;
}

.btn svg {
  width: 16px;
  height: 16px;
  fill: currentColor;
}

.btn-primary {
  background: #667eea;
  color: #fff;
}

.btn-primary:hover {
  background: #5a6fd6;
}

.btn-default {
  background: #fff;
  color: #606266;
  border-color: #dcdfe6;
}

.btn-default:hover {
  border-color: #667eea;
  color: #667eea;
}
</style>
