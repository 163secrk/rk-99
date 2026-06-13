<template>
  <div class="audit-page">
    <div class="page-header">
      <h2><el-icon><Document /></el-icon> 审计日志</h2>
      <div class="filter-bar">
        <el-select
          v-model="filterDsId"
          placeholder="按数据源筛选"
          clearable
          size="default"
          style="width: 240px;"
          @change="onFilterChange"
        >
          <el-option
            v-for="ds in datasources"
            :key="ds.id"
            :label="ds.name"
            :value="ds.id"
          />
        </el-select>
        <el-select
          v-model="filterStatus"
          placeholder="按状态筛选"
          clearable
          size="default"
          style="width: 140px; margin-left: 10px;"
          @change="onFilterChange"
        >
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
        </el-select>
        <el-select
          v-model="filterBlocked"
          placeholder="按拦截状态筛选"
          clearable
          size="default"
          style="width: 160px; margin-left: 10px;"
          @change="onFilterChange"
        >
          <el-option label="已拦截" :value="true" />
          <el-option label="未拦截" :value="false" />
        </el-select>
        <el-button type="primary" style="margin-left: 10px;" @click="fetchLogs">
          <el-icon><Search /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <el-card class="table-card">
      <el-table :data="logs" v-loading="loading" stripe border>
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="datasource_name" label="数据源" min-width="130">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.datasource_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="executed_by" label="执行人" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="primary">{{ row.executed_by || 'anonymous' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="SQL语句" min-width="260">
          <template #default="{ row }">
            <el-tooltip
              effect="dark"
              :content="row.sql_statement"
              placement="top-start"
              show-after="500"
            >
              <code class="sql-code">{{ truncateSql(row.sql_statement) }}</code>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="结果行数" width="100" align="center">
          <template #default="{ row }">
            <span>{{ row.result_rows }}</span>
          </template>
        </el-table-column>
        <el-table-column label="耗时(ms)" width="100" align="center">
          <template #default="{ row }">
            <span :class="{ 'slow': row.execution_time_ms > 1000 }">{{ row.execution_time_ms }}</span>
          </template>
        </el-table-column>
        <el-table-column label="执行结果" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'success' ? 'success' : 'danger'"
              size="small"
            >
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="是否拦截" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="row.blocked"
              type="danger"
              size="small"
              effect="dark"
            >
              <el-icon><Warning /></el-icon> 已拦截
            </el-tag>
            <el-tag v-else type="success" size="small">
              正常
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="block_reason" label="拦截原因" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.block_reason" class="block-reason-text">{{ row.block_reason }}</span>
            <span v-else style="color: #c0c4cc;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.error_message" class="err-text">{{ row.error_message }}</span>
            <span v-else style="color: #c0c4cc;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="executed_at" label="执行时间" width="170" align="center">
          <template #default="{ row }">
            {{ formatTime(row.executed_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right" align="center">
          <template #default="{ row }">
            <el-button
              size="small"
              type="warning"
              link
              @click="handleViewSql(row)"
            >
              查看SQL
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="total > 0" class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="onSizeChange"
          @current-change="onPageChange"
        />
      </div>

      <el-empty v-if="!loading && logs.length === 0" description="暂无审计日志" />
    </el-card>

    <el-dialog v-model="sqlDialogVisible" title="SQL 详情" width="720px">
      <pre class="sql-detail-pre">{{ selectedSql }}</pre>
      <template #footer>
        <el-button type="primary" @click="copySql">
          <el-icon><CopyDocument /></el-icon> 复制SQL
        </el-button>
        <el-button @click="sqlDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Warning, Search, Document, CopyDocument } from '@element-plus/icons-vue'
import { auditApi, datasourceApi } from '@/api'

const loading = ref(false)
const logs = ref([])
const datasources = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterDsId = ref(null)
const filterStatus = ref(null)
const filterBlocked = ref(null)
const sqlDialogVisible = ref(false)
const selectedSql = ref('')

const fetchLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value
    }
    if (filterDsId.value) params.datasource_id = filterDsId.value
    if (filterStatus.value) params.status = filterStatus.value
    if (filterBlocked.value !== null) params.blocked = filterBlocked.value
    const res = await auditApi.list(params)
    logs.value = res.items
    total.value = res.total
  } catch (e) {
    ElMessage.error('获取日志失败')
  } finally {
    loading.value = false
  }
}

const fetchDatasources = async () => {
  try {
    datasources.value = await datasourceApi.list()
  } catch (e) {}
}

const onFilterChange = () => {
  page.value = 1
  fetchLogs()
}

const onPageChange = (p) => {
  page.value = p
  fetchLogs()
}

const onSizeChange = (size) => {
  pageSize.value = size
  page.value = 1
  fetchLogs()
}

const formatTime = (t) => {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

const truncateSql = (sql) => {
  if (!sql) return ''
  const trimmed = sql.replace(/\s+/g, ' ').trim()
  return trimmed.length > 80 ? trimmed.slice(0, 80) + '...' : trimmed
}

const handleViewSql = (row) => {
  selectedSql.value = row.sql_statement
  sqlDialogVisible.value = true
}

const copySql = async () => {
  try {
    await navigator.clipboard.writeText(selectedSql.value)
    ElMessage.success('已复制到剪贴板')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

onMounted(() => {
  fetchDatasources()
  fetchLogs()
})
</script>

<style scoped>
.audit-page {
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
}

.filter-bar {
  display: flex;
  align-items: center;
}

.table-card {
  background: #fff;
  padding: 0;
}

.sql-code {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  color: #409eff;
}

.slow {
  color: #e6a23c;
  font-weight: 600;
}

.err-text {
  color: #f56c6c;
  font-size: 12px;
}

.block-reason-text {
  color: #f56c6c;
  font-size: 12px;
  background: #fef0f0;
  padding: 2px 6px;
  border-radius: 3px;
}

.pagination-wrap {
  padding: 16px 16px 8px;
  display: flex;
  justify-content: flex-end;
}

.sql-detail-pre {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 6px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 400px;
  overflow: auto;
  margin: 0;
}
</style>
