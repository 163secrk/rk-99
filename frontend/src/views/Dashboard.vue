<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h2><el-icon><DataAnalysis /></el-icon> 审计分析看板</h2>
      <div class="header-actions">
        <el-select v-model="selectedDays" size="default" style="width: 140px;" @change="fetchStatistics">
          <el-option label="最近7天" :value="7" />
          <el-option label="最近15天" :value="15" />
          <el-option label="最近30天" :value="30" />
        </el-select>
        <el-button type="primary" style="margin-left: 10px;" @click="fetchStatistics">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <el-row :gutter="16" class="stats-cards">
      <el-col :span="6">
        <el-card class="stat-card total-card" shadow="hover">
          <div class="stat-icon">
            <el-icon :size="32"><TrendCharts /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ statistics.total_queries || 0 }}</div>
            <div class="stat-label">总查询次数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card success-card" shadow="hover">
          <div class="stat-icon">
            <el-icon :size="32"><CircleCheck /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ statistics.success_queries || 0 }}</div>
            <div class="stat-label">成功执行</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card blocked-card" shadow="hover">
          <div class="stat-icon">
            <el-icon :size="32"><Warning /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ statistics.blocked_queries || 0 }}</div>
            <div class="stat-label">风险拦截</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card failed-card" shadow="hover">
          <div class="stat-icon">
            <el-icon :size="32"><CircleClose /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ statistics.failed_queries || 0 }}</div>
            <div class="stat-label">执行失败</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="charts-row">
      <el-col :span="14">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span class="card-title">查询趋势</span>
            </div>
          </template>
          <div ref="trendChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span class="card-title">风险拦截分布</span>
            </div>
          </template>
          <div ref="pieChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="charts-row">
      <el-col :span="10">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span class="card-title">高频查询用户排名</span>
            </div>
          </template>
          <div ref="barChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="14">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span class="card-title">各数据源查询量对比</span>
            </div>
          </template>
          <div ref="datasourceChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { DataAnalysis, Refresh, TrendCharts, CircleCheck, Warning, CircleClose } from '@element-plus/icons-vue'
import { auditApi } from '@/api'
import * as echarts from 'echarts'

const selectedDays = ref(7)
const statistics = ref({})
const loading = ref(false)

const trendChartRef = ref(null)
const pieChartRef = ref(null)
const barChartRef = ref(null)
const datasourceChartRef = ref(null)

let trendChart = null
let pieChart = null
let barChart = null
let datasourceChart = null

const fetchStatistics = async () => {
  loading.value = true
  try {
    const res = await auditApi.getStatistics({ days: selectedDays.value })
    statistics.value = res
    await nextTick()
    renderCharts()
  } catch (e) {
    ElMessage.error('获取统计数据失败')
  } finally {
    loading.value = false
  }
}

const renderCharts = () => {
  renderTrendChart()
  renderPieChart()
  renderBarChart()
  renderDatasourceChart()
}

const renderTrendChart = () => {
  if (!trendChartRef.value) return
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }
  const dates = (statistics.value.query_trend || []).map(item => item.date)
  const counts = (statistics.value.query_trend || []).map(item => item.count)

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e4e7ed',
      borderWidth: 1,
      textStyle: {
        color: '#303133'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLine: {
        lineStyle: {
          color: '#dcdfe6'
        }
      },
      axisLabel: {
        color: '#606266',
        fontSize: 12
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        show: false
      },
      axisTick: {
        show: false
      },
      splitLine: {
        lineStyle: {
          color: '#f0f2f5'
        }
      },
      axisLabel: {
        color: '#606266',
        fontSize: 12
      }
    },
    series: [
      {
        name: '查询次数',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        data: counts,
        lineStyle: {
          width: 3,
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: '#667eea' },
              { offset: 1, color: '#764ba2' }
            ]
          }
        },
        itemStyle: {
          color: '#667eea',
          borderColor: '#fff',
          borderWidth: 2
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(102, 126, 234, 0.3)' },
              { offset: 1, color: 'rgba(102, 126, 234, 0.05)' }
            ]
          }
        }
      }
    ]
  }
  trendChart.setOption(option)
}

const renderPieChart = () => {
  if (!pieChartRef.value) return
  if (!pieChart) {
    pieChart = echarts.init(pieChartRef.value)
  }
  const data = statistics.value.risk_distribution || []

  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e4e7ed',
      borderWidth: 1,
      textStyle: {
        color: '#303133'
      },
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
      textStyle: {
        color: '#606266',
        fontSize: 13
      }
    },
    series: [
      {
        name: '查询分布',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold',
            formatter: '{b}\n{c}次'
          }
        },
        labelLine: {
          show: false
        },
        data: data.map((item, index) => ({
          value: item.value,
          name: item.name,
          itemStyle: {
            color: ['#67c23a', '#f56c6c', '#e6a23c'][index]
          }
        }))
      }
    ]
  }
  pieChart.setOption(option)
}

const renderBarChart = () => {
  if (!barChartRef.value) return
  if (!barChart) {
    barChart = echarts.init(barChartRef.value)
  }
  const users = (statistics.value.top_users || []).map(item => item.username)
  const counts = (statistics.value.top_users || []).map(item => item.count)

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e4e7ed',
      borderWidth: 1,
      textStyle: {
        color: '#303133'
      },
      axisPointer: {
        type: 'shadow'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '5%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      axisLine: {
        show: false
      },
      axisTick: {
        show: false
      },
      splitLine: {
        lineStyle: {
          color: '#f0f2f5'
        }
      },
      axisLabel: {
        color: '#606266',
        fontSize: 12
      }
    },
    yAxis: {
      type: 'category',
      data: users.reverse(),
      axisLine: {
        lineStyle: {
          color: '#dcdfe6'
        }
      },
      axisTick: {
        show: false
      },
      axisLabel: {
        color: '#606266',
        fontSize: 12
      }
    },
    series: [
      {
        name: '查询次数',
        type: 'bar',
        data: counts.reverse(),
        barWidth: '50%',
        itemStyle: {
          borderRadius: [0, 4, 4, 0],
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: '#409eff' },
              { offset: 1, color: '#66b1ff' }
            ]
          }
        }
      }
    ]
  }
  barChart.setOption(option)
}

const renderDatasourceChart = () => {
  if (!datasourceChartRef.value) return
  if (!datasourceChart) {
    datasourceChart = echarts.init(datasourceChartRef.value)
  }
  const names = (statistics.value.datasource_stats || []).map(item => item.name)
  const counts = (statistics.value.datasource_stats || []).map(item => item.count)

  const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#43e97b', '#fa709a', '#fee140']

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e4e7ed',
      borderWidth: 1,
      textStyle: {
        color: '#303133'
      },
      axisPointer: {
        type: 'shadow'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '5%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: names,
      axisLine: {
        lineStyle: {
          color: '#dcdfe6'
        }
      },
      axisTick: {
        show: false
      },
      axisLabel: {
        color: '#606266',
        fontSize: 11,
        rotate: names.length > 5 ? 30 : 0,
        interval: 0
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        show: false
      },
      axisTick: {
        show: false
      },
      splitLine: {
        lineStyle: {
          color: '#f0f2f5'
        }
      },
      axisLabel: {
        color: '#606266',
        fontSize: 12
      }
    },
    series: [
      {
        name: '查询量',
        type: 'bar',
        data: counts.map((value, index) => ({
          value,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: colors[index % colors.length] },
                { offset: 1, color: colors[(index + 1) % colors.length] + '99' }
              ]
            },
            borderRadius: [4, 4, 0, 0]
          }
        })),
        barWidth: '50%'
      }
    ]
  }
  datasourceChart.setOption(option)
}

const handleResize = () => {
  trendChart && trendChart.resize()
  pieChart && pieChart.resize()
  barChart && barChart.resize()
  datasourceChart && datasourceChart.resize()
}

onMounted(() => {
  fetchStatistics()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart && trendChart.dispose()
  pieChart && pieChart.dispose()
  barChart && barChart.dispose()
  datasourceChart && datasourceChart.dispose()
})
</script>

<style scoped>
.dashboard-page {
  max-width: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.page-header h2 {
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  color: #303133;
}

.header-actions {
  display: flex;
  align-items: center;
}

.stats-cards {
  margin-bottom: 16px;
}

.stat-card {
  border: none;
  border-radius: 12px;
  overflow: hidden;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  padding: 20px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  flex-shrink: 0;
}

.total-card .stat-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.success-card .stat-icon {
  background: linear-gradient(135deg, #67c23a 0%, #95d475 100%);
  color: #fff;
}

.blocked-card .stat-icon {
  background: linear-gradient(135deg, #f56c6c 0%, #f89898 100%);
  color: #fff;
}

.failed-card .stat-icon {
  background: linear-gradient(135deg, #e6a23c 0%, #f0c78a 100%);
  color: #fff;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

.charts-row {
  margin-bottom: 16px;
}

.chart-card {
  border-radius: 12px;
  border: none;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.chart-container {
  width: 100%;
  height: 320px;
}

:deep(.el-card__header) {
  padding: 14px 20px;
  border-bottom: 1px solid #f0f2f5;
}

:deep(.el-card__body) {
  padding: 16px 20px;
}
</style>
