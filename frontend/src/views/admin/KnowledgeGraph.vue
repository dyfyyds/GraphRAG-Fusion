<template>
  <div class="knowledge-graph-page">
    <button class="cosmos-exit" title="退出全屏图谱" @click="exitGraph">
      <svg viewBox="0 0 24 24"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.42-1.41L7.83 13H20v-2z"/></svg>
      <span>退出</span>
    </button>

    <!-- Toolbar -->
    <GraphToolbar
      v-model:type-filter="typeFilter"
      :entity-types="dynamicEntityTypes"
      @search="handleSearch"
      @add-entity="openCreateEntity"
      @add-relation="openCreateRelation"
      @import="openImport"
    />

    <div class="graph-layout">
      <!-- Main graph area -->
      <div class="graph-canvas">
        <!-- Floating stats overlay -->
        <div class="graph-stats">
          <div class="graph-stat">
            <div class="num">{{ filteredEntityCount.toLocaleString() }}</div>
            <div class="label">显示实体</div>
          </div>
          <div class="graph-stat">
            <div class="num">{{ filteredRelationCount.toLocaleString() }}</div>
            <div class="label">显示关系</div>
          </div>
          <div class="graph-stat">
            <div class="num">{{ entityCount.toLocaleString() }}</div>
            <div class="label">实体总数</div>
          </div>
          <div class="graph-stat">
            <div class="num">{{ typeCount }}</div>
            <div class="label">实体类型</div>
          </div>
        </div>

        <SemanticCosmos
          ref="semanticCosmosRef"
          :entities="graphFilteredEntities"
          :relations="graphFilteredRelations"
          :selected-entity="selectedEntity"
          @select="selectEntity"
        />

        <!-- Filter Panel: Entity Types & Relation Types -->
        <div class="graph-filter-panel" v-if="allEntityTypes.length > 0 || allRelationTypes.length > 0">
          <!-- Entity Types -->
          <div class="filter-section">
            <div class="filter-section-header">
              <span class="filter-section-title">实体类型 <span class="filter-count">{{ allEntityTypes.length }}</span></span>
            </div>
            <div class="filter-chips">
              <button
                v-for="t in allEntityTypes"
                :key="t.type"
                class="filter-chip entity-chip"
                :class="{ active: activeEntityTypes.size === 0 || activeEntityTypes.has(t.type) }"
                @click="toggleEntityType(t.type)"
              >
                <span class="chip-label">{{ t.type }}</span>
                <span class="chip-count">{{ t.count }}</span>
              </button>
            </div>
          </div>

          <!-- Relation Types -->
          <div class="filter-section" v-if="allRelationTypes.length > 0">
            <div class="filter-section-header">
              <span class="filter-section-title">关系类型 <span class="filter-count">{{ allRelationTypes.length }}</span></span>
            </div>
            <div class="filter-chips">
              <button
                v-for="r in allRelationTypes.slice(0, 20)"
                :key="r.type"
                class="filter-chip rel-chip"
                :class="{ active: activeRelationTypes.size === 0 || activeRelationTypes.has(r.type) }"
                @click="toggleRelationType(r.type)"
              >
                <span class="chip-label">{{ r.type }}</span>
                <span class="chip-count">{{ r.count }}</span>
              </button>
            </div>
          </div>
        </div>

        <div class="graph-controls">
          <div class="graph-control" @click="zoomIn" title="放大">
            <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
          </div>
          <div class="graph-control" @click="zoomOut" title="缩小">
            <svg viewBox="0 0 24 24"><path d="M19 13H5v-2h14v2z"/></svg>
          </div>
          <div class="graph-control" @click="resetZoom" title="重置缩放">
            <svg viewBox="0 0 24 24"><path d="M12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm8.94 3c-.46-4.17-3.77-7.48-7.94-7.94V1h-2v2.06C6.83 3.52 3.52 6.83 3.06 11H1v2h2.06c.46 4.17 3.77 7.48 7.94 7.94V23h2v-2.06c4.17-.46 7.48-3.77 7.94-7.94H23v-2h-2.06zM12 19c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/></svg>
          </div>
          <div class="graph-control" @click="fitToView" title="适应视图">
            <svg viewBox="0 0 24 24"><path d="M15 3l2.3 2.3-2.89 2.87 1.42 1.42L18.7 6.7 21 9V3h-6zM3 9l2.3-2.3 2.87 2.89 1.42-1.42L6.7 5.3 9 3H3v6zm6 12l-2.3-2.3 2.89-2.87-1.42-1.42L5.3 17.3 3 15v6h6zm12-6l-2.3 2.3-2.87-2.89-1.42 1.42 2.89 2.87L15 21h6v-6z"/></svg>
          </div>
        </div>
      </div>

      <!-- Right panel -->
      <button
        class="panel-toggle"
        :class="{ collapsed: rightPanelCollapsed }"
        :title="rightPanelCollapsed ? '展开侧栏' : '收起侧栏'"
        @click="toggleRightPanel"
      >
        <svg viewBox="0 0 24 24">
          <path :d="rightPanelCollapsed ? 'M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z' : 'M14 6l1.41 1.41L10.83 12l4.58 4.59L14 18l-6-6z'"/>
        </svg>
      </button>

      <div class="right-panel" :class="{ collapsed: rightPanelCollapsed }">
        <!-- Entity list card -->
        <div class="panel-card">
          <div class="panel-header">
            <h3>实体列表</h3>
            <span class="panel-count">{{ filteredEntityList.length.toLocaleString() }} / {{ entityCount.toLocaleString() }}</span>
          </div>
          <div class="panel-search">
            <svg viewBox="0 0 24 24"><path d="M9.5 3a6.5 6.5 0 0 1 5.2 10.4l4.45 4.45-1.41 1.41-4.45-4.45A6.5 6.5 0 1 1 9.5 3Zm0 2a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9Z"/></svg>
            <input v-model="entityListQuery" type="text" placeholder="搜索实体名称、类型或描述">
          </div>
          <div class="panel-body">
            <ul class="entity-list">
              <li
                v-for="entity in filteredEntityList"
                :key="entity.id"
                class="entity-item"
                :class="{ active: selectedEntity?.id === entity.id }"
                @click="selectEntity(entity)"
              >
                <div class="entity-icon" :class="getTypeClass(entity.entity_type)">
                  {{ getTypeLabel(entity.entity_type) }}
                </div>
                <div class="entity-info">
                  <div class="name">{{ entity.name }}</div>
                  <div class="type">类型: {{ getTypeName(entity.entity_type) }}</div>
                  <div class="relations">{{ getEntityRelationCount(entity.id) }} 个关系</div>
                </div>
                <div class="item-actions">
                  <button class="btn-icon btn-edit" @click.stop="openEditEntity(entity)" title="修改实体">
                    <svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zm19.71-11.04a1 1 0 0 0 0-1.41l-2.5-2.5a1 1 0 0 0-1.41 0l-1.96 1.96 3.75 3.75 2-1.8z"/></svg>
                  </button>
                  <button class="btn-icon btn-delete" @click.stop="deleteEntity(entity)" title="删除实体">
                    <svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                  </button>
                </div>
              </li>
              <li v-if="filteredEntityList.length === 0" class="relation-empty">暂无匹配实体</li>
            </ul>
          </div>
        </div>

        <!-- Relation list card -->
        <div class="panel-card">
          <div class="panel-header">
            <h3>关系列表</h3>
            <span class="panel-count">{{ filteredRelationList.length.toLocaleString() }} 个</span>
          </div>
          <div class="panel-search">
            <svg viewBox="0 0 24 24"><path d="M9.5 3a6.5 6.5 0 0 1 5.2 10.4l4.45 4.45-1.41 1.41-4.45-4.45A6.5 6.5 0 1 1 9.5 3Zm0 2a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9Z"/></svg>
            <input v-model="relationListQuery" type="text" placeholder="搜索起点、终点、关系类型">
          </div>
          <div class="panel-body">
            <ul class="relation-list">
              <li v-for="(rel, idx) in filteredRelationList" :key="relationKey(rel, idx)" class="relation-item">
                <span class="rel-name">{{ getEntityName(rel.source) }}</span>
                <span class="relation-arrow">→</span>
                <span class="relation-label">{{ rel.relation_type }}</span>
                <span class="relation-arrow">→</span>
                <span class="rel-name">{{ getEntityName(rel.target) }}</span>
                <div class="item-actions relation-actions">
                  <button class="btn-icon btn-edit-sm" @click.stop="openEditRelation(rel)" title="修改关系">
                    <svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zm19.71-11.04a1 1 0 0 0 0-1.41l-2.5-2.5a1 1 0 0 0-1.41 0l-1.96 1.96 3.75 3.75 2-1.8z"/></svg>
                  </button>
                  <button class="btn-icon btn-delete-sm" @click.stop="deleteRelation(rel)" title="删除关系">
                    <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                  </button>
                </div>
              </li>
              <li v-if="filteredRelationList.length === 0" class="relation-empty">暂无匹配关系</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Entity Modal -->
    <div v-if="showAddEntity" class="modal-overlay" @click.self="closeEntityModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingEntityId ? '修改实体' : '添加实体' }}</h3>
          <svg class="modal-close" viewBox="0 0 24 24" @click="closeEntityModal">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
          </svg>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>实体名称 <span class="required">*</span></label>
            <input v-model="newEntity.name" class="form-input" type="text" placeholder="请输入实体名称">
          </div>
          <div class="form-group">
            <label>实体类型 <span class="required">*</span></label>
            <input v-model="newEntity.entity_type" class="form-input" list="entity-type-options" type="text" placeholder="请输入或选择实体类型">
            <datalist id="entity-type-options">
              <option v-for="t in dynamicEntityTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
              <option value="概念">概念</option>
            </datalist>
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea v-model="newEntity.description" class="form-textarea" placeholder="请输入实体描述"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-default" @click="closeEntityModal">取消</button>
          <button class="btn btn-primary" @click="submitEntity">{{ editingEntityId ? '保存修改' : '确定添加' }}</button>
        </div>
      </div>
    </div>

    <!-- Relation Modal -->
    <div v-if="showAddRelation" class="modal-overlay" @click.self="closeRelationModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingRelationOriginal ? '修改关系' : '添加关系' }}</h3>
          <svg class="modal-close" viewBox="0 0 24 24" @click="closeRelationModal">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
          </svg>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>起始实体 <span class="required">*</span></label>
            <input v-model="newRelation.source" class="form-input" list="relation-entity-options" type="text" placeholder="请输入或选择起始实体">
            <datalist id="relation-entity-options">
              <option v-for="e in entities" :key="e.id" :value="e.name">{{ e.name }}</option>
            </datalist>
          </div>
          <div class="form-group">
            <label>关系类型 <span class="required">*</span></label>
            <input v-model="newRelation.relation_type" class="form-input" list="relation-type-options" type="text" placeholder="请输入或选择关系类型">
            <datalist id="relation-type-options">
              <option v-for="t in allRelationTypes" :key="t.type" :value="t.type">{{ t.type }} ({{ t.count }})</option>
              <option value="关联">关联</option>
            </datalist>
          </div>
          <div class="form-group">
            <label>目标实体 <span class="required">*</span></label>
            <input v-model="newRelation.target" class="form-input" list="relation-entity-options" type="text" placeholder="请输入或选择目标实体">
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea v-model="newRelation.description" class="form-textarea" placeholder="请输入关系描述"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-default" @click="closeRelationModal">取消</button>
          <button class="btn btn-primary" @click="submitRelation">{{ editingRelationOriginal ? '保存修改' : '确定添加' }}</button>
        </div>
      </div>
    </div>

    <!-- Import Modal -->
    <div v-if="showImportModal" class="modal-overlay" @click.self="closeImportModal">
      <div class="modal">
        <div class="modal-header">
          <h3>导入实体与关系</h3>
          <svg class="modal-close" viewBox="0 0 24 24" @click="closeImportModal">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
          </svg>
        </div>
        <div class="modal-body">
          <div
            style="border:2px dashed rgba(125,211,252,0.35);border-radius:10px;padding:28px;text-align:center;cursor:pointer;color:#93c5fd;transition:border-color .2s;"
            @click="importInputRef?.click()"
          >
            <svg viewBox="0 0 24 24" style="width:40px;height:40px;fill:#7dd3fc;"><path d="M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z"/></svg>
            <p style="margin-top:10px;color:#dbeafe;">{{ importFile ? importFile.name : '点击选择文件（JSON / TXT / Word）' }}</p>
          </div>
          <input ref="importInputRef" type="file" accept=".json,.txt,.md,.docx,.doc" style="display:none" @change="handleImportFileChange">
          <div style="margin-top:14px;font-size:12px;color:#94a3b8;line-height:1.8;">
            <p style="margin:0 0 4px;"><strong style="color:#cbd5e1;">支持格式（自动识别）</strong></p>
            <p style="margin:0;">· JSON：{ "entities": [...], "relations": [...] }</p>
            <p style="margin:0;">· TXT：每行一个三元组 &nbsp;源实体 | 关系 | 目标实体 | 描述</p>
            <p style="margin:0;">· Word：含「源 / 关系 / 目标」三列的表格</p>
            <p style="margin:0;">· 非结构化正文将自动调用大模型抽取实体关系</p>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-default" @click="closeImportModal">取消</button>
          <button class="btn btn-primary" :disabled="!importFile || importing" @click="submitImport">
            {{ importing ? '导入中…' : '开始导入' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, provide } from 'vue'
import { ElMessage } from 'element-plus'
import * as d3 from 'd3'
import { useRouter } from 'vue-router'
import GraphToolbar from '../../components/graph/GraphToolbar.vue'
import SemanticCosmos from '../../components/graph/SemanticCosmos.vue'
import request from '../../api/request'
import { on } from '../../utils/eventBus'

const graphRef = ref()
const semanticCosmosRef = ref()
const router = useRouter()
const selectedEntity = ref(null)
const typeFilter = ref('')
const entities = ref([])
const relations = ref([])
const showAddEntity = ref(false)
const showAddRelation = ref(false)
const loading = ref(false)
const rightPanelCollapsed = ref(false)
const editingEntityId = ref('')
const editingRelationOriginal = ref(null)
const entityListQuery = ref('')
const relationListQuery = ref('')

// --- Entity Type & Relation Type Filter State ---
const activeEntityTypes = ref(new Set())
const activeRelationTypes = ref(new Set())

const TYPE_TO_GALAXY = {
  // English types
  Product: 'Knowledge', Department: 'Society', Person: 'Self',
  Concept: 'Abstract', Process: 'Creation', Document: 'Knowledge',
  Policy: 'Society', Rule: 'Society', Event: 'Emotion',
  // Chinese types from LLM extraction
  '法规': 'Knowledge', '文件': 'Knowledge', '条款': 'Abstract',
  '章节': 'Abstract', '附件': 'Knowledge', '主体': 'Society',
  '机构': 'Society', '职责': 'Society', '条件': 'Abstract',
  '材料': 'Creation', '资质': 'Self', '资格': 'Self',
  '能力': 'Self', '行为': 'Emotion', '流程': 'Creation',
  '标准': 'Knowledge', '范围': 'Abstract', '例外': 'Emotion',
  '禁止': 'Emotion', '期限': 'Nature', '金额': 'Nature',
  '比例': 'Nature', '项目': 'Creation', '服务': 'Creation',
  '系统': 'Knowledge', '凭证': 'Knowledge', '责任': 'Society',
  '财务事项': 'Nature', '概念': 'Abstract', '规则': 'Society',
}

const GALAXY_NAMES = {
  Society: '社会', Self: '自我', Nature: '自然', Emotion: '情绪',
  Abstract: '抽象', Knowledge: '知识', Art: '艺术', Creation: '创造',
}

function galaxyForType(entityType) {
  if (TYPE_TO_GALAXY[entityType]) return TYPE_TO_GALAXY[entityType]
  const keys = Object.keys(GALAXY_NAMES)
  let h = 2166136261
  const text = String(entityType || 'default')
  for (let i = 0; i < text.length; i++) { h ^= text.charCodeAt(i); h = Math.imul(h, 16777619) }
  return keys[Math.abs(h >>> 0) % keys.length]
}

// Compute all unique entity types and relation types from loaded data
const allEntityTypes = computed(() => {
  const map = new Map()
  for (const e of entities.value) {
    if (!e.entity_type) continue
    if (!map.has(e.entity_type)) map.set(e.entity_type, { type: e.entity_type, count: 0 })
    map.get(e.entity_type).count++
  }
  return [...map.values()].sort((a, b) => b.count - a.count)
})

const allRelationTypes = computed(() => {
  const map = new Map()
  for (const r of relations.value) {
    const t = r.relation_type || '关联'
    if (!map.has(t)) map.set(t, { type: t, count: 0 })
    map.get(t).count++
  }
  return [...map.values()].sort((a, b) => b.count - a.count)
})

// Filtered data for the 3D graph visualization
const graphFilteredEntities = computed(() => {
  if (activeEntityTypes.value.size === 0) return entities.value
  return entities.value.filter(e => activeEntityTypes.value.has(e.entity_type))
})

const graphFilteredRelations = computed(() => {
  const entityNames = new Set(graphFilteredEntities.value.map(e => e.name).filter(Boolean))
  return relations.value.filter(r => {
    // Both endpoints must be visible
    if (!entityNames.has(r.source) || !entityNames.has(r.target)) return false
    // Relation type must be active
    const relType = r.relation_type || '关联'
    if (activeRelationTypes.value.size > 0 && !activeRelationTypes.value.has(relType)) return false
    return true
  })
})

function toggleEntityType(type) {
  const s = new Set(activeEntityTypes.value)
  if (s.has(type)) s.delete(type)
  else s.add(type)
  activeEntityTypes.value = s
}

function toggleRelationType(relType) {
  const s = new Set(activeRelationTypes.value)
  if (s.has(relType)) s.delete(relType)
  else s.add(relType)
  activeRelationTypes.value = s
}

// Provide filter state to child components
provide('activeEntityTypes', activeEntityTypes)
provide('activeRelationTypes', activeRelationTypes)
provide('toggleEntityType', toggleEntityType)
provide('toggleRelationType', toggleRelationType)
provide('allEntityTypes', allEntityTypes)
provide('allRelationTypes', allRelationTypes)

let simulation = null
let svg = null
let zoomBehavior = null
let renderTimer = null
let loadRequestId = 0
let highlightedNode = null

const newEntity = ref({ name: '', entity_type: '概念', description: '' })
const newRelation = ref({ source: '', target: '', relation_type: '关联', description: '' })

const TYPE_PALETTE = ['#7dd3fc', '#f0abfc', '#bef264', '#fde68a', '#c4b5fd', '#5eead4', '#fb7185', '#93c5fd', '#86efac', '#f9a8d4', '#ddd6fe', '#67e8f9', '#facc15', '#a78bfa', '#38bdf8', '#f87171']

const TYPE_COLORS = {}
const TYPE_NAMES = {}
const TYPE_LABELS = {}

function assignTypeStyles() {
  const types = [...new Set(entities.value.map(e => e.entity_type).filter(Boolean))]
  types.forEach((t, i) => {
    TYPE_COLORS[t] = TYPE_PALETTE[i % TYPE_PALETTE.length]
    TYPE_NAMES[t] = t
    TYPE_LABELS[t] = t[0]
  })
}

function typeDomId(type) {
  return String(type || 'default').replace(/[^\w-]/g, '_')
}

const entityCount = computed(() => entities.value.length)
const relationCount = computed(() => relations.value.length)
const filteredEntityCount = computed(() => graphFilteredEntities.value.length)
const filteredRelationCount = computed(() => graphFilteredRelations.value.length)

const dynamicEntityTypes = computed(() => {
  return allEntityTypes.value.map(t => ({
    value: t.type,
    label: t.type,
    count: t.count
  }))
})

const typeCount = computed(() => {
  const types = new Set(entities.value.map(e => e.entity_type))
  return types.size
})

const filteredRelations = computed(() => {
  if (!selectedEntity.value) return relations.value
  const name = selectedEntity.value.name
  const id = selectedEntity.value.id
  return relations.value.filter(r => r.source === name || r.target === name || r.source_id === id || r.target_id === id)
})

const filteredEntityList = computed(() => {
  const query = normalizeListQuery(entityListQuery.value)
  if (!query) return entities.value
  return entities.value.filter(e => {
    return [
      e.name,
      e.entity_type,
      e.description,
    ].some(value => normalizeListQuery(value).includes(query))
  })
})

const filteredRelationList = computed(() => {
  const query = normalizeListQuery(relationListQuery.value)
  const list = filteredRelations.value
  if (!query) return list
  return list.filter(r => {
    return [
      r.source,
      r.target,
      r.relation_type,
      r.description,
    ].some(value => normalizeListQuery(value).includes(query))
  })
})

// 预计算 名称→关系数 / 名称→实体，避免列表里逐项 O(n) 查找造成 O(n²) 卡顿
const relationCountByName = computed(() => {
  const m = Object.create(null)
  for (const r of relations.value) {
    m[r.source] = (m[r.source] || 0) + 1
    m[r.target] = (m[r.target] || 0) + 1
  }
  return m
})
const entityById = computed(() => {
  const m = Object.create(null)
  for (const e of entities.value) m[e.id] = e
  return m
})
const entityByName = computed(() => {
  const m = Object.create(null)
  for (const e of entities.value) m[e.name] = e
  return m
})

function getTypeClass(type) {
  // Return CSS-safe class based on color index
  if (!type) return 'type-concept'
  const idx = Object.keys(TYPE_COLORS).indexOf(type)
  const classList = ['type-c0', 'type-c1', 'type-c2', 'type-c3', 'type-c4', 'type-c5',
    'type-c6', 'type-c7', 'type-c8', 'type-c9', 'type-c10', 'type-c11', 'type-c12', 'type-c13', 'type-c14', 'type-c15']
  return classList[idx] || 'type-c0'
}

function getTypeLabel(type) {
  return TYPE_LABELS[type] || (type ? type[0] : '?')
}

function getTypeName(type) {
  return TYPE_NAMES[type] || type || 'Unknown'
}

function getEntityName(idOrName) {
  // Relations now use entity names directly, so just return as-is if it's a name
  const e = entityById.value[idOrName] || entityByName.value[idOrName]
  return e ? e.name : idOrName
}

function getEntityRelationCount(entityId) {
  const entity = entityById.value[entityId]
  if (!entity) return 0
  return relationCountByName.value[entity.name] || 0
}

function normalizeListQuery(value) {
  return String(value || '').trim().toLowerCase()
}

function relationKey(rel, idx = '') {
  return `${rel.source || ''}::${rel.relation_type || ''}::${rel.target || ''}::${idx}`
}

function createDefaultEntityForm() {
  return {
    name: '',
    entity_type: dynamicEntityTypes.value[0]?.value || '概念',
    description: '',
  }
}

function createDefaultRelationForm() {
  const firstEntity = selectedEntity.value || entities.value[0] || null
  const fallbackTarget = entities.value.find(e => e.name !== firstEntity?.name) || firstEntity
  return {
    source: firstEntity?.name || '',
    target: fallbackTarget?.name || '',
    relation_type: allRelationTypes.value[0]?.type || '关联',
    description: '',
  }
}

function openCreateEntity() {
  editingEntityId.value = ''
  newEntity.value = createDefaultEntityForm()
  showAddEntity.value = true
}

function openEditEntity(entity) {
  editingEntityId.value = entity.id
  newEntity.value = {
    name: entity.name || '',
    entity_type: entity.entity_type || '概念',
    description: entity.description || '',
  }
  showAddEntity.value = true
}

function closeEntityModal() {
  showAddEntity.value = false
  editingEntityId.value = ''
  newEntity.value = createDefaultEntityForm()
}

function openCreateRelation() {
  editingRelationOriginal.value = null
  newRelation.value = createDefaultRelationForm()
  showAddRelation.value = true
}

function openEditRelation(rel) {
  editingRelationOriginal.value = {
    source: rel.source,
    target: rel.target,
    relation_type: rel.relation_type,
  }
  newRelation.value = {
    source: rel.source || '',
    target: rel.target || '',
    relation_type: rel.relation_type || '关联',
    description: rel.description || '',
  }
  showAddRelation.value = true
}

function closeRelationModal() {
  showAddRelation.value = false
  editingRelationOriginal.value = null
  newRelation.value = createDefaultRelationForm()
}

// --- Import entities/relations from file ---
const showImportModal = ref(false)
const importFile = ref(null)
const importing = ref(false)
const importInputRef = ref(null)

function openImport() {
  importFile.value = null
  showImportModal.value = true
}

function closeImportModal() {
  showImportModal.value = false
  importFile.value = null
  importing.value = false
}

function handleImportFileChange(e) {
  const file = e.target.files?.[0]
  if (file) importFile.value = file
  e.target.value = ''
}

async function submitImport() {
  if (!importFile.value || importing.value) return
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', importFile.value)
    const res = await request.post('/graph/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    if (res && res.success === false) {
      ElMessage.error(res.message || '导入失败')
      return
    }
    const modeLabel = { json: 'JSON', txt: '三元组', 'docx-table': 'Word 表格', llm: '大模型抽取' }[res?.mode] || ''
    ElMessage.success((res?.message || '导入完成') + (modeLabel ? `（${modeLabel}）` : ''))
    closeImportModal()
    await loadGraph()
  } catch (err) {
    ElMessage.error('导入失败: ' + (err?.response?.data?.message || err?.response?.data?.detail || err.message || '网络错误'))
  } finally {
    importing.value = false
  }
}

async function loadGraph(query = '') {
  const requestId = ++loadRequestId
  loading.value = true
  try {
    const [entRes, relRes] = await Promise.all([
      request.get('/graph/entities', { params: { q: query || undefined, limit: 0, entity_type: typeFilter.value || undefined } }),
      request.get('/graph/relations', { params: { limit: 0 } }),
    ])
    if (requestId !== loadRequestId) return
    entities.value = Array.isArray(entRes) ? entRes : (entRes.data || [])
    relations.value = Array.isArray(relRes) ? relRes : (relRes.data || [])
    assignTypeStyles()
    // Initialize filter state: all entity types and relation types active by default
    if (activeEntityTypes.value.size === 0) {
      activeEntityTypes.value = new Set(entities.value.map(e => e.entity_type).filter(Boolean))
    }
    if (activeRelationTypes.value.size === 0) {
      activeRelationTypes.value = new Set(relations.value.map(r => r.relation_type || '关联'))
    }
  } catch (err) {
    if (requestId === loadRequestId) {
      ElMessage.error('加载知识图谱失败: ' + (err?.response?.data?.message || err.message || '网络错误'))
    }
  } finally {
    if (requestId === loadRequestId) loading.value = false
  }
}

function cleanupGraph() {
  if (renderTimer) {
    clearTimeout(renderTimer)
    renderTimer = null
  }

  if (simulation) {
    simulation.stop()
    simulation = null
  }

  if (svg) {
    svg.selectAll('*').interrupt()
    svg.on('.zoom', null)
    svg.on('click', null)
  }

  if (graphRef.value) {
    d3.select(graphRef.value).selectAll('*').interrupt().remove()
  }

  svg = null
  zoomBehavior = null
  highlightedNode = null
}

function scheduleRender(delay = 0) {
  if (renderTimer) clearTimeout(renderTimer)
  renderTimer = setTimeout(() => {
    renderTimer = null
    renderGraph()
  }, delay)
}

function renderGraph() {
  if (!graphRef.value) return

  // 自动刷新时保留当前视图（缩放/平移），避免每次重绘都跳回原点
  const prevTransform = svg ? d3.zoomTransform(svg.node()) : null
  const hadView = !!prevTransform && (prevTransform.k !== 1 || prevTransform.x !== 0 || prevTransform.y !== 0)
  // 记住当前选中实体，重绘后恢复高亮
  const prevSelectedId = selectedEntity.value?.id || null

  cleanupGraph()

  const width = graphRef.value.clientWidth || 800
  const height = graphRef.value.clientHeight || 550

  svg = d3.select(graphRef.value)
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('class', 'kg-svg')

  // ---- defs: arrow markers + glow filter + gradients ----
  const defs = svg.append('defs')

  defs.append('filter').attr('id','glow').html(`
    <feGaussianBlur stdDeviation="3" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  `)

  defs.append('filter').attr('id','cosmicGlow').html(`
    <feGaussianBlur stdDeviation="5" result="coloredBlur"/>
    <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
  `)

  defs.append('filter').attr('id','shadow').html(`
    <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.15"/>
  `)

  for (const [t, c] of Object.entries(TYPE_COLORS)) {
    const safeId = typeDomId(t)
    const gradient = defs.append('radialGradient')
      .attr('id', 'planet-' + safeId)
      .attr('cx', '35%')
      .attr('cy', '28%')
      .attr('r', '70%')
    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#ffffff')
    gradient.append('stop').attr('offset', '38%').attr('stop-color', c)
    gradient.append('stop').attr('offset', '100%').attr('stop-color', '#111827')

    defs.append('marker')
      .attr('id', 'arrow-' + safeId)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 28).attr('refY', 0)
      .attr('markerWidth', 8).attr('markerHeight', 8)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', c)
      .attr('opacity', 0.78)
  }

  defs.append('marker')
    .attr('id', 'arrow-default')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 24).attr('refY', 0)
    .attr('markerWidth', 7).attr('markerHeight', 7)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#64748b')
    .attr('opacity', 0.55)

  const g = svg.append('g').attr('class', 'graph-root')

  zoomBehavior = d3.zoom()
    .scaleExtent([0.15, 5])
    .on('zoom', (event) => g.attr('transform', event.transform))
  svg.call(zoomBehavior)

  // 还原刷新前的视图变换
  if (hadView) {
    svg.call(zoomBehavior.transform, prevTransform)
  }

  // ---- build graph data ----
  const connCount = {}
  for (const e of entities.value) {
    connCount[e.name] = 0
  }
  for (const r of relations.value) {
    connCount[r.source] = (connCount[r.source] || 0) + 1
    connCount[r.target] = (connCount[r.target] || 0) + 1
  }

  const nodes = entities.value.map(e => ({
    id: e.id, name: e.name, type: e.entity_type || 'Concept',
    radius: Math.min(12 + Math.sqrt(connCount[e.name] || 0) * 4, 36),
    connections: connCount[e.name] || 0,
  }))

  // O(1) 查找表，替代每条连线的 nodes.find() 遍历
  const nodeByName = new Map(nodes.map(n => [n.name, n]))

  // 仅保留两端节点都在渲染集合中的关系，
  // 否则 d3.forceLink 会因引用缺失节点抛错 (missing: X) 导致整个图谱崩溃
  const linkMap = new Map()
  for (const r of relations.value) {
    if (!nodeByName.has(r.source) || !nodeByName.has(r.target)) continue
    const key = `${r.source}::${r.target}::${r.relation_type || r.rel}`
    if (!linkMap.has(key)) linkMap.set(key, r)
  }
  const links = Array.from(linkMap.values()).map(r => ({
    source: r.source, target: r.target, type: r.relation_type || r.rel || '关联',
  }))

  // 大图谱降级：关闭连线文字标签等高开销绘制
  const bigGraph = nodes.length > 150

  const starCount = Math.min(180, Math.max(72, nodes.length * 2))
  const stars = Array.from({ length: starCount }, (_, i) => ({
    id: i,
    x: ((i * 97) % Math.max(width, 1)),
    y: ((i * 53) % Math.max(height, 1)),
    r: 0.6 + ((i * 17) % 16) / 16,
    opacity: 0.16 + ((i * 29) % 70) / 160,
  }))

  g.append('g')
    .attr('class', 'cosmic-dust')
    .selectAll('circle')
    .data(stars)
    .join('circle')
    .attr('cx', d => d.x)
    .attr('cy', d => d.y)
    .attr('r', d => d.r)
    .attr('fill', '#dbeafe')
    .attr('opacity', d => d.opacity)

  // ---- links (paths with arrowheads) ----
  const linkGroup = g.append('g').attr('class', 'links')
  const linkPaths = linkGroup.selectAll('line').data(links).join('line')
    .attr('stroke', d => {
      const tgtNode = nodeByName.get(d.target)
      return TYPE_COLORS[tgtNode?.type] || '#9fb3ff'
    })
    .attr('stroke-width', bigGraph ? 1 : 1.55)
    .attr('stroke-opacity', bigGraph ? 0.34 : 0.58)
    .attr('filter', bigGraph ? null : 'url(#glow)')
    .attr('marker-end', d => {
      const tgtNode = nodeByName.get(d.target)
      return `url(#arrow-${typeDomId(tgtNode?.type || 'default')})`
    })
    .style('cursor', 'pointer')

  const linkLabelGroup = g.append('g').attr('class', 'link-labels')
  const linkLabels = linkLabelGroup.selectAll('text').data(links).join('text')
    .text(d => d.type)
    .attr('font-size', 10)
    .attr('fill', '#dbeafe')
    .attr('text-anchor', 'middle')
    .attr('dy', -4)
    .style('pointer-events', 'none')
    .style('opacity', 0.76)

  // ---- nodes ----
  const nodeGroup = g.append('g').attr('class', 'nodes')
  const nodeG = nodeGroup.selectAll('g').data(nodes).join('g')
    .attr('cursor', 'pointer')
    .call(d3.drag()
      .on('start', dragStarted)
      .on('drag', dragged)
      .on('end', dragEnded))
    .on('click', (event, d) => {
      event.stopPropagation()
      highlightNode(d)
    })
    .on('mouseenter', function(event, d) {
      d3.select(this).select('.node-core').interrupt().transition().duration(120).attr('filter', 'url(#shadow)')
      tooltip.style('opacity', 1).html(`<b>${d.name}</b><br><span style="opacity:.7">${getTypeName(d.type)} · ${d.connections} 个关系</span>`)
    })
    .on('mousemove', function(event) {
      const [mx, my] = d3.pointer(event, graphRef.value)
      tooltip.style('left', mx + 'px').style('top', (my - 10) + 'px')
    })
    .on('mouseleave', function() {
      d3.select(this).select('.node-core').interrupt().transition().duration(120).attr('filter', null)
      tooltip.style('opacity', 0)
    })

  nodeG.append('circle')
    .attr('class', 'node-halo')
    .attr('r', d => d.radius + 13)
    .attr('fill', d => (TYPE_COLORS[d.type] || '#9fb3ff') + '2b')
    .attr('stroke', d => (TYPE_COLORS[d.type] || '#9fb3ff') + '66')
    .attr('stroke-width', 1.2)
    .attr('filter', 'url(#cosmicGlow)')
    .attr('pointer-events', 'none')

  nodeG.append('ellipse')
    .attr('class', 'node-orbit')
    .attr('rx', d => d.radius + 16)
    .attr('ry', d => Math.max(8, d.radius * 0.45))
    .attr('fill', 'none')
    .attr('stroke', d => TYPE_COLORS[d.type] || '#9fb3ff')
    .attr('stroke-width', 1.2)
    .attr('stroke-opacity', d => d.connections > 1 ? 0.72 : 0.32)
    .attr('transform', d => `rotate(${(d.id || d.name.length) % 2 ? -18 : 18})`)
    .attr('pointer-events', 'none')

  nodeG.append('circle')
    .attr('class', 'node-core')
    .attr('r', d => d.radius)
    .attr('fill', d => `url(#planet-${typeDomId(d.type)})`)
    .attr('stroke', d => TYPE_COLORS[d.type] || '#9fb3ff')
    .attr('stroke-width', 2)
    .attr('filter', 'url(#cosmicGlow)')
    .style('transition', 'all 0.3s ease')

  nodeG.append('circle')
    .attr('class', 'node-specular')
    .attr('cx', d => -d.radius * 0.28)
    .attr('cy', d => -d.radius * 0.3)
    .attr('r', d => Math.max(2.4, d.radius * 0.18))
    .attr('fill', '#ffffff')
    .attr('opacity', 0.74)
    .attr('pointer-events', 'none')

  nodeG.append('text')
    .text(d => getTypeLabel(d.type))
    .attr('text-anchor', 'middle')
    .attr('dy', 5)
    .attr('font-size', d => Math.max(11, Math.min(16, d.radius - 4)))
    .attr('font-weight', 700)
    .attr('fill', '#08111f')
    .attr('pointer-events', 'none')

  nodeG.append('text')
    .attr('class', 'node-name')
    .text(d => d.name)
    .attr('text-anchor', 'middle')
    .attr('dy', d => d.radius + 14)
    .attr('font-size', 11)
    .attr('font-weight', 600)
    .attr('fill', '#eaf2ff')
    .attr('paint-order', 'stroke')
    .attr('stroke', '#07111f')
    .attr('stroke-width', 5)
    .attr('stroke-linejoin', 'round')
    .attr('pointer-events', 'none')

  // ---- tooltip ----
  const tooltip = d3.select(graphRef.value).append('div')
    .attr('class', 'graph-tooltip')
    .style('opacity', 0)

  // ---- force simulation ----
  const nodeCount = nodes.length
  // Dynamic spacing: more nodes → longer links, stronger repulsion
  const linkDist = Math.max(120, Math.min(260, 580 / Math.sqrt(nodeCount || 1)))
  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.name).distance(linkDist).strength(0.22))
    .force('charge', d3.forceManyBody().strength(d => -460 - d.radius * 12))
    .force('center', d3.forceCenter(width / 2, height / 2).strength(0.03))
    .force('x', d3.forceX(width / 2).strength(0.015))
    .force('y', d3.forceY(height / 2).strength(0.015))
    .force('collision', d3.forceCollide().radius(d => d.radius + 14).strength(0.9))
    .alphaDecay(bigGraph ? 0.045 : 0.015)
    .velocityDecay(bigGraph ? 0.45 : 0.35)

  simulation.on('tick', () => {
    linkPaths
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
    linkLabels
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2)
    nodeG.attr('transform', d => `translate(${d.x},${d.y})`)
  })

  // ---- click on background resets highlight ----
  svg.on('click', () => resetHighlight())

  // 首次渲染（无历史视图）时，待力学布局稳定后自动适应到所有节点
  if (!hadView && nodes.length) {
    setTimeout(() => fitGraphToNodes(nodes), 700)
  }

  // 重绘后恢复之前选中实体的高亮
  if (prevSelectedId) {
    const node = nodes.find(n => n.id === prevSelectedId)
    if (node) {
      highlightedNode = null
      highlightNode(node)
    }
  }
}

// 根据节点包围盒自动缩放/平移，使整个图谱居中可见
function fitGraphToNodes(nodes) {
  if (!svg || !zoomBehavior || !graphRef.value || !nodes.length) return
  const xs = nodes.map(n => n.x).filter(v => Number.isFinite(v))
  const ys = nodes.map(n => n.y).filter(v => Number.isFinite(v))
  if (!xs.length || !ys.length) return
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  const width = graphRef.value.clientWidth || 800
  const height = graphRef.value.clientHeight || 550
  const pad = 80
  const gw = Math.max(maxX - minX, 1)
  const gh = Math.max(maxY - minY, 1)
  const scale = Math.min(2, Math.max(0.2, Math.min((width - pad) / gw, (height - pad) / gh)))
  const cx = (minX + maxX) / 2
  const cy = (minY + maxY) / 2
  const transform = d3.zoomIdentity
    .translate(width / 2, height / 2)
    .scale(scale)
    .translate(-cx, -cy)
  svg.interrupt().transition().duration(400).call(zoomBehavior.transform, transform)
}

// ---- Highlight / Dim ----
function highlightNode(d) {
  if (!svg) return
  if (highlightedNode?.id === d.id) return
  highlightedNode = d
  selectedEntity.value = entities.value.find(e => e.id === d.id) || d

  const connectedNames = new Set()
  for (const r of relations.value) {
    if (r.source === d.name) connectedNames.add(r.target)
    if (r.target === d.name) connectedNames.add(r.source)
  }
  connectedNames.add(d.name)

  const duration = entities.value.length > 300 ? 0 : 140
  const nodeSel = svg.select('g.nodes').selectAll('g')
  const linkSel = svg.select('g.links').selectAll('line')
  const labelSel = svg.select('g.link-labels').selectAll('text')

  nodeSel.selectAll('*').interrupt()
  linkSel.interrupt()
  labelSel.interrupt()

  nodeSel.select('.node-core')
    .transition().duration(duration)
    .attr('stroke-opacity', n => connectedNames.has(n.name) ? 1 : 0.1)
    .attr('opacity', n => connectedNames.has(n.name) ? 1 : 0.2)
  nodeSel.select('.node-halo')
    .transition().duration(duration)
    .attr('opacity', n => connectedNames.has(n.name) ? 1 : 0.12)

  nodeSel.select('text')
    .transition().duration(duration)
    .attr('opacity', n => connectedNames.has(n.name) ? 1 : 0.15)

  linkSel
    .transition().duration(duration)
    .attr('stroke-opacity', r => {
      return (r.source.name === d.name || r.target.name === d.name) ? 0.8 : 0.05
    })
    .attr('stroke-width', r => {
      return (r.source.name === d.name || r.target.name === d.name) ? 3 : 1.5
    })

  labelSel
    .transition().duration(duration)
    .style('opacity', r => {
      return (r.source.name === d.name || r.target.name === d.name) ? 1 : 0.05
    })
    .attr('font-weight', r => {
      return (r.source.name === d.name || r.target.name === d.name) ? 700 : 400
    })
}

function resetHighlight() {
  if (!svg || !highlightedNode) return
  highlightedNode = null
  selectedEntity.value = null
  const duration = entities.value.length > 300 ? 0 : 140

  svg.selectAll('g.nodes g *').interrupt()
  svg.selectAll('g.links line').interrupt()
  svg.selectAll('g.link-labels text').interrupt()

  svg.select('g.nodes').selectAll('g').select('.node-core')
    .transition().duration(duration)
    .attr('stroke-opacity', 1).attr('opacity', 1)
  svg.select('g.nodes').selectAll('g').select('.node-halo')
    .transition().duration(duration)
    .attr('opacity', 1)
  svg.select('g.nodes').selectAll('g').select('text')
    .transition().duration(duration)
    .attr('opacity', 1)
  svg.select('g.links').selectAll('line')
    .transition().duration(duration)
    .attr('stroke-opacity', 0.42).attr('stroke-width', 1.4)
  svg.select('g.link-labels').selectAll('text')
    .transition().duration(duration)
    .style('opacity', 0.72).attr('font-weight', 400)
}

function dragStarted(event) {
  if (!simulation) return
  if (!event.active) simulation.alphaTarget(0.3).restart()
  event.subject.fx = event.subject.x
  event.subject.fy = event.subject.y
}
function dragged(event) {
  event.subject.fx = event.x
  event.subject.fy = event.y
}
function dragEnded(event) {
  if (!simulation) return
  if (!event.active) simulation.alphaTarget(0)
  event.subject.fx = null
  event.subject.fy = null
}

function handleSearch(q) { loadGraph(q) }

function selectEntity(entity) {
  selectedEntity.value = entity
}

function exitGraph() {
  router.push('/admin')
}

function toggleRightPanel() {
  rightPanelCollapsed.value = !rightPanelCollapsed.value
}

async function deleteEntity(entity) {
  if (!confirm(`确定删除实体「${entity.name}」？该实体的所有关系也将被删除。`)) return
  try {
    await request.delete(`/graph/entities/${entity.id}`)
    ElMessage.success('实体已删除')
    if (selectedEntity.value?.id === entity.id) selectedEntity.value = null
    await loadGraph()
  } catch (err) {
    ElMessage.error('删除失败: ' + (err?.response?.data?.message || err.message || '网络错误'))
  }
}

async function deleteRelation(rel) {
  if (!confirm(`确定删除关系「${rel.source} → ${rel.relation_type} → ${rel.target}」？`)) return
  try {
    await request.delete('/graph/relations', { data: { source: rel.source, target: rel.target, relation_type: rel.relation_type } })
    ElMessage.success('关系已删除')
    await loadGraph()
  } catch (err) {
    ElMessage.error('删除失败: ' + (err?.response?.data?.message || err.message || '网络错误'))
  }
}

function zoomIn() {
  semanticCosmosRef.value?.zoomIn()
}
function zoomOut() {
  semanticCosmosRef.value?.zoomOut()
}
function resetZoom() {
  semanticCosmosRef.value?.resetView()
}
function fitToView() {
  semanticCosmosRef.value?.fitView()
}

async function submitEntity() {
  const payload = {
    name: newEntity.value.name.trim(),
    entity_type: newEntity.value.entity_type.trim(),
    description: newEntity.value.description.trim(),
  }
  if (!payload.name || !payload.entity_type) {
    ElMessage.warning('请填写实体名称和实体类型')
    return
  }
  try {
    if (editingEntityId.value) {
      await request.put(`/graph/entities/${editingEntityId.value}`, payload)
      ElMessage.success('实体修改成功')
    } else {
      await request.post('/graph/entities', payload)
      ElMessage.success('实体创建成功')
    }
    closeEntityModal()
    await loadGraph()
  } catch (err) {
    ElMessage.error(`${editingEntityId.value ? '修改' : '创建'}实体失败: ` + (err?.response?.data?.message || err.message || '网络错误'))
  }
}

async function submitRelation() {
  const payload = {
    source: newRelation.value.source.trim(),
    target: newRelation.value.target.trim(),
    relation_type: newRelation.value.relation_type.trim(),
    description: newRelation.value.description.trim(),
  }
  if (!payload.source || !payload.target || !payload.relation_type) {
    ElMessage.warning('请填写起始实体、目标实体和关系类型')
    return
  }
  if (payload.source === payload.target) {
    ElMessage.warning('起始实体和目标实体不能相同')
    return
  }
  try {
    if (editingRelationOriginal.value) {
      await request.put('/graph/relations', {
        original_source: editingRelationOriginal.value.source,
        original_target: editingRelationOriginal.value.target,
        original_relation_type: editingRelationOriginal.value.relation_type,
        ...payload,
      })
      ElMessage.success('关系修改成功')
    } else {
      await request.post('/graph/relations', payload)
      ElMessage.success('关系创建成功')
    }
    closeRelationModal()
    await loadGraph()
  } catch (err) {
    ElMessage.error(`${editingRelationOriginal.value ? '修改' : '创建'}关系失败: ` + (err?.response?.data?.message || err.message || '网络错误'))
  }
}

watch(typeFilter, () => loadGraph())

// 监听文档更新事件，自动刷新图谱（防抖，避免解析多阶段状态变更引发频繁重绘）
let refreshTimer = null
const unsubscribe = on('documents:updated', () => {
  if (refreshTimer) clearTimeout(refreshTimer)
  refreshTimer = setTimeout(() => {
    refreshTimer = null
    loadGraph()
  }, 600)
})

onMounted(() => {
  loadGraph()
})
onUnmounted(() => {
  unsubscribe()
  if (refreshTimer) clearTimeout(refreshTimer)
  loadRequestId++
  cleanupGraph()
})
</script>

<style scoped>
.knowledge-graph-page {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: block;
  height: 100vh;
  min-height: 100vh;
  overflow: hidden;
  background: #000;
}

.cosmos-exit {
  position: absolute;
  top: 16px;
  left: 18px;
  z-index: 42;
  height: 38px;
  padding: 0 12px 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: rgba(226, 246, 255, 0.92);
  background: rgba(3, 7, 18, 0.72);
  border: 1px solid rgba(125, 211, 252, 0.22);
  border-radius: 7px;
  cursor: pointer;
  box-shadow: 0 12px 34px rgba(0, 0, 0, 0.38), inset 0 1px 0 rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(16px);
  transition: border-color 0.2s, background 0.2s, transform 0.2s;
}

.cosmos-exit:hover {
  transform: translateY(-1px);
  background: rgba(8, 15, 30, 0.88);
  border-color: rgba(125, 211, 252, 0.44);
}

.cosmos-exit svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

.cosmos-exit span {
  font-size: 13px;
  font-weight: 650;
}

.knowledge-graph-page :deep(.graph-toolbar) {
  position: absolute;
  top: 14px;
  left: 100px;
  z-index: 32;
  width: min(760px, calc(100vw - 520px));
  padding: 8px;
  gap: 10px;
  background: rgba(3, 7, 18, 0.7);
  border-color: rgba(125, 211, 252, 0.18);
  box-shadow: 0 18px 46px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(18px);
}

.knowledge-graph-page :deep(.toolbar-title) {
  display: none;
}

.knowledge-graph-page :deep(.left) {
  width: 100%;
  gap: 8px;
}

.knowledge-graph-page :deep(.right) {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.knowledge-graph-page :deep(.search-box),
.knowledge-graph-page :deep(.filter-select),
.knowledge-graph-page :deep(.btn) {
  height: 34px;
}

.knowledge-graph-page :deep(.search-box) {
  flex: 1;
  width: auto;
  background: rgba(8, 15, 30, 0.82);
}

.knowledge-graph-page :deep(.filter-select) {
  width: 128px;
  background: rgba(8, 15, 30, 0.82);
}

.knowledge-graph-page :deep(.btn) {
  padding: 0 10px;
  white-space: nowrap;
}

.graph-layout {
  position: absolute;
  inset: 0;
  display: block;
  overflow: hidden;
  min-height: 0;
}

/* Graph canvas */
.graph-canvas {
  position: absolute;
  inset: 0;
  background: #000;
  border: 0;
  border-radius: 0;
  box-shadow: none;
  overflow: hidden;
  min-width: 0;
}

.graph-canvas::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 30% 22%, rgba(125, 211, 252, 0.08), transparent 30%),
    radial-gradient(circle at 68% 42%, rgba(190, 242, 100, 0.06), transparent 30%),
    radial-gradient(circle at 48% 78%, rgba(249, 168, 212, 0.08), transparent 32%);
  mix-blend-mode: screen;
  z-index: 1;
}

.graph-canvas::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.12), transparent 18%, transparent 82%, rgba(0, 0, 0, 0.38));
  mask-image: none;
  z-index: 2;
}

.graph-svg-container {
  width: 100%;
  height: 100%;
  min-height: 560px;
  background:
    radial-gradient(circle at center, rgba(15, 23, 42, 0.2), rgba(2, 6, 23, 0.96)),
    #070b14;
  position: relative;
  z-index: 3;
}

.kg-svg {
  cursor: grab;
}

.kg-svg:active {
  cursor: grabbing;
}

:deep(.cosmic-dust circle) {
  animation: starPulse 4.8s ease-in-out infinite;
}

:deep(.node-orbit) {
  transform-box: fill-box;
  transform-origin: center;
  animation: orbitDrift 9s linear infinite;
}

:deep(.node-halo) {
  animation: haloBreath 3.8s ease-in-out infinite;
}

:deep(.links line) {
  stroke-dasharray: 6 12;
  animation: lightTrace 9s linear infinite;
}

@keyframes starPulse {
  0%, 100% { opacity: 0.18; }
  50% { opacity: 0.62; }
}

@keyframes orbitDrift {
  from { rotate: 0deg; }
  to { rotate: 360deg; }
}

@keyframes haloBreath {
  0%, 100% { opacity: 0.62; }
  50% { opacity: 1; }
}

@keyframes lightTrace {
  to { stroke-dashoffset: -72; }
}

.graph-tooltip {
  position: absolute;
  padding: 9px 12px;
  background: rgba(6, 11, 24, 0.92);
  color: #fff;
  border: 1px solid rgba(125, 211, 252, 0.24);
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
  pointer-events: none;
  z-index: 100;
  transform: translate(-50%, -130%);
  white-space: nowrap;
  box-shadow: 0 18px 36px rgba(0, 0, 0, 0.34), 0 0 28px rgba(125, 211, 252, 0.16);
  backdrop-filter: blur(14px);
}

.graph-loading,
.graph-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 5;
  color: #cbd5e1;
  font-size: 13px;
}

.graph-empty {
  flex-direction: column;
  gap: 6px;
}

.empty-title {
  font-size: 15px;
  font-weight: 650;
  color: #e2e8f0;
}

.empty-desc {
  color: #94a3b8;
}

/* Stats overlay */
.graph-stats {
  position: absolute;
  top: 16px;
  right: 22px;
  left: auto;
  display: flex;
  gap: 0;
  z-index: 30;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.36);
  backdrop-filter: blur(18px);
  box-shadow: 0 14px 34px rgba(0, 0, 0, 0.38);
}

.graph-stat {
  padding: 8px 14px;
  min-width: 76px;
  border-right: 1px solid rgba(148, 163, 184, 0.16);
}

.graph-stat:last-child {
  border-right: 0;
}

.graph-stat .num {
  font-size: 17px;
  font-weight: 700;
  color: #eff6ff;
  line-height: 1.1;
}

.graph-stat .label {
  margin-top: 4px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.58);
}

/* Filter Panel */
.graph-filter-panel {
  position: absolute;
  top: 68px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
  display: flex;
  gap: 16px;
  max-width: min(90vw, 720px);
  background: rgba(2, 6, 23, 0.82);
  border: 1px solid rgba(125, 211, 252, 0.16);
  border-radius: 10px;
  padding: 10px 16px;
  backdrop-filter: blur(18px);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.45);
}

.filter-section {
  flex: 1;
  min-width: 0;
}

.filter-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.filter-section-title {
  font-size: 11px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-count {
  font-size: 10px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  padding: 1px 6px;
  font-family: monospace;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  max-height: 80px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.1) transparent;
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.45);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  font-family: inherit;
}

.filter-chip:hover {
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.8);
}

.filter-chip.active {
  color: #ffffff;
  background: color-mix(in srgb, var(--chip-color, #06b6d4) 18%, transparent);
  border-color: color-mix(in srgb, var(--chip-color, #06b6d4) 40%, transparent);
  box-shadow: 0 0 8px color-mix(in srgb, var(--chip-color, #06b6d4) 20%, transparent);
}

.filter-chip:not(.active) {
  opacity: 0.45;
}

.filter-chip .chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.25);
  flex-shrink: 0;
  transition: all 0.2s;
}

.filter-chip.active .chip-dot {
  box-shadow: 0 0 4px var(--chip-color, #06b6d4);
}

.filter-chip .chip-count {
  font-size: 9px;
  opacity: 0.5;
  font-family: monospace;
}

.filter-chip.rel-chip {
  --chip-color: #06b6d4;
}

.filter-chip.rel-chip.active {
  background: rgba(6, 182, 212, 0.15);
  border-color: rgba(6, 182, 212, 0.4);
}

.filter-chip.entity-chip {
  --chip-color: #a78bfa;
}

.filter-chip.entity-chip.active {
  background: rgba(167, 139, 250, 0.15);
  border-color: rgba(167, 139, 250, 0.4);
}

/* Legend */
.graph-legend {
  position: absolute;
  bottom: 16px;
  left: 16px;
  max-width: min(520px, calc(100% - 32px));
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  background: rgba(8, 15, 30, 0.72);
  border: 1px solid rgba(125, 211, 252, 0.22);
  border-radius: 8px;
  padding: 10px;
  box-shadow: 0 14px 34px rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(12px);
  z-index: 10;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #dbeafe;
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 999px;
  padding: 4px 8px;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

/* Zoom controls */
.graph-controls {
  position: absolute;
  top: 78px;
  right: 22px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  z-index: 30;
}

.graph-control {
  width: 34px;
  height: 34px;
  background: rgba(8, 15, 30, 0.76);
  border: 1px solid rgba(125, 211, 252, 0.24);
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.26);
  transition: background 0.2s, color 0.2s, transform 0.2s;
}

.graph-control:hover {
  background: rgba(14, 165, 233, 0.24);
  transform: translateY(-1px);
}

.graph-control svg {
  width: 18px;
  height: 18px;
  fill: #dbeafe;
}

/* Left panel */
.right-panel {
  position: absolute;
  top: 96px;
  left: 24px;
  right: auto;
  bottom: 28px;
  z-index: 36;
  width: 360px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  transition: opacity 0.2s ease, transform 0.24s ease;
}

.right-panel.collapsed {
  opacity: 0;
  transform: translateX(calc(-100% - 56px));
  pointer-events: none;
  overflow: hidden;
}

.panel-toggle {
  position: absolute;
  top: 112px;
  left: 384px;
  z-index: 38;
  width: 28px;
  height: 56px;
  border: 1px solid rgba(125, 211, 252, 0.26);
  border-left-color: rgba(125, 211, 252, 0.16);
  border-radius: 0 8px 8px 0;
  background: rgba(8, 15, 30, 0.88);
  color: #bfdbfe;
  box-shadow: 0 16px 34px rgba(0, 0, 0, 0.28);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: left 0.24s ease, background 0.2s, color 0.2s;
}

.panel-toggle:hover {
  background: rgba(37, 99, 235, 0.28);
  color: #ffffff;
}

.panel-toggle.collapsed {
  left: 18px;
  border-radius: 0 8px 8px 0;
}

.panel-toggle svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

.panel-card {
  background: rgba(8, 15, 30, 0.86);
  border: 1px solid rgba(125, 211, 252, 0.2);
  border-radius: 8px;
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.24);
  min-height: 0;
  overflow: hidden;
  backdrop-filter: blur(16px);
}

.panel-header {
  padding: 14px 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  font-size: 15px;
  font-weight: 650;
  color: #eaf2ff;
  margin: 0;
}

.panel-count {
  font-size: 12px;
  color: #93c5fd;
}

.panel-search {
  margin: 8px 8px 0;
  height: 34px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  border: 1px solid rgba(125, 211, 252, 0.18);
  border-radius: 7px;
  background: rgba(3, 7, 18, 0.52);
  transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
}

.panel-search:focus-within {
  border-color: rgba(125, 211, 252, 0.48);
  background: rgba(8, 15, 30, 0.82);
  box-shadow: 0 0 0 3px rgba(125, 211, 252, 0.1);
}

.panel-search svg {
  width: 15px;
  height: 15px;
  fill: #7dd3fc;
  flex-shrink: 0;
}

.panel-search input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  color: #eaf2ff;
  background: transparent;
  font-size: 12px;
  font-family: inherit;
}

.panel-search input::placeholder {
  color: #64748b;
}

.panel-body {
  padding: 8px;
  max-height: 310px;
  overflow-y: auto;
}

/* Entity list */
.entity-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.entity-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 7px;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.entity-item:hover {
  background: rgba(37, 99, 235, 0.12);
  border-color: rgba(125, 211, 252, 0.18);
}

.entity-item.active {
  background: rgba(37, 99, 235, 0.22);
  border-color: rgba(125, 211, 252, 0.42);
}

.entity-item:last-child {
  border-bottom: none;
}

.entity-icon {
  width: 32px;
  height: 32px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 500;
  flex-shrink: 0;
}

.entity-info {
  flex: 1;
  min-width: 0;
}

.entity-info .name {
  font-size: 13px;
  font-weight: 650;
  color: #eaf2ff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entity-info .type {
  margin-top: 2px;
  font-size: 11px;
  color: #94a3b8;
}

.entity-info .relations {
  margin-top: 2px;
  font-size: 11px;
  color: #7dd3fc;
}

.item-actions {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  opacity: 1;
  transition: opacity 0.2s;
}

.entity-item:hover .item-actions,
.entity-item.active .item-actions,
.relation-item:hover .item-actions {
  opacity: 1;
}

.type-c0  { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.2); }
	.type-c1  { background: rgba(248, 113, 113, 0.15); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.2); }
	.type-c2  { background: rgba(52, 211, 153, 0.15); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.2); }
	.type-c3  { background: rgba(251, 191, 36, 0.15); color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.2); }
	.type-c4  { background: rgba(167, 139, 250, 0.15); color: #a78bfa; border: 1px solid rgba(167, 139, 250, 0.2); }
	.type-c5  { background: rgba(45, 212, 191, 0.15); color: #2dd4bf; border: 1px solid rgba(45, 212, 191, 0.2); }
	.type-c6  { background: rgba(251, 146, 60, 0.15); color: #fb923c; border: 1px solid rgba(251, 146, 60, 0.2); }
	.type-c7  { background: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.2); }
	.type-c8  { background: rgba(74, 222, 128, 0.15); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.2); }
	.type-c9  { background: rgba(244, 114, 182, 0.15); color: #f472b6; border: 1px solid rgba(244, 114, 182, 0.2); }
	.type-c10 { background: rgba(192, 132, 252, 0.15); color: #c084fc; border: 1px solid rgba(192, 132, 252, 0.2); }
	.type-c11 { background: rgba(96, 165, 250, 0.15); color: #60a5fa; border: 1px solid rgba(96, 165, 250, 0.2); }
	.type-c12 { background: rgba(253, 224, 71, 0.15); color: #fde047; border: 1px solid rgba(253, 224, 71, 0.2); }
	.type-c13 { background: rgba(168, 85, 247, 0.15); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.2); }
	.type-c14 { background: rgba(56, 189, 248, 0.12); color: #7dd3fc; border: 1px solid rgba(56, 189, 248, 0.18); }
	.type-c15 { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }

/* Relation list */
.relation-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.relation-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 10px;
  border: 1px solid transparent;
  border-radius: 7px;
  font-size: 13px;
  color: #cbd5e1;
  flex-wrap: wrap;
}

.relation-item:hover {
  background: rgba(37, 99, 235, 0.12);
  border-color: rgba(125, 211, 252, 0.18);
}

.relation-item:last-child {
  border-bottom: none;
}

.rel-name {
  font-weight: 650;
  color: #eaf2ff;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.relation-arrow {
  color: #94a3b8;
  font-weight: 600;
}

.relation-label {
  color: #7dd3fc;
  font-size: 11px;
  background: rgba(37, 99, 235, 0.22);
  border: 1px solid rgba(125, 211, 252, 0.22);
  padding: 2px 7px;
  border-radius: 999px;
}

.relation-actions {
  margin-left: auto;
}

.relation-empty {
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  padding: 20px 0;
}

.list-more-tip {
  text-align: center;
  color: #fde68a;
  background: rgba(67, 43, 8, 0.62);
  border: 1px dashed rgba(250, 204, 21, 0.32);
  border-radius: 6px;
  font-size: 12px;
  padding: 8px 10px;
  margin-top: 6px;
  list-style: none;
}

/* Modals */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(3, 7, 18, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(12px);
}

.modal {
  background:
    linear-gradient(135deg, rgba(8, 15, 30, 0.96), rgba(15, 23, 42, 0.94)),
    var(--color-surface-solid);
  border-radius: 8px;
  width: 480px;
  max-width: calc(100vw - 32px);
  border: 1px solid rgba(125, 211, 252, 0.24);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.58), 0 0 36px rgba(14, 165, 233, 0.1);
  overflow: hidden;
}

.modal-header {
  padding: 18px 20px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 650;
  color: #eaf2ff;
  margin: 0;
}

.modal-close {
  width: 24px;
  height: 24px;
  cursor: pointer;
  fill: #94a3b8;
  transition: fill 0.2s;
}

.modal-close:hover {
  fill: #eaf2ff;
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 18px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 6px;
  font-weight: 500;
}

.form-group label .required {
  color: var(--color-danger);
}

.form-input {
  width: 100%;
  height: 36px;
  border: 1px solid rgba(125, 211, 252, 0.22);
  border-radius: 6px;
  padding: 0 12px;
  font-size: 13px;
  outline: none;
  color: #eaf2ff;
  background: rgba(8, 15, 30, 0.82);
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: rgba(125, 211, 252, 0.56);
  background: rgba(8, 15, 30, 0.96);
  box-shadow: 0 0 0 3px rgba(125, 211, 252, 0.12);
}

.form-select {
  width: 100%;
  height: 36px;
  border: 1px solid rgba(125, 211, 252, 0.22);
  border-radius: 6px;
  padding: 0 12px;
  font-size: 13px;
  color: #dbeafe;
  background: rgba(8, 15, 30, 0.82);
  outline: none;
  box-sizing: border-box;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}

.form-select:focus {
  border-color: rgba(125, 211, 252, 0.56);
  background: rgba(8, 15, 30, 0.96);
  box-shadow: 0 0 0 3px rgba(125, 211, 252, 0.12);
}

.form-textarea {
  width: 100%;
  border: 1px solid rgba(125, 211, 252, 0.22);
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 13px;
  outline: none;
  resize: vertical;
  min-height: 60px;
  font-family: inherit;
  color: #eaf2ff;
  background: rgba(8, 15, 30, 0.82);
  box-sizing: border-box;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}

.form-textarea:focus {
  border-color: rgba(125, 211, 252, 0.56);
  background: rgba(8, 15, 30, 0.96);
  box-shadow: 0 0 0 3px rgba(125, 211, 252, 0.12);
}

.modal-footer {
  padding: 14px 20px;
  border-top: 1px solid rgba(148, 163, 184, 0.16);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
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
}

.btn-primary {
  background: #7dd3fc;
  color: #07111f;
  border-color: transparent;
  box-shadow: 0 0 14px rgba(125, 211, 252, 0.28);
}

.btn-primary:hover {
  background: #bae6fd;
  box-shadow: 0 0 22px rgba(125, 211, 252, 0.4);
}

.btn-default {
  background: rgba(15, 23, 42, 0.78);
  color: #dbeafe;
  border-color: rgba(125, 211, 252, 0.22);
}

.btn-default:hover {
  border-color: rgba(125, 211, 252, 0.56);
  color: #ffffff;
  background: rgba(37, 99, 235, 0.16);
}

.btn-icon {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  flex-shrink: 0;
  transition: background 0.2s;
}

.btn-icon:hover {
  background: rgba(125, 211, 252, 0.12);
}

.btn-icon svg {
  width: 16px;
  height: 16px;
  fill: #94a3b8;
}

.btn-icon:hover svg {
  fill: #7dd3fc;
}

.btn-delete:hover,
.btn-delete-sm:hover {
  background: rgba(248, 113, 113, 0.12);
}

.btn-delete:hover svg,
.btn-delete-sm:hover svg {
  fill: #f87171;
}

.btn-edit-sm,
.btn-delete-sm {
  width: 22px;
  height: 22px;
}

.btn-edit-sm svg,
.btn-delete-sm svg {
  width: 14px;
  height: 14px;
}

@media (max-width: 1100px) {
  .cosmos-exit {
    top: 10px;
    left: 10px;
  }

  .knowledge-graph-page :deep(.graph-toolbar) {
    top: 56px;
    left: 10px;
    width: calc(100vw - 20px);
    flex-wrap: wrap;
  }

  .graph-stats {
    display: none;
  }

  .graph-controls {
    top: 88px;
    right: 12px;
  }

  .right-panel {
    top: 88px;
    left: 12px;
    right: auto;
    bottom: 12px;
    width: min(360px, calc(100vw - 48px));
  }

  .graph-filter-panel {
    top: 110px;
    left: 10px;
    right: 10px;
    transform: none;
    max-width: none;
    flex-direction: column;
    gap: 10px;
  }

  .panel-toggle {
    top: 104px;
    left: min(384px, calc(100vw - 40px));
  }

  .panel-toggle.collapsed {
    left: 8px;
  }
}
</style>
