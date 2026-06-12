<template>
  <div class="sql-editor-page">
    <el-card class="editor-card">
      <div class="editor-header">
        <div class="header-left">
          <el-icon><Edit /></el-icon>
          <span class="header-title">SQL 查询编辑器</span>
        </div>
        <div class="header-right">
          <el-select
            v-model="selectedDsId"
            placeholder="选择数据源"
            style="width: 260px;"
            @change="onDsChange"
          >
            <el-option
              v-for="ds in datasources"
              :key="ds.id"
              :label="`${ds.name} (${ds.host}:${ds.port}/${ds.database})`"
              :value="ds.id"
            />
          </el-select>
          <el-button type="primary" :loading="executing" @click="runQuery">
            <el-icon><VideoPlay /></el-icon> 执行查询 (Ctrl+Enter)
          </el-button>
          <el-button @click="clearEditor">
            <el-icon><RefreshRight /></el-icon> 清空
          </el-button>
        </div>
      </div>

      <div class="editor-area">
        <textarea
          ref="editorRef"
          v-model="sqlText"
          class="sql-textarea"
          placeholder="请输入SQL语句... 例如: SELECT * FROM users LIMIT 100"
          @keydown.ctrl.enter.exact="runQuery"
          @keydown.meta.enter.exact="runQuery"
          spellcheck="false"
        ></textarea>
      </div>

      <div class="page-size-row">
        <span style="color: #666;">每页行数:</span>
        <el-select v-model="pageSize" size="small" style="width: 120px;">
          <el-option label="10 行" :value="10" />
          <el-option label="20 行" :value="20" />
          <el-option label="50 行" :value="50" />
          <el-option label="100 行" :value="100" />
          <el-option label="500 行" :value="500" />
        </el-select>
        <el-tooltip content="只对SELECT查询有效" placement="top">
          <el-icon class="info-icon"><InfoFilled /></el-icon>
        </el-tooltip>
      </div>
    </el-card>

    <el-card class="result-card">
      <div class="result-header">
        <div class="result-title">
          <el-icon><DataLine /></el-icon>
          <span>查询结果</span>
          <el-tag v-if="resultInfo.total_rows !== null" type="info" style="margin-left: 12px;">
            共 {{ resultInfo.total_rows }} 行 / 耗时 {{ resultInfo.execution_time_ms }}ms
          </el-tag>
        </div>
      </div>

      <div v-loading="executing" class="result-body">
        <div v-if="!executing && columns.length === 0" class="empty-tip">
          <el-empty description="暂无结果，请先执行SQL查询" />
        </div>

        <div v-else-if="columns.length > 0" class="table-wrap">
          <el-table :data="rows" stripe border size="small" style="width: 100%" max-height="500">
            <el-table-column
              v-for="col in columns"
              :key="col"
              :prop="col"
              :label="col"
              min-width="140"
              show-overflow-tooltip
            >
              <template #default="{ row }">
                <span>{{ formatCell(row[col]) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="columns.length > 0 && resultInfo.total_pages > 1" class="pagination-wrap">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="resultInfo.total_rows"
            layout="total, prev, pager, next, jumper"
            background
            @current-change="changePage"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { datasourceApi, queryApi } from '@/api'

const editorRef = ref(null)
const datasources = ref([])
const selectedDsId = ref(null)
const sqlText = ref('')
const executing = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const columns = ref([])
const rows = ref([])
const resultInfo = reactive({
  total_rows: null,
  total_pages: 0,
  execution_time_ms: 0
})

const fetchDatasources = async () => {
  try {
    datasources.value = await datasourceApi.list()
    if (datasources.value.length > 0 && !selectedDsId.value) {
      selectedDsId.value = datasources.value[0].id
    }
  } catch (e) {
    ElMessage.error('获取数据源列表失败')
  }
}

const onDsChange = () => {
  columns.value = []
  rows.value = []
  currentPage.value = 1
  resultInfo.total_rows = null
  resultInfo.total_pages = 0
}

const runQuery = async () => {
  if (!selectedDsId.value) {
    ElMessage.warning('请先选择数据源')
    return
  }
  const sql = sqlText.value.trim()
  if (!sql) {
    ElMessage.warning('请输入SQL语句')
    return
  }

  executing.value = true
  currentPage.value = 1
  try {
    const result = await queryApi.execute({
      datasource_id: selectedDsId.value,
      sql: sql,
      page: 1,
      page_size: pageSize.value
    })
    columns.value = result.columns || []
    rows.value = transformRows(result.columns, result.rows)
    resultInfo.total_rows = result.total_rows
    resultInfo.total_pages = result.total_pages
    resultInfo.execution_time_ms = result.execution_time_ms
    ElMessage.success(`执行成功，共 ${result.total_rows} 行`)
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '执行失败'
    ElMessageBox.alert(msg, 'SQL执行错误', {
      confirmButtonText: '确定',
      type: 'error'
    })
    columns.value = []
    rows.value = []
    resultInfo.total_rows = null
  } finally {
    executing.value = false
  }
}

const transformRows = (cols, list) => {
  return list.map(arr => {
    const obj = {}
    cols.forEach((c, i) => { obj[c] = arr[i] })
    return obj
  })
}

const changePage = async (p) => {
  if (!selectedDsId.value || !sqlText.value.trim()) return
  executing.value = true
  try {
    const result = await queryApi.execute({
      datasource_id: selectedDsId.value,
      sql: sqlText.value.trim(),
      page: p,
      page_size: pageSize.value
    })
    columns.value = result.columns || []
    rows.value = transformRows(result.columns, result.rows)
    resultInfo.total_rows = result.total_rows
    resultInfo.total_pages = result.total_pages
    resultInfo.execution_time_ms = result.execution_time_ms
    await nextTick()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  } finally {
    executing.value = false
  }
}

const formatCell = (val) => {
  if (val === null || val === undefined) return 'NULL'
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

const clearEditor = () => {
  sqlText.value = ''
  columns.value = []
  rows.value = []
  currentPage.value = 1
  resultInfo.total_rows = null
  resultInfo.total_pages = 0
  resultInfo.execution_time_ms = 0
  editorRef.value?.focus()
}

onMounted(fetchDatasources)
</script>

<style scoped>
.sql-editor-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.editor-card, .result-card {
  padding: 0;
}

.editor-header {
  padding: 14px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #ebeef5;
  flex-wrap: wrap;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  gap: 10px;
  align-items: center;
}

.editor-area {
  padding: 12px 18px 4px;
}

.sql-textarea {
  width: 100%;
  min-height: 200px;
  padding: 14px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  resize: vertical;
  outline: none;
  background: #1e1e1e;
  color: #d4d4d4;
}

.sql-textarea:focus {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

.sql-textarea::placeholder {
  color: #888;
}

.page-size-row {
  padding: 10px 18px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.info-icon {
  color: #909399;
  cursor: help;
}

.result-header {
  padding: 14px 18px;
  border-bottom: 1px solid #ebeef5;
}

.result-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.result-body {
  padding: 18px;
  min-height: 200px;
}

.empty-tip {
  padding: 40px 0;
}

.table-wrap {
  border: 1px solid #ebeef5;
  border-radius: 4px;
  overflow: auto;
}

.pagination-wrap {
  padding-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
