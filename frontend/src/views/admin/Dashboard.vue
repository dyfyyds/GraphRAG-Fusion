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
              <div class="status-copy">
                <span>{{ s.name }}</span>
                <small v-if="s.detail">{{ s.detail }}</small>
              </div>
            </div>
            <span class="status-badge" :class="'badge-' + s.status">{{ s.statusText }}</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { ElEmpty } from 'element-plus'
import * as echarts from 'echarts/core'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import request from '../../api/request'

echarts.use([LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const stats = ref({})
const trend = ref([])
const hotQuestions = ref([])
const docTypes = ref([])
const healthLoading = ref(false)
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
  if (healthLoading.value) {
    return [{
      name: '系统健康检查',
      status: 'warning',
      statusText: '检测中',
      detail: '后台检测服务连接状态',
    }]
  }
  return []
})

const trendDateRange = computed(() => {
  if (trend.value.length < 2) return ''
  return `${trend.value[0].date} ~ ${trend.value[trend.value.length - 1].date}`
})

function renderTrendChart() {
  if (!trendChartRef.value || !trend.value.length) return
  const chart = echarts.init(trendChartRef.value)
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 20, 35, 0.9)',
      borderColor: 'rgba(56, 189, 248, 0.2)',
      textStyle: { color: '#e8ecf4' },
    },
    xAxis: {
      type: 'category',
      data: trend.value.map(t => t.date),
      axisLine: { lineStyle: { color: 'rgba(56, 189, 248, 0.12)' } },
      axisLabel: { color: '#5a6a82', fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { type: 'dashed', color: 'rgba(56, 189, 248, 0.06)' } },
      axisLabel: { color: '#5a6a82', fontSize: 11 },
      axisLine: { show: false },
    },
    series: [{
      data: trend.value.map(t => t.count),
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { color: '#0ea5e9', width: 2.5 },
      itemStyle: { color: '#0ea5e9', borderColor: '#0f1423', borderWidth: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(14, 165, 233, 0.25)' },
          { offset: 1, color: 'rgba(14, 165, 233, 0)' },
        ]),
      },
    }],
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
  })
}

function renderPieChart() {
  if (!pieChartRef.value || !docTypes.value.length) return
  const chart = echarts.init(pieChartRef.value)
  const colors = ['#0ea5e9', '#34d399', '#fbbf24', '#f87171', '#a78bfa']
  chart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {d}%',
      backgroundColor: 'rgba(15, 20, 35, 0.9)',
      borderColor: 'rgba(56, 189, 248, 0.2)',
      textStyle: { color: '#e8ecf4' },
    },
    legend: {
      bottom: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { fontSize: 12, color: '#5a6a82' },
    },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#e8ecf4' },
        itemStyle: { shadowBlur: 20, shadowColor: 'rgba(14, 165, 233, 0.3)' },
      },
      data: docTypes.value.map((d, i) => ({
        name: d.file_type?.toUpperCase() || d.name,
        value: d.count,
        itemStyle: { color: colors[i % colors.length] },
      })),
    }],
  })
}

function renderChartsLater() {
  nextTick(() => {
    requestAnimationFrame(() => {
      renderTrendChart()
      renderPieChart()
    })
  })
}

async function loadSystemHealth() {
  healthLoading.value = true
  try {
    const health = await request.get('/dashboard/system-health')
    if (Array.isArray(health) && health.length) {
      stats.value = {
        ...stats.value,
        system_status: health.map(svc => ({
          name: svc.name,
          status: svc.status,
          statusText: statusTextOf(svc.status),
          detail: svc.detail || '',
        })),
      }
    }
  } catch {
  } finally {
    healthLoading.value = false
  }
}

onMounted(async () => {
  try {
    const overview = await request.get('/dashboard/overview')
    stats.value = overview.stats || {}
    trend.value = overview.trend || []
    hotQuestions.value = overview.hotQuestions || []
    docTypes.value = Array.isArray(overview.docTypes) ? overview.docTypes : []
  } catch {}

  renderChartsLater()
  loadSystemHealth()
})

function statusTextOf(status) {
  if (status === 'online') return '正常'
  if (status === 'warning') return '警告'
  return '异常'
}
</script>

<style scoped>
.dashboard {
  padding: 0;
}

/* Stat Cards */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow-xs);
  display: flex;
  justify-content: space-between;
  align-items: center;
  backdrop-filter: blur(8px);
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}
.stat-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.03), transparent 60%);
  pointer-events: none;
}
.stat-card:hover {
  border-color: var(--color-border-glow);
  box-shadow: var(--shadow-glow);
  transform: translateY(-2px);
}
.stat-card .info h3 {
  font-size: 13px;
  color: var(--color-text-muted);
  font-weight: 550;
  margin-bottom: 8px;
}
.stat-card .info .value {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
}
.stat-card .info .trend {
  font-size: 12px;
  margin-top: 6px;
}
.trend.up {
  color: var(--color-success);
}
.trend.down {
  color: var(--color-danger);
}
.stat-card .icon-box {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 16px rgba(0, 0, 0, 0.3);
}
.stat-card .icon-box svg {
  width: 28px;
  height: 28px;
  fill: #fff;
}
.icon-blue {
  background: linear-gradient(135deg, #0ea5e9, #0369a1);
  box-shadow: 0 0 16px rgba(14, 165, 233, 0.3);
}
.icon-green {
  background: linear-gradient(135deg, #34d399, #059669);
  box-shadow: 0 0 16px rgba(52, 211, 153, 0.3);
}
.icon-orange {
  background: linear-gradient(135deg, #fbbf24, #d97706);
  box-shadow: 0 0 16px rgba(251, 191, 36, 0.3);
}
.icon-red {
  background: linear-gradient(135deg, #f87171, #dc2626);
  box-shadow: 0 0 16px rgba(248, 113, 113, 0.3);
}

/* Charts Row */
.charts-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}
.chart-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 20px;
  box-shadow: var(--shadow-xs);
  min-width: 0;
  backdrop-filter: blur(8px);
}
.chart-card h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--color-text);
}
.chart-card h3 .subtitle {
  font-size: 12px;
  color: var(--color-text-subtle);
  font-weight: 400;
}

/* Bottom Row */
.bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
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
  border-bottom: 1px solid var(--color-border-soft);
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
  background: var(--color-danger-soft);
  color: var(--color-danger);
  box-shadow: 0 0 8px rgba(248, 113, 113, 0.2);
}
.rank-2 {
  background: var(--color-warning-soft);
  color: var(--color-warning);
  box-shadow: 0 0 8px rgba(251, 191, 36, 0.2);
}
.rank-3 {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  box-shadow: 0 0 8px rgba(14, 165, 233, 0.2);
}
.rank-n {
  background: var(--color-surface-muted);
  color: var(--color-text-subtle);
}
.hot-question {
  flex: 1;
  font-size: 13px;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hot-count {
  font-size: 12px;
  color: var(--color-text-subtle);
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
  border-bottom: 1px solid var(--color-border-soft);
}
.status-item:last-child {
  border-bottom: none;
}
.status-item .label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  min-width: 0;
}
.status-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.status-copy span,
.status-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status-copy span {
  color: var(--color-text);
}
.status-copy small {
  color: var(--color-text-subtle);
  font-size: 12px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.online {
  background: var(--color-success);
  box-shadow: 0 0 8px rgba(52, 211, 153, 0.5);
}
.status-dot.warning {
  background: var(--color-warning);
  box-shadow: 0 0 8px rgba(251, 191, 36, 0.5);
}
.status-dot.offline {
  background: var(--color-danger);
  box-shadow: 0 0 8px rgba(248, 113, 113, 0.5);
}
.status-badge {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
}
.badge-online {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.badge-warning {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}
.badge-offline {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

@media (max-width: 1200px) {
  .stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .charts-row,
  .bottom-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .stat-cards {
    grid-template-columns: 1fr;
  }

  .stat-card {
    padding: 16px;
  }
}
</style>
