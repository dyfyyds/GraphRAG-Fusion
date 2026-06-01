<template>
  <div class="knowledge-graph-page">
    <!-- Toolbar -->
    <GraphToolbar
      v-model:type-filter="typeFilter"
      @search="handleSearch"
      @add-entity="showAddEntity = true"
      @add-relation="showAddRelation = true"
    />

    <div class="graph-layout">
      <!-- Main graph area -->
      <div class="graph-canvas">
        <!-- Floating stats overlay -->
        <div class="graph-stats">
          <div class="graph-stat">
            <div class="num">{{ entityCount.toLocaleString() }}</div>
            <div class="label">实体总数</div>
          </div>
          <div class="graph-stat">
            <div class="num">{{ relationCount.toLocaleString() }}</div>
            <div class="label">关系总数</div>
          </div>
          <div class="graph-stat">
            <div class="num">{{ typeCount }}</div>
            <div class="label">实体类型</div>
          </div>
        </div>

        <!-- 大图谱折叠提示 -->
        <div v-if="hiddenNodeCount > 0" class="graph-truncate-tip">
          图谱较大，仅展示连接最密集的前 {{ MAX_RENDER_NODES }} 个实体（已折叠 {{ hiddenNodeCount }} 个）。可用搜索或类型筛选定位具体实体。
        </div>

        <!-- D3 graph container -->
        <div ref="graphRef" class="graph-svg-container"></div>
        <div v-if="loading" class="graph-loading">加载图谱中...</div>
        <div v-else-if="!entities.length" class="graph-empty">
          <div class="empty-title">暂无实体</div>
          <div class="empty-desc">添加实体或导入文档后，图谱会显示在这里</div>
        </div>

        <!-- Color-coded legend (dynamic) -->
        <div class="graph-legend">
          <div class="legend-item" v-for="(color, type) in TYPE_COLORS" :key="type">
            <div class="legend-dot" :style="{ background: color }"></div>{{ getTypeName(type) }}
          </div>
        </div>

        <!-- Zoom controls -->
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
            <span class="panel-count">共 {{ entityCount.toLocaleString() }} 个</span>
          </div>
          <div class="panel-body">
            <ul class="entity-list">
              <li
                v-for="entity in displayedEntities"
                :key="entity.id"
                class="entity-item"
                :class="{ active: selectedEntity?.id === entity.id }"
                @click="selectedEntity = entity"
              >
                <div class="entity-icon" :class="getTypeClass(entity.entity_type)">
                  {{ getTypeLabel(entity.entity_type) }}
                </div>
                <div class="entity-info">
                  <div class="name">{{ entity.name }}</div>
                  <div class="type">类型: {{ getTypeName(entity.entity_type) }}</div>
                  <div class="relations">{{ getEntityRelationCount(entity.id) }} 个关系</div>
                </div>
                <button class="btn-icon btn-delete" @click.stop="deleteEntity(entity)" title="删除实体">
                  <svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                </button>
              </li>
              <li v-if="entities.length > displayedEntities.length" class="list-more-tip">
                仅显示前 {{ displayedEntities.length }} / {{ entityCount.toLocaleString() }} 个实体，请用搜索筛选
              </li>
            </ul>
          </div>
        </div>

        <!-- Relation list card -->
        <div class="panel-card">
          <div class="panel-header">
            <h3>关系列表</h3>
            <span class="panel-count">{{ selectedEntity ? '选中实体的关系' : '全部关系' }}</span>
          </div>
          <div class="panel-body">
            <ul class="relation-list">
              <li v-for="(rel, idx) in displayedRelations" :key="idx" class="relation-item">
                <span class="rel-name">{{ getEntityName(rel.source) }}</span>
                <span class="relation-arrow">→</span>
                <span class="relation-label">{{ rel.relation_type }}</span>
                <span class="relation-arrow">→</span>
                <span class="rel-name">{{ getEntityName(rel.target) }}</span>
                <button class="btn-icon btn-delete-sm" @click.stop="deleteRelation(rel)" title="删除关系">
                  <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 19 19 17.59 13.41 12z"/></svg>
                </button>
              </li>
              <li v-if="filteredRelations.length > displayedRelations.length" class="list-more-tip">
                仅显示前 {{ displayedRelations.length }} / {{ filteredRelations.length.toLocaleString() }} 条关系
              </li>
              <li v-if="filteredRelations.length === 0" class="relation-empty">暂无关系数据</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Add Entity Modal -->
    <div v-if="showAddEntity" class="modal-overlay" @click.self="showAddEntity = false">
      <div class="modal">
        <div class="modal-header">
          <h3>添加实体</h3>
          <svg class="modal-close" viewBox="0 0 24 24" @click="showAddEntity = false">
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
            <select v-model="newEntity.entity_type" class="form-select">
              <option value="Product">产品</option>
              <option value="Department">部门</option>
              <option value="Person">人物</option>
              <option value="Concept">概念</option>
              <option value="Process">流程</option>
            </select>
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea v-model="newEntity.description" class="form-textarea" placeholder="请输入实体描述"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-default" @click="showAddEntity = false">取消</button>
          <button class="btn btn-primary" @click="submitEntity">确定</button>
        </div>
      </div>
    </div>

    <!-- Add Relation Modal -->
    <div v-if="showAddRelation" class="modal-overlay" @click.self="showAddRelation = false">
      <div class="modal">
        <div class="modal-header">
          <h3>添加关系</h3>
          <svg class="modal-close" viewBox="0 0 24 24" @click="showAddRelation = false">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
          </svg>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>起始实体 <span class="required">*</span></label>
            <select v-model="newRelation.source" class="form-select">
              <option v-for="e in entities" :key="e.id" :value="e.name">{{ e.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>关系类型 <span class="required">*</span></label>
            <select v-model="newRelation.relation_type" class="form-select">
              <option value="包含">包含</option>
              <option value="属于">属于</option>
              <option value="生产">生产</option>
              <option value="使用">使用</option>
              <option value="依赖">依赖</option>
              <option value="导致">导致</option>
            </select>
          </div>
          <div class="form-group">
            <label>目标实体 <span class="required">*</span></label>
            <select v-model="newRelation.target" class="form-select">
              <option v-for="e in entities" :key="e.id" :value="e.name">{{ e.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea v-model="newRelation.description" class="form-textarea" placeholder="请输入关系描述"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-default" @click="showAddRelation = false">取消</button>
          <button class="btn btn-primary" @click="submitRelation">确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as d3 from 'd3'
import GraphToolbar from '../../components/graph/GraphToolbar.vue'
import request from '../../api/request'
import { on } from '../../utils/eventBus'

const graphRef = ref()
const selectedEntity = ref(null)
const typeFilter = ref('')
const entities = ref([])
const relations = ref([])
const showAddEntity = ref(false)
const showAddRelation = ref(false)
const loading = ref(false)
const rightPanelCollapsed = ref(false)
const hiddenNodeCount = ref(0)  // 大图谱保护：被折叠未渲染的节点数

// 大图谱渲染上限：超过则只渲染连接度最高的前 N 个节点，避免浏览器卡死/崩溃
const MAX_RENDER_NODES = 300

let simulation = null
let svg = null
let zoomBehavior = null
let renderTimer = null
let loadRequestId = 0
let highlightedNode = null

const newEntity = ref({ name: '', entity_type: 'Product', description: '' })
const newRelation = ref({ source: '', target: '', relation_type: '包含', description: '' })

const TYPE_PALETTE = ['#409eff', '#f56c6c', '#67c23a', '#e6a23c', '#9b59b6', '#36cfc9', '#ff7a45', '#597ef7', '#73d13d', '#ff85c0', '#b37feb', '#5cdbd3', '#ffc53d', '#9254de', '#40a9ff', '#ff4d4f']

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

const entityCount = computed(() => entities.value.length)
const relationCount = computed(() => relations.value.length)
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

// 右侧列表渲染上限：大数据量下避免一次渲染上千 DOM 节点导致页面卡死
const MAX_LIST_ITEMS = 500

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

const displayedEntities = computed(() => entities.value.slice(0, MAX_LIST_ITEMS))
const displayedRelations = computed(() => filteredRelations.value.slice(0, MAX_LIST_ITEMS))

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

async function loadGraph(query = '') {
  const requestId = ++loadRequestId
  loading.value = true
  try {
    const [entRes, relRes] = await Promise.all([
      request.get('/graph/entities', { params: { q: query || undefined, limit: 1000, entity_type: typeFilter.value || undefined } }),
      request.get('/graph/relations', { params: { limit: 1000 } }),
    ])
    if (requestId !== loadRequestId) return
    entities.value = Array.isArray(entRes) ? entRes : (entRes.data || [])
    relations.value = Array.isArray(relRes) ? relRes : (relRes.data || [])
    assignTypeStyles()
    renderGraph()
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

  defs.append('filter').attr('id','shadow').html(`
    <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.15"/>
  `)

  for (const [t, c] of Object.entries(TYPE_COLORS)) {
    defs.append('marker')
      .attr('id', 'arrow-' + t)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 28).attr('refY', 0)
      .attr('markerWidth', 8).attr('markerHeight', 8)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#64748b')
      .attr('opacity', 0.65)
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

  // 大图谱保护：节点过多时只渲染连接度最高的前 N 个，避免浏览器卡死/崩溃
  let renderEntities = entities.value
  if (entities.value.length > MAX_RENDER_NODES) {
    renderEntities = [...entities.value]
      .sort((a, b) => (connCount[b.name] || 0) - (connCount[a.name] || 0))
      .slice(0, MAX_RENDER_NODES)
    hiddenNodeCount.value = entities.value.length - renderEntities.length
  } else {
    hiddenNodeCount.value = 0
  }

  const nodes = renderEntities.map(e => ({
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

  // ---- links (paths with arrowheads) ----
  const linkGroup = g.append('g').attr('class', 'links')
  const linkPaths = linkGroup.selectAll('line').data(links).join('line')
    .attr('stroke', d => {
      const tgtNode = nodeByName.get(d.target)
      return TYPE_COLORS[tgtNode?.type] || '#909399'
    })
    .attr('stroke-width', 1.4)
    .attr('stroke-opacity', 0.42)
    .attr('marker-end', d => {
      const tgtNode = nodeByName.get(d.target)
      return `url(#arrow-${tgtNode?.type || 'default'})`
    })
    .style('cursor', 'pointer')

  // 大图谱时不渲染连线文字标签，避免大量 <text> 拖垮性能
  const linkLabelGroup = g.append('g').attr('class', 'link-labels')
  const linkLabels = bigGraph
    ? linkLabelGroup.selectAll('text')
    : linkLabelGroup.selectAll('text').data(links).join('text')
        .text(d => d.type)
        .attr('font-size', 10)
        .attr('fill', '#64748b')
        .attr('text-anchor', 'middle')
        .attr('dy', -4)
        .style('pointer-events', 'none')
        .style('opacity', 0.72)

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
    .attr('r', d => d.radius + 8)
    .attr('fill', d => (TYPE_COLORS[d.type] || '#64748b') + '14')
    .attr('stroke', d => (TYPE_COLORS[d.type] || '#64748b') + '22')
    .attr('stroke-width', 1)
    .attr('pointer-events', 'none')

  nodeG.append('circle')
    .attr('class', 'node-core')
    .attr('r', d => d.radius)
    .attr('fill', '#ffffff')
    .attr('stroke', d => TYPE_COLORS[d.type] || '#64748b')
    .attr('stroke-width', 2.2)
    .style('transition', 'all 0.3s ease')

  nodeG.append('text')
    .text(d => getTypeLabel(d.type))
    .attr('text-anchor', 'middle')
    .attr('dy', 5)
    .attr('font-size', d => Math.max(11, Math.min(16, d.radius - 4)))
    .attr('font-weight', 700)
    .attr('fill', d => TYPE_COLORS[d.type] || '#64748b')
    .attr('pointer-events', 'none')

  nodeG.append('text')
    .attr('class', 'node-name')
    .text(d => d.name.length > 8 ? d.name.slice(0, 8) + '..' : d.name)
    .attr('text-anchor', 'middle')
    .attr('dy', d => d.radius + 14)
    .attr('font-size', 11)
    .attr('font-weight', 600)
    .attr('fill', '#334155')
    .attr('paint-order', 'stroke')
    .attr('stroke', '#fff')
    .attr('stroke-width', 4)
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

function toggleRightPanel() {
  rightPanelCollapsed.value = !rightPanelCollapsed.value
  scheduleRender(260)
}

async function deleteEntity(entity) {
  if (!confirm(`确定删除实体「${entity.name}」？该实体的所有关系也将被删除。`)) return
  try {
    await request.delete(`/graph/entities/${entity.id}`)
    ElMessage.success('实体已删除')
    if (selectedEntity.value?.id === entity.id) selectedEntity.value = null
    loadGraph()
  } catch (err) {
    ElMessage.error('删除失败: ' + (err?.response?.data?.message || err.message || '网络错误'))
  }
}

async function deleteRelation(rel) {
  if (!confirm(`确定删除关系「${rel.source} → ${rel.relation_type} → ${rel.target}」？`)) return
  try {
    await request.delete('/graph/relations', { params: { source: rel.source, target: rel.target, relation_type: rel.relation_type } })
    ElMessage.success('关系已删除')
    loadGraph()
  } catch (err) {
    ElMessage.error('删除失败: ' + (err?.response?.data?.message || err.message || '网络错误'))
  }
}

function zoomIn() {
  if (!svg || !zoomBehavior) return
  svg.interrupt().transition().duration(180).call(zoomBehavior.scaleBy, 1.3)
}
function zoomOut() {
  if (!svg || !zoomBehavior) return
  svg.interrupt().transition().duration(180).call(zoomBehavior.scaleBy, 0.7)
}
function resetZoom() {
  if (!svg || !zoomBehavior) return
  svg.interrupt().transition().duration(180).call(zoomBehavior.transform, d3.zoomIdentity)
}
function fitToView() {
  if (!svg || !zoomBehavior || !graphRef.value) return
  const width = graphRef.value.clientWidth
  const height = graphRef.value.clientHeight || 500
  svg.interrupt().transition().duration(180).call(
    zoomBehavior.transform,
    d3.zoomIdentity.translate(width / 2, height / 2).scale(0.8).translate(-width / 2, -height / 2)
  )
}

async function submitEntity() {
  try {
    await request.post('/graph/entities', newEntity.value)
    ElMessage.success('实体创建成功')
    showAddEntity.value = false
    newEntity.value = { name: '', entity_type: 'Product', description: '' }
    loadGraph()
  } catch (err) {
    ElMessage.error('创建实体失败: ' + (err?.response?.data?.message || err.message || '网络错误'))
  }
}

async function submitRelation() {
  try {
    await request.post('/graph/relations', newRelation.value)
    ElMessage.success('关系创建成功')
    showAddRelation.value = false
    newRelation.value = { source: '', target: '', relation_type: '包含', description: '' }
    loadGraph()
  } catch (err) {
    ElMessage.error('创建关系失败: ' + (err?.response?.data?.message || err.message || '网络错误'))
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
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  min-height: 0;
  background: #f6f8fb;
}

.graph-layout {
  display: flex;
  gap: 16px;
  flex: 1;
  overflow: hidden;
  min-height: 0;
  position: relative;
}

/* Graph canvas */
.graph-canvas {
  flex: 1;
  background: #fff;
  border: 1px solid #e7eaf0;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(18, 25, 38, 0.04);
  position: relative;
  overflow: hidden;
  min-width: 0;
}

.graph-svg-container {
  width: 100%;
  height: 100%;
  min-height: 560px;
  background:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    radial-gradient(circle at 28% 22%, rgba(37, 99, 235, 0.08), transparent 32%),
    radial-gradient(circle at 76% 72%, rgba(20, 184, 166, 0.08), transparent 30%),
    #fbfdff;
  background-size: 28px 28px, 28px 28px, 100% 100%, 100% 100%, auto;
}

.kg-svg {
  cursor: grab;
}

.kg-svg:active {
  cursor: grabbing;
}

.graph-tooltip {
  position: absolute;
  padding: 9px 12px;
  background: rgba(15, 23, 42, 0.92);
  color: #fff;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.6;
  pointer-events: none;
  z-index: 100;
  transform: translate(-50%, -130%);
  white-space: nowrap;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.2);
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
  color: #64748b;
  font-size: 13px;
}

.graph-empty {
  flex-direction: column;
  gap: 6px;
}

.empty-title {
  font-size: 15px;
  font-weight: 650;
  color: #334155;
}

.empty-desc {
  color: #7a8494;
}

/* 大图谱折叠提示 */
.graph-truncate-tip {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  max-width: min(560px, calc(100% - 220px));
  z-index: 11;
  padding: 8px 14px;
  font-size: 12px;
  line-height: 1.5;
  color: #92520a;
  background: rgba(254, 243, 224, 0.96);
  border: 1px solid #f6c97a;
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(12px);
  text-align: center;
}

/* Stats overlay */
.graph-stats {
  position: absolute;
  top: 16px;
  left: 16px;
  display: flex;
  gap: 0;
  z-index: 10;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 8px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(12px);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
}

.graph-stat {
  padding: 10px 16px;
  min-width: 82px;
  border-right: 1px solid #eef2f7;
}

.graph-stat:last-child {
  border-right: 0;
}

.graph-stat .num {
  font-size: 19px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.1;
}

.graph-stat .label {
  margin-top: 4px;
  font-size: 11px;
  color: #7a8494;
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
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 8px;
  padding: 10px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(12px);
  z-index: 10;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #edf2f7;
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
  top: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  z-index: 10;
}

.graph-control {
  width: 34px;
  height: 34px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
  transition: background 0.2s, color 0.2s, transform 0.2s;
}

.graph-control:hover {
  background: #eff6ff;
  transform: translateY(-1px);
}

.graph-control svg {
  width: 18px;
  height: 18px;
  fill: #475569;
}

/* Right panel */
.right-panel {
  width: 360px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex-shrink: 0;
  min-height: 0;
  transition: width 0.24s ease, opacity 0.18s ease, transform 0.24s ease;
}

.right-panel.collapsed {
  width: 0;
  opacity: 0;
  transform: translateX(24px);
  pointer-events: none;
  overflow: hidden;
}

.panel-toggle {
  position: absolute;
  top: 50%;
  right: 368px;
  z-index: 20;
  width: 28px;
  height: 56px;
  border: 1px solid #d8dee8;
  border-right-color: #e7eaf0;
  border-radius: 8px 0 0 8px;
  background: rgba(255, 255, 255, 0.94);
  color: #64748b;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.1);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transform: translateY(-50%);
  transition: right 0.24s ease, background 0.2s, color 0.2s;
}

.panel-toggle:hover {
  background: #eff6ff;
  color: #2563eb;
}

.panel-toggle.collapsed {
  right: 0;
  border-radius: 8px 0 0 8px;
}

.panel-toggle svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

.panel-card {
  background: #fff;
  border: 1px solid #e7eaf0;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(18, 25, 38, 0.04);
  min-height: 0;
  overflow: hidden;
}

.panel-header {
  padding: 14px 16px;
  border-bottom: 1px solid #eef2f7;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  font-size: 15px;
  font-weight: 650;
  color: #1f2937;
  margin: 0;
}

.panel-count {
  font-size: 12px;
  color: #7a8494;
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
  background: #f8fafc;
  border-color: #edf2f7;
}

.entity-item.active {
  background: #eff6ff;
  border-color: #bfdbfe;
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
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entity-info .type {
  margin-top: 2px;
  font-size: 11px;
  color: #7a8494;
}

.entity-info .relations {
  margin-top: 2px;
  font-size: 11px;
  color: #2563eb;
}

.type-c0  { background: #ecf5ff; color: #409eff; }
	.type-c1  { background: #fef0f0; color: #f56c6c; }
	.type-c2  { background: #f0f9eb; color: #67c23a; }
	.type-c3  { background: #fdf6ec; color: #e6a23c; }
	.type-c4  { background: #f5f0ff; color: #9b59b6; }
	.type-c5  { background: #e6fffb; color: #36cfc9; }
	.type-c6  { background: #fff2e8; color: #ff7a45; }
	.type-c7  { background: #f0f5ff; color: #597ef7; }
	.type-c8  { background: #f6ffed; color: #73d13d; }
	.type-c9  { background: #fff0f6; color: #ff85c0; }
	.type-c10 { background: #f9f0ff; color: #b37feb; }
	.type-c11 { background: #e6fffb; color: #5cdbd3; }
	.type-c12 { background: #fffbe6; color: #ffc53d; }
	.type-c13 { background: #f9f0ff; color: #9254de; }
	.type-c14 { background: #e6f7ff; color: #40a9ff; }
	.type-c15 { background: #fff1f0; color: #ff4d4f; }

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
  color: #475569;
  flex-wrap: wrap;
}

.relation-item:hover {
  background: #f8fafc;
  border-color: #edf2f7;
}

.relation-item:last-child {
  border-bottom: none;
}

.rel-name {
  font-weight: 650;
  color: #1f2937;
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
  color: #2563eb;
  font-size: 11px;
  background: #eff6ff;
  border: 1px solid #dbeafe;
  padding: 2px 7px;
  border-radius: 999px;
}

.relation-empty {
  text-align: center;
  color: #7a8494;
  font-size: 13px;
  padding: 20px 0;
}

.list-more-tip {
  text-align: center;
  color: #92520a;
  background: #fff7ed;
  border: 1px dashed #f6c97a;
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
  background: rgba(15, 23, 42, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #fff;
  border-radius: 8px;
  width: 480px;
  border: 1px solid #e7eaf0;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.24);
}

.modal-header {
  padding: 18px 20px;
  border-bottom: 1px solid #eef2f7;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 650;
  color: #1f2937;
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
  fill: #475569;
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
  color: #475569;
  margin-bottom: 6px;
  font-weight: 500;
}

.form-group label .required {
  color: #f56c6c;
}

.form-input {
  width: 100%;
  height: 36px;
  border: 1px solid #d8dee8;
  border-radius: 6px;
  padding: 0 12px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-select {
  width: 100%;
  height: 36px;
  border: 1px solid #d8dee8;
  border-radius: 6px;
  padding: 0 12px;
  font-size: 13px;
  color: #475569;
  background: #fff;
  outline: none;
  box-sizing: border-box;
}

.form-textarea {
  width: 100%;
  border: 1px solid #d8dee8;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 13px;
  outline: none;
  resize: vertical;
  min-height: 60px;
  font-family: inherit;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.form-textarea:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.modal-footer {
  padding: 14px 20px;
  border-top: 1px solid #eef2f7;
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
  background: #2563eb;
  color: #fff;
}

.btn-primary:hover {
  background: #1d4ed8;
}

.btn-default {
  background: #fff;
  color: #475569;
  border-color: #d8dee8;
}

.btn-default:hover {
  border-color: #2563eb;
  color: #2563eb;
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
  background: #fef0f0;
}

.btn-icon svg {
  width: 16px;
  height: 16px;
  fill: #909399;
}

.btn-icon:hover svg {
  fill: #f56c6c;
}

.btn-delete {
  opacity: 0;
  transition: opacity 0.2s;
}

.entity-item:hover .btn-delete {
  opacity: 1;
}

.btn-delete-sm {
  width: 22px;
  height: 22px;
  margin-left: auto;
}

.btn-delete-sm svg {
  width: 14px;
  height: 14px;
}
</style>
