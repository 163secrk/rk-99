<template>
  <div class="sql-editor-page">
    <el-card class="editor-card">
      <div class="editor-header">
        <div class="header-left">
          <el-icon><Edit /></el-icon>
          <span class="header-title">SQL 查询编辑器</span>
          <el-tag v-if="statementCount > 1" type="warning" size="small" style="margin-left: 8px;">
            {{ statementCount }} 条语句
          </el-tag>
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
            <el-icon><VideoPlay /></el-icon> 执行 (Ctrl+Enter)
          </el-button>
          <el-button :loading="checkingRisk" @click="checkRisk">
            <el-icon><Warning /></el-icon> 风险检测
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
          placeholder="请输入SQL语句，多条语句用分号分隔... 例如: SELECT * FROM users LIMIT 100; SELECT * FROM orders LIMIT 100"
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
        <el-tooltip content="只对第一条SELECT查询分页，多条查询时其余结果返回前1000行" placement="top">
          <el-icon class="info-icon"><InfoFilled /></el-icon>
        </el-tooltip>
        <span v-if="hasWriteOperation" class="write-tip">
          <el-icon color="#e6a23c"><Warning /></el-icon>
          检测到写操作，普通用户需提交工单审批
          <el-button type="primary" link size="small" @click="goToWorkOrders">去提交工单</el-button>
        </span>
      </div>
    </el-card>

    <el-card class="result-card">
      <div class="result-header">
        <div class="result-title">
          <el-icon><DataLine /></el-icon>
          <span>查询结果</span>
          <el-tag v-if="batchMode && batchResultInfo.success_count !== undefined" type="success" style="margin-left: 12px;">
            成功 {{ batchResultInfo.success_count }} 条
          </el-tag>
          <el-tag v-if="batchMode && batchResultInfo.failed_count > 0" type="danger" style="margin-left: 6px;">
            失败 {{ batchResultInfo.failed_count }} 条
          </el-tag>
          <el-tag v-if="!batchMode && resultInfo.total_rows !== null" type="info" style="margin-left: 12px;">
            共 {{ resultInfo.total_rows }} 行 / 耗时 {{ resultInfo.execution_time_ms }}ms
          </el-tag>
          <el-tag v-if="batchMode && batchResultInfo.execution_time_ms" type="info" style="margin-left: 12px;">
            总耗时 {{ batchResultInfo.execution_time_ms }}ms
          </el-tag>
        </div>
      </div>

      <div v-loading="executing" class="result-body">
        <div v-if="!executing && !hasResults" class="empty-tip">
          <el-empty description="暂无结果，请先执行SQL查询" />
        </div>

        <template v-else-if="batchMode && batchResults.length > 0">
          <el-tabs v-model="activeResultTab" type="card" class="result-tabs">
            <el-tab-pane
              v-for="(res, idx) in batchResults"
              :key="idx"
              :label="getResultTabLabel(res, idx)"
              :name="String(idx)"
            >
              <div v-if="res.error" class="error-tip">
                <el-alert :title="res.error" type="error" :closable="false" show-icon />
              </div>
              <div v-else-if="res.is_select && res.columns.length > 0" class="table-wrap">
                <el-table :data="transformRows(res.columns, res.rows)" stripe border size="small" style="width: 100%" max-height="450">
                  <el-table-column
                    v-for="col in res.columns"
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
                <div class="result-meta">
                  <span>{{ res.total_rows }} 行</span>
                </div>
              </div>
              <div v-else-if="!res.is_select" class="affected-tip">
                <el-alert :title="`执行成功，影响 ${res.affected_rows} 行`" type="success" :closable="false" show-icon />
              </div>
              <div v-else class="empty-tip">
                <el-empty description="无结果" :image-size="60" />
              </div>
            </el-tab-pane>
          </el-tabs>
        </template>

        <div v-else-if="!batchMode && columns.length > 0" class="table-wrap">
          <el-table :data="rows" stripe border size="small" style="width: 100%" max-height="450">
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

        <div v-if="!batchMode && columns.length > 0 && resultInfo.total_pages > 1" class="pagination-wrap">
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
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Warning, Edit, VideoPlay, RefreshRight, InfoFilled, DataLine } from '@element-plus/icons-vue'
import { datasourceApi, queryApi, riskRuleApi } from '@/api'

const router = useRouter()
const editorRef = ref(null)
const datasources = ref([])
const selectedDsId = ref(null)
const sqlText = ref('')
const executing = ref(false)
const checkingRisk = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const columns = ref([])
const rows = ref([])
const activeResultTab = ref('0')

const resultInfo = reactive({
  total_rows: null,
  total_pages: 0,
  execution_time_ms: 0
})

const batchResults = ref([])
const batchResultInfo = reactive({
  success_count: 0,
  failed_count: 0,
  execution_time_ms: 0
})

const statementCount = computed(() => {
  const sql = sqlText.value.trim()
  if (!sql) return 0
  let count = 0
  let inSingleQuote = false
  let inDoubleQuote = false
  let inBacktick = false
  for (let i = 0; i < sql.length; i++) {
    const ch = sql[i]
    if (ch === "'" && !inDoubleQuote && !inBacktick) {
      if (i > 0 && sql[i - 1] === '\\') continue
      inSingleQuote = !inSingleQuote
    } else if (ch === '"' && !inSingleQuote && !inBacktick) {
      if (i > 0 && sql[i - 1] === '\\') continue
      inDoubleQuote = !inDoubleQuote
    } else if (ch === '`' && !inSingleQuote && !inDoubleQuote) {
      inBacktick = !inBacktick
    } else if (ch === ';' && !inSingleQuote && !inDoubleQuote && !inBacktick) {
      count++
    }
  }
  const hasTrailing = sql.replace(/;+\s*$/, '').trim().length > 0
  return count > 0 ? count : (hasTrailing ? 1 : 0)
})

const batchMode = computed(() => {
  return statementCount.value > 1
})

const hasResults = computed(() => {
  if (batchMode.value) {
    return batchResults.value.length > 0
  }
  return columns.value.length > 0
})

const hasWriteOperation = computed(() => {
  const sql = sqlText.value.trim().toUpperCase()
  const writeKeywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'REPLACE']
  return writeKeywords.some(kw => sql.includes(kw))
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
  batchResults.value = []
  currentPage.value = 1
  resultInfo.total_rows = null
  resultInfo.total_pages = 0
  resultInfo.execution_time_ms = 0
  batchResultInfo.success_count = 0
  batchResultInfo.failed_count = 0
  batchResultInfo.execution_time_ms = 0
}

const checkRisk = async () => {
  if (!selectedDsId.value) {
    ElMessage.warning('请先选择数据源')
    return
  }
  const sql = sqlText.value.trim()
  if (!sql) {
    ElMessage.warning('请输入SQL语句')
    return
  }

  checkingRisk.value = true
  try {
    const result = await riskRuleApi.check({
      datasource_id: selectedDsId.value,
      sql: sql,
      page: 1,
      page_size: 20
    })
    if (result.blocked) {
      const reasons = result.reasons.map((r, i) => `${i + 1}. ${r}`).join('\n')
      ElMessageBox.alert(
        `检测到以下风险，执行将被拦截：\n\n${reasons}`,
        'SQL 风险警告',
        {
          confirmButtonText: '我知道了',
          type: 'error',
          dangerouslyUseHTMLString: false
        }
      )
    } else if (result.reasons && result.reasons.length > 0) {
      const reasons = result.reasons.map((r, i) => `${i + 1}. ${r}`).join('\n')
      ElMessageBox.alert(
        `检测到以下风险提示：\n\n${reasons}\n\n可以执行，但请注意操作风险。`,
        'SQL 风险提示',
        {
          confirmButtonText: '我知道了',
          type: 'warning'
        }
      )
    } else {
      ElMessage.success('未检测到SQL风险')
    }
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '检测失败'
    ElMessage.error(msg)
  } finally {
    checkingRisk.value = false
  }
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
  activeResultTab.value = '0'

  if (batchMode.value) {
    await runBatchQuery(sql)
  } else {
    await runSingleQuery(sql)
  }

  executing.value = false
}

const runSingleQuery = async (sql) => {
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
    batchResults.value = []
    ElMessage.success(`执行成功，共 ${result.total_rows} 行`)
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '执行失败'
    const isBlocked = msg && msg.includes('SQL 风险拦截')
    const needsOrder = msg && msg.includes('工单审批')
    ElMessageBox.alert(
      msg,
      isBlocked ? 'SQL 执行被拦截' : (needsOrder ? '需要工单审批' : 'SQL 执行错误'),
      {
        confirmButtonText: needsOrder ? '去提交工单' : '确定',
        type: 'error',
        callback: (action) => {
          if (needsOrder && action === 'confirm') {
            router.push('/work-orders')
          }
        }
      }
    )
    columns.value = []
    rows.value = []
    resultInfo.total_rows = null
  }
}

const runBatchQuery = async (sql) => {
  try {
    const result = await queryApi.executeBatch({
      datasource_id: selectedDsId.value,
      sql: sql,
      page: 1,
      page_size: pageSize.value
    })
    batchResults.value = result.results || []
    batchResultInfo.success_count = result.success_count
    batchResultInfo.failed_count = result.failed_count
    batchResultInfo.execution_time_ms = result.execution_time_ms
    columns.value = []
    rows.value = []
    if (result.failed_count > 0) {
      ElMessage.warning(`执行完成：成功 ${result.success_count} 条，失败 ${result.failed_count} 条`)
    } else {
      ElMessage.success(`全部执行成功，共 ${result.success_count} 条语句`)
    }
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '执行失败'
    const isBlocked = msg && msg.includes('SQL 风险拦截')
    const needsOrder = msg && msg.includes('工单审批')
    ElMessageBox.alert(
      msg,
      isBlocked ? 'SQL 执行被拦截' : (needsOrder ? '需要工单审批' : 'SQL 执行错误'),
      {
        confirmButtonText: needsOrder ? '去提交工单' : '确定',
        type: 'error',
        callback: (action) => {
          if (needsOrder && action === 'confirm') {
            router.push('/work-orders')
          }
        }
      }
    )
    batchResults.value = []
  }
}

const transformRows = (cols, list) => {
  if (!cols || !list) return []
  return list.map(arr => {
    const obj = {}
    cols.forEach((c, i) => { obj[c] = arr[i] })
    return obj
  })
}

const getResultTabLabel = (res, idx) => {
  const num = idx + 1
  if (res.error) return `${num}. 失败`
  if (res.is_select) return `${num}. 查询 (${res.total_rows}行)`
  return `${num}. 执行 (${res.affected_rows}行)`
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
  batchResults.value = []
  currentPage.value = 1
  resultInfo.total_rows = null
  resultInfo.total_pages = 0
  resultInfo.execution_time_ms = 0
  batchResultInfo.success_count = 0
  batchResultInfo.failed_count = 0
  batchResultInfo.execution_time_ms = 0
  activeResultTab.value = '0'
  editorRef.value?.focus()
}

const goToWorkOrders = () => {
  router.push('/work-orders')
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
  flex-wrap: wrap;
}

.info-icon {
  color: #909399;
  cursor: help;
}

.write-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #e6a23c;
  margin-left: auto;
  font-size: 13px;
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

.result-meta {
  padding: 8px 12px;
  color: #909399;
  font-size: 13px;
  background: #fafafa;
  border-top: 1px solid #ebeef5;
}

.result-tabs {
  margin-top: -8px;
}

.error-tip, .affected-tip {
  padding: 10px 0;
}

.pagination-wrap {
  padding-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
