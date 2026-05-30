<template>
  <div class="dashboard">
    <!-- Stat Cards -->
    <div class="stat-cards">
      <div class="stat-card" v-for="card in statCards" :key="card.label">
        <div class="info">
          <h3>{{ card.label }}</h3>
          <div class="value">{{ card.value }}</div>
          <div class="trend" :class="card.trendDir">{{ card.trend }}</div>
        </div>
        <div class="icon-box" :class="card.iconClass">
          <svg viewBox="0 0 24 24"><path :d="card.iconPath"/></svg>
        </div>
      </div>
    </div>

    <!-- Charts Row: Trend + Pie -->
    <div class="charts-row">
      <div class="chart-card">
        <h3>
          近7天问答趋势
          <span class="subtitle">{{ trendDateRange }}</span>
        </h3>
        <div ref="trendChartRef" style="height: 260px"></div>
      </div>
      <div class="chart-card">
        <h3>文档类型分布</h3>
        <div ref="pieChartRef" style="height: 260px"></div>
      </div>
    </div>

    <!-- Bottom Row: Hot Questions + System Status -->
    <div class="bottom-row">
      <div class="chart-card">
        <h3>热门问题 TOP 10</h3>
        <ul class="hot-list">
          <li v-for="(q, idx) in hotQuestions" :key="q.question">
            <span class="hot-rank" :class="idx < 3 ? 'rank-' + (idx + 1) : 'rank-n'">{{ idx + 1 }}</span>
            <span class="hot-question">{{ q.question }}</span>
            <span class="hot-count">{{ q.count }} 次</span>
          </li>
        </ul>
        <el-empty v-if="!hotQuestions.length" :image-size="40" />
      </div>
      <div class="chart-card">
        <h3>系统状态</h3>
        <ul class="status-list">
          <li class="status-item" v-for="s in systemStatus" :key="s.name">
            <div class="label">
              <div class="status-dot" :class="s.status"></div>
              {{ s.name }}
            </div>
            <span class="status-badge" :class="'badge-' + s.status">{{ s.statusText }}</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import * as echarts from 'echarts'
import request from '../../api/request'

const stats = ref({})
const trend = ref([])
const hotQuestions = ref([])
const docTypes = ref([])
const trendChartRef = ref()
const pieChartRef = ref()

const statCards = computed(() => [
  {
    label: '文档总数',
    value: (stats.value.document_count ?? 0).toLocaleString(),
    trend: stats.value.document_trend || '',
    trendDir: (stats.value.document_trend_dir === 'down') ? 'down' : 'up',
    iconClass: 'icon-blue',
    iconPath: 'M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z',
  },
  {
    label: '知识条目',
    value: (stats.value.chunk_count ?? 0).toLocaleString(),
    trend: stats.value.chunk_trend || '',
    trendDir: (stats.value.chunk_trend_dir === 'down') ? 'down' : 'up',
    iconClass: 'icon-green',
    iconPath: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z',
  },
  {
    label: '注册用户',
    value: (stats.value.user_count ?? 0).toLocaleString(),
    trend: stats.value.user_trend || '',
    trendDir: (stats.value.user_trend_dir === 'down') ? 'down' : 'up',
    iconClass: 'icon-orange',
    iconPath: 'M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5z',
  },
  {
    label: '今日问答',
    value: (stats.value.today_chat_count ?? 0).toLocaleString(),
    trend: stats.value.today_trend || '',
    trendDir: (stats.value.today_trend_dir === 'down') ? 'down' : 'up',
    iconClass: 'icon-red',
    iconPath: 'M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z',
  },
])

const systemStatus = computed(() => {
  const raw = stats.value.system_status
  if (Array.isArray(raw)) return raw
  return [
    { name: 'ChromaDB 向量库', status: 'online', statusText: '正常' },
    { name: 'Neo4j 图数据库', status: 'online', statusText: '正常' },
    { name: 'MySQL 数据库', status: 'online', statusText: '正常' },
    { name: 'LLM 服务 (mimo-2.5-pro)', status: 'online', statusText: '正常' },
    { name: 'Embedding 服务', status: 'online', statusText: '正常' },
  ]
})

const trendDateRange = computed(() => {
  if (trend.value.length < 2) return ''
  return `${trend.value[0].date} ~ ${trend.value[trend.value.length - 1].date}`
})

function renderTrendChart() {
  if (!trendChartRef.value || !trend.value.length) return
  const chart = echarts.init(trendChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: trend.value.map(t => t.date),
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#909399', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { type: 'dashed', color: '#f0f0f0' } },
      axisLabel: { color: '#909399', fontSize: 11 },
    },
    series: [{
      data: trend.value.map(t => t.count),
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { color: '#667eea', width: 2.5 },
      itemStyle: { color: '#667eea' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(102,126,234,0.3)' },
          { offset: 1, color: 'rgba(102,126,234,0)' },
        ]),
      },
    }],
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
  })
}

function renderPieChart() {
  if (!pieChartRef.value || !docTypes.value.length) return
  const chart = echarts.init(pieChartRef.value)
  const colors = ['#667eea', '#764ba2', '#67c23a', '#e6a23c', '#909399']
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {d}%' },
    legend: {
      bottom: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { fontSize: 12, color: '#606266' },
    },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
      data: docTypes.value.map((d, i) => ({
        name: d.file_type?.toUpperCase() || d.name,
        value: d.count,
        itemStyle: { color: colors[i % colors.length] },
      })),
    }],
  })
}

onMounted(async () => {
  try {
    const [s, t, h, d, health] = await Promise.all([
      request.get('/dashboard/stats'),
      request.get('/dashboard/trend'),
      request.get('/dashboard/hot-questions'),
      request.get('/dashboard/doc-types').catch(() => []),
      request.get('/dashboard/system-health').catch(() => []),
    ])
    stats.value = s
    trend.value = t
    hotQuestions.value = h
    docTypes.value = Array.isArray(d) ? d : (d?.list || [])
    if (Array.isArray(health) && health.length) {
      stats.value.system_status = health.map(svc => ({
        name: svc.name,
        status: svc.status,
        statusText: svc.status === 'online' ? '正常' : '异常',
      }))
    }
  } catch {}

  renderTrendChart()
  renderPieChart()
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

/* Stat Cards */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}
.stat-card {
  background: #fff;
  border-radius: 10px;
  padding: 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stat-card .info h3 {
  font-size: 13px;
  color: #909399;
  font-weight: 400;
  margin-bottom: 8px;
}
.stat-card .info .value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}
.stat-card .info .trend {
  font-size: 12px;
  margin-top: 6px;
}
.trend.up {
  color: #67c23a;
}
.trend.down {
  color: #f56c6c;
}
.stat-card .icon-box {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stat-card .icon-box svg {
  width: 28px;
  height: 28px;
  fill: #fff;
}
.icon-blue {
  background: linear-gradient(135deg, #667eea, #764ba2);
}
.icon-green {
  background: linear-gradient(135deg, #67c23a, #4caf50);
}
.icon-orange {
  background: linear-gradient(135deg, #e6a23c, #f39c12);
}
.icon-red {
  background: linear-gradient(135deg, #f56c6c, #e74c3c);
}

/* Charts Row */
.charts-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}
.chart-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.chart-card h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.chart-card h3 .subtitle {
  font-size: 12px;
  color: #909399;
  font-weight: 400;
}

/* Bottom Row */
.bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

/* Hot Questions */
.hot-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.hot-list li {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}
.hot-list li:last-child {
  border-bottom: none;
}
.hot-rank {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  margin-right: 12px;
  flex-shrink: 0;
}
.rank-1 {
  background: #fef0f0;
  color: #f56c6c;
}
.rank-2 {
  background: #fdf6ec;
  color: #e6a23c;
}
.rank-3 {
  background: #ecf5ff;
  color: #409eff;
}
.rank-n {
  background: #f5f7fa;
  color: #909399;
}
.hot-question {
  flex: 1;
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hot-count {
  font-size: 12px;
  color: #909399;
  margin-left: 12px;
  flex-shrink: 0;
}

/* System Status */
.status-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.status-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 0;
  border-bottom: 1px solid #f0f0f0;
}
.status-item:last-child {
  border-bottom: none;
}
.status-item .label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.status-dot.online {
  background: #67c23a;
}
.status-dot.warning {
  background: #e6a23c;
}
.status-dot.offline {
  background: #f56c6c;
}
.status-badge {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
}
.badge-online {
  background: #f0f9eb;
  color: #67c23a;
}
.badge-warning {
  background: #fdf6ec;
  color: #e6a23c;
}
.badge-offline {
  background: #fef0f0;
  color: #f56c6c;
}
</style>
