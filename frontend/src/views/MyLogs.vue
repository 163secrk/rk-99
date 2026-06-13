<template>
  <div class="my-logs-page">
    <el-card>
      <div class="page-header">
        <div class="header-left">
          <el-icon><Document /></el-icon>
          <span class="header-title">我的执行记录</span>
        </div>
      </div>

      <el-table :data="logs" stripe border style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="datasource_name" label="数据源" width="150" />
        <el-table-column prop="sql_statement" label="SQL语句" min-width="280">
          <template #default="{ row }">
            <el-tooltip :content="row.sql_statement" placement="top" :show-after="300">
              <span class="sql-text">{{ row.sql_statement }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'success' ? 'success' : row.status === 'blocked' ? 'danger' : 'warning'"
              size="small"
            >
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="result_rows" label="结果行数" width="90" />
        <el-table-column prop="execution_time_ms" label="耗时(ms)" width="100" />
        <el-table-column prop="executed_at" label="执行时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.executed_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" min-width="200">
          <template #default="{ row }">
            <el-tooltip v-if="row.error_message" :content="row.error_message" placement="top" :show-after="300">
              <span class="error-text">{{ row.error_message }}</span>
            </el-tooltip>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next, jumper"
          background
          @current-change="fetchLogs"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import { myLogApi } from '@/api'

const logs = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)

const fetchLogs = async () => {
  loading.value = true
  try {
    const result = await myLogApi.list({
      page: currentPage.value,
      page_size: pageSize
    })
    logs.value = result.items
    total.value = result.total
  } catch (e) {
    ElMessage.error('获取执行记录失败')
  } finally {
    loading.value = false
  }
}

const statusLabel = (status) => {
  const map = { success: '成功', failed: '失败', blocked: '已拦截' }
  return map[status] || status
}

const formatTime = (val) => {
  if (!val) return '-'
  const d = new Date(val)
  return d.toLocaleString('zh-CN')
}

onMounted(fetchLogs)
</script>

<style scoped>
.my-logs-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid #ebeef5;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.sql-text {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
}

.error-text {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #f56c6c;
  font-size: 12px;
}

.pagination-wrap {
  padding: 16px 0 4px;
  display: flex;
  justify-content: flex-end;
}
</style>
