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

        <!-- D3 graph container -->
        <div ref="graphRef" class="graph-svg-container"></div>

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
      <div class="right-panel">
        <!-- Entity list card -->
        <div class="panel-card">
          <div class="panel-header">
            <h3>实体列表</h3>
            <span class="panel-count">共 {{ entityCount.toLocaleString() }} 个</span>
          </div>
          <div class="panel-body">
            <ul class="entity-list">
              <li
                v-for="entity in entities"
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
              <li v-for="(rel, idx) in filteredRelations" :key="idx" class="relation-item">
                <span class="rel-name">{{ getEntityName(rel.source) }}</span>
                <span class="relation-arrow">→</span>
                <span class="relation-label">{{ rel.relation_type }}</span>
                <span class="relation-arrow">→</span>
                <span class="rel-name">{{ getEntityName(rel.target) }}</span>
                <button class="btn-icon btn-delete-sm" @click.stop="deleteRelation(rel)" title="删除关系">
                  <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 19 19 17.59 13.41 12z"/></svg>
                </button>
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
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as d3 from 'd3'
import GraphToolbar from '../../components/graph/GraphToolbar.vue'
import request from '../../api/request'

const graphRef = ref()
const selectedEntity = ref(null)
const typeFilter = ref('')
const entities = ref([])
const relations = ref([])
const showAddEntity = ref(false)
const showAddRelation = ref(false)
const loading = ref(false)

let simulation = null
let svg = null
let zoomBehavior = null

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
  const e = entities.value.find(e => e.id === idOrName || e.name === idOrName)
  return e ? e.name : idOrName
}

function getEntityRelationCount(entityId) {
  const entity = entities.value.find(e => e.id === entityId)
  if (!entity) return 0
  const name = entity.name
  return relations.value.filter(r => r.source === name || r.target === name || r.source_id === entityId || r.target_id === entityId).length
}

async function loadGraph(query = '') {
  loading.value = true
  try {
    const [entRes, relRes] = await Promise.all([
      request.get('/graph/entities', { params: { q: query || undefined, limit: 1000, entity_type: typeFilter.value || undefined } }),
      request.get('/graph/relations', { params: { limit: 1000 } }),
    ])
    entities.value = Array.isArray(entRes) ? entRes : (entRes.data || [])
    relations.value = Array.isArray(relRes) ? relRes : (relRes.data || [])
    assignTypeStyles()
    renderGraph()
  } catch (err) {
    ElMessage.error('加载知识图谱失败: ' + (err?.response?.data?.message || err.message || '网络错误'))
  } finally {
    loading.value = false
  }
}

function renderGraph() {
  if (!graphRef.value) return

  if (simulation) {
    simulation.stop()
    simulation = null
  }
  graphRef.value.innerHTML = ''

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
      .attr('fill', c)
      .attr('opacity', 0.6)
  }

  defs.append('marker')
    .attr('id', 'arrow-default')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 24).attr('refY', 0)
    .attr('markerWidth', 7).attr('markerHeight', 7)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#909399')
    .attr('opacity', 0.5)

  const g = svg.append('g')

  zoomBehavior = d3.zoom()
    .scaleExtent([0.15, 5])
    .on('zoom', (event) => g.attr('transform', event.transform))
  svg.call(zoomBehavior)

  // ---- build graph data ----
  const connCount = {}
  const nameToId = {}
  for (const e of entities.value) {
    connCount[e.name] = 0
    nameToId[e.name] = e.id
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

  // Deduplicate links by source+target+type
  const linkMap = new Map()
  for (const r of relations.value) {
    const key = `${r.source}::${r.target}::${r.relation_type || r.rel}`
    if (!linkMap.has(key)) linkMap.set(key, r)
  }
  const links = Array.from(linkMap.values()).map(r => ({
    source: r.source, target: r.target, type: r.relation_type || r.rel || '关联',
  }))

  // ---- links (paths with arrowheads) ----
  const linkGroup = g.append('g').attr('class', 'links')
  const linkPaths = linkGroup.selectAll('line').data(links).join('line')
    .attr('stroke', d => {
      const tgtNode = nodes.find(n => n.name === d.target)
      return TYPE_COLORS[tgtNode?.type] || '#909399'
    })
    .attr('stroke-width', 1.5)
    .attr('stroke-opacity', 0.35)
    .attr('marker-end', d => {
      const tgtNode = nodes.find(n => n.name === d.target)
      return `url(#arrow-${tgtNode?.type || 'default'})`
    })
    .style('cursor', 'pointer')

  const linkLabelGroup = g.append('g').attr('class', 'link-labels')
  const linkLabels = linkLabelGroup.selectAll('text').data(links).join('text')
    .text(d => d.type)
    .attr('font-size', 10)
    .attr('fill', '#909399')
    .attr('text-anchor', 'middle')
    .attr('dy', -4)
    .style('pointer-events', 'none')
    .style('opacity', 0.7)

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
      d3.select(this).select('circle').transition().duration(200).attr('filter', 'url(#shadow)')
      tooltip.style('opacity', 1).html(`<b>${d.name}</b><br><span style="opacity:.7">${getTypeName(d.type)} · ${d.connections} 个关系</span>`)
    })
    .on('mousemove', function(event) {
      const [mx, my] = d3.pointer(event, graphRef.value)
      tooltip.style('left', mx + 'px').style('top', (my - 10) + 'px')
    })
    .on('mouseleave', function() {
      d3.select(this).select('circle').transition().duration(200).attr('filter', null)
      tooltip.style('opacity', 0)
    })

  nodeG.append('circle')
    .attr('r', d => d.radius)
    .attr('fill', d => (TYPE_COLORS[d.type] || '#909399') + '22')
    .attr('stroke', d => TYPE_COLORS[d.type] || '#909399')
    .attr('stroke-width', 2.5)
    .style('transition', 'all 0.3s ease')

  nodeG.append('text')
    .text(d => d.name.length > 8 ? d.name.slice(0, 8) + '..' : d.name)
    .attr('text-anchor', 'middle')
    .attr('dy', d => d.radius + 14)
    .attr('font-size', 11)
    .attr('font-weight', 500)
    .attr('fill', d => TYPE_COLORS[d.type] || '#606266')
    .attr('pointer-events', 'none')

  // ---- tooltip ----
  const tooltip = d3.select(graphRef.value).append('div')
    .attr('class', 'graph-tooltip')
    .style('opacity', 0)

  // ---- force simulation ----
  const nodeCount = nodes.length
  // Dynamic spacing: more nodes → longer links, stronger repulsion
  const linkDist = Math.max(120, Math.min(280, 600 / Math.sqrt(nodeCount || 1)))
  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.name).distance(linkDist).strength(0.25))
    .force('charge', d3.forceManyBody().strength(d => -400 - d.radius * 12))
    .force('center', d3.forceCenter(width / 2, height / 2).strength(0.03))
    .force('x', d3.forceX(width / 2).strength(0.015))
    .force('y', d3.forceY(height / 2).strength(0.015))
    .force('collision', d3.forceCollide().radius(d => d.radius + 14).strength(0.9))
    .alphaDecay(0.015)
    .velocityDecay(0.35)

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
}

// ---- Highlight / Dim ----
let highlightedNode = null
function highlightNode(d) {
  highlightedNode = d
  selectedEntity.value = entities.value.find(e => e.id === d.id) || d

  const connectedNames = new Set()
  for (const r of relations.value) {
    if (r.source === d.name) connectedNames.add(r.target)
    if (r.target === d.name) connectedNames.add(r.source)
  }
  connectedNames.add(d.name)

  const nodeSel = d3.select('g.nodes').selectAll('g')
  const linkSel = d3.select('g.links').selectAll('line')
  const labelSel = d3.select('g.link-labels').selectAll('text')

  nodeSel.select('circle')
    .transition().duration(400)
    .attr('stroke-opacity', n => connectedNames.has(n.name) ? 1 : 0.1)
    .attr('opacity', n => connectedNames.has(n.name) ? 1 : 0.2)

  nodeSel.select('text')
    .transition().duration(400)
    .attr('opacity', n => connectedNames.has(n.name) ? 1 : 0.15)

  linkSel
    .transition().duration(400)
    .attr('stroke-opacity', r => {
      return (r.source.name === d.name || r.target.name === d.name) ? 0.8 : 0.05
    })
    .attr('stroke-width', r => {
      return (r.source.name === d.name || r.target.name === d.name) ? 3 : 1.5
    })

  labelSel
    .transition().duration(400)
    .style('opacity', r => {
      return (r.source.name === d.name || r.target.name === d.name) ? 1 : 0.05
    })
    .attr('font-weight', r => {
      return (r.source.name === d.name || r.target.name === d.name) ? 700 : 400
    })
}

function resetHighlight() {
  highlightedNode = null
  selectedEntity.value = null

  d3.select('g.nodes').selectAll('g').select('circle')
    .transition().duration(400)
    .attr('stroke-opacity', 1).attr('opacity', 1)
  d3.select('g.nodes').selectAll('g').select('text')
    .transition().duration(400)
    .attr('opacity', 1)
  d3.select('g.links').selectAll('line')
    .transition().duration(400)
    .attr('stroke-opacity', 0.35).attr('stroke-width', 1.5)
  d3.select('g.link-labels').selectAll('text')
    .transition().duration(400)
    .style('opacity', 0.7).attr('font-weight', 400)
}

function dragStarted(event) {
  if (!event.active) simulation.alphaTarget(0.3).restart()
  event.subject.fx = event.subject.x
  event.subject.fy = event.subject.y
}
function dragged(event) {
  event.subject.fx = event.x
  event.subject.fy = event.y
}
function dragEnded(event) {
  if (!event.active) simulation.alphaTarget(0)
  event.subject.fx = null
  event.subject.fy = null
}

function handleSearch(q) { loadGraph(q) }

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
  svg?.transition().duration(300).call(zoomBehavior.scaleBy, 1.3)
}
function zoomOut() {
  svg?.transition().duration(300).call(zoomBehavior.scaleBy, 0.7)
}
function resetZoom() {
  svg?.transition().duration(300).call(zoomBehavior.transform, d3.zoomIdentity)
}
function fitToView() {
  if (!svg || !graphRef.value) return
  const width = graphRef.value.clientWidth
  const height = graphRef.value.clientHeight || 500
  svg.transition().duration(300).call(
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

onMounted(() => loadGraph())
</script>

<style scoped>
.knowledge-graph-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.graph-layout {
  display: flex;
  gap: 20px;
  flex: 1;
  overflow: hidden;
}

/* Graph canvas */
.graph-canvas {
  flex: 1;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  position: relative;
  overflow: hidden;
}

.graph-svg-container {
  width: 100%;
  height: 100%;
}

.kg-svg {
  cursor: grab;
}

.kg-svg:active {
  cursor: grabbing;
}

.graph-tooltip {
  position: absolute;
  padding: 8px 14px;
  background: rgba(30, 30, 30, 0.92);
  color: #fff;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
  pointer-events: none;
  z-index: 100;
  transform: translate(-50%, -130%);
  white-space: nowrap;
  box-shadow: 0 4px 16px rgba(0,0,0,0.2);
}

/* Stats overlay */
.graph-stats {
  position: absolute;
  top: 16px;
  left: 16px;
  display: flex;
  gap: 12px;
  z-index: 10;
}

.graph-stat {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  padding: 10px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.graph-stat .num {
  font-size: 20px;
  font-weight: 700;
  color: #667eea;
}

.graph-stat .label {
  font-size: 11px;
  color: #909399;
}

/* Legend */
.graph-legend {
  position: absolute;
  bottom: 16px;
  left: 16px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 10;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #606266;
}

.legend-item:last-child {
  margin-bottom: 0;
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
  gap: 4px;
  z-index: 10;
}

.graph-control {
  width: 36px;
  height: 36px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: background 0.2s;
}

.graph-control:hover {
  background: #ecf5ff;
}

.graph-control svg {
  width: 18px;
  height: 18px;
  fill: #606266;
}

/* Right panel */
.right-panel {
  width: 340px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  flex-shrink: 0;
}

.panel-card {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.panel-count {
  font-size: 12px;
  color: #909399;
}

.panel-body {
  padding: 16px 20px;
  max-height: 300px;
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
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background 0.2s;
}

.entity-item:hover {
  background: #f5f7fa;
  margin: 0 -20px;
  padding: 10px 20px;
}

.entity-item.active {
  background: #ecf5ff;
  margin: 0 -20px;
  padding: 10px 20px;
}

.entity-item:last-child {
  border-bottom: none;
}

.entity-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
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
  font-weight: 500;
  color: #303133;
}

.entity-info .type {
  font-size: 11px;
  color: #909399;
}

.entity-info .relations {
  font-size: 11px;
  color: #667eea;
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
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
}

.relation-item:last-child {
  border-bottom: none;
}

.rel-name {
  font-weight: 500;
  color: #303133;
}

.relation-arrow {
  color: #667eea;
  font-weight: 600;
}

.relation-label {
  color: #909399;
  font-size: 11px;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
}

.relation-empty {
  text-align: center;
  color: #909399;
  font-size: 13px;
  padding: 20px 0;
}

/* Modals */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #fff;
  border-radius: 12px;
  width: 480px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.modal-close {
  width: 24px;
  height: 24px;
  cursor: pointer;
  fill: #909399;
  transition: fill 0.2s;
}

.modal-close:hover {
  fill: #606266;
}

.modal-body {
  padding: 24px;
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
  color: #606266;
  margin-bottom: 6px;
  font-weight: 500;
}

.form-group label .required {
  color: #f56c6c;
}

.form-input {
  width: 100%;
  height: 36px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 0 12px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: #667eea;
}

.form-select {
  width: 100%;
  height: 36px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 0 12px;
  font-size: 13px;
  color: #606266;
  background: #fff;
  outline: none;
  box-sizing: border-box;
}

.form-textarea {
  width: 100%;
  border: 1px solid #dcdfe6;
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
  border-color: #667eea;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #ebeef5;
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
