<template>
  <div class="work-orders-page">
    <el-card class="filter-card">
      <div class="filter-row">
        <div class="filter-left">
          <span class="filter-label">状态：</span>
          <el-select v-model="filterStatus" placeholder="全部状态" size="default" style="width: 140px;" @change="fetchOrders">
            <el-option label="全部" value="" />
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
            <el-option label="已执行" value="executed" />
            <el-option label="已回滚" value="rollbacked" />
          </el-select>
          <el-checkbox v-model="filterMine" style="margin-left: 16px;" @change="fetchOrders">只看我的</el-checkbox>
        </div>
        <div class="filter-right">
          <el-button type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon> 创建工单
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card class="list-card">
      <el-table :data="orders" stripe border size="default" v-loading="loading">
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="title" label="工单标题" min-width="160" show-overflow-tooltip />
        <el-table-column prop="datasource_name" label="数据源" width="150" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTypeMap[row.status]" size="small">
              {{ statusTextMap[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_by" label="创建人" width="110" />
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="280" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="viewDetail(row)">详情</el-button>
            <el-button
              v-if="isDba && row.status === 'pending'"
              size="small"
              type="success"
              link
              @click="handleApprove(row)"
            >审批通过</el-button>
            <el-button
              v-if="isDba && row.status === 'pending'"
              size="small"
              type="danger"
              link
              @click="openRejectDialog(row)"
            >拒绝</el-button>
            <el-button
              v-if="isDba && row.status === 'approved'"
              size="small"
              type="primary"
              link
              @click="handleExecute(row)"
            >执行</el-button>
            <el-button
              v-if="isDba && row.status === 'executed'"
              size="small"
              type="warning"
              link
              @click="handleRollback(row)"
            >回滚</el-button>
            <el-button
              v-if="row.status === 'pending' && (row.created_by === currentUser?.username || isDba)"
              size="small"
              type="danger"
              link
              @click="handleDelete(row)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next, jumper"
          background
          @current-change="fetchOrders"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="createDialogVisible" title="创建变更工单" width="600px" :close-on-click-modal="false">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="90px">
        <el-form-item label="工单标题" prop="title">
          <el-input v-model="createForm.title" placeholder="请输入工单标题" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="数据源" prop="datasource_id">
          <el-select v-model="createForm.datasource_id" placeholder="请选择数据源" style="width: 100%;">
            <el-option
              v-for="ds in datasources"
              :key="ds.id"
              :label="`${ds.name} (${ds.host}:${ds.port}/${ds.database})`"
              :value="ds.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="SQL语句" prop="sql_statement">
          <el-input
            v-model="createForm.sql_statement"
            type="textarea"
            :rows="8"
            placeholder="请输入写操作SQL（INSERT/UPDATE/DELETE等），多条SQL用分号分隔"
            maxlength="5000"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="请输入变更描述" maxlength="1000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailDialogVisible" title="工单详情" width="720px">
      <div v-if="currentOrder" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="工单ID">{{ currentOrder.id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTypeMap[currentOrder.status]">
              {{ statusTextMap[currentOrder.status] }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="工单标题" :span="2">{{ currentOrder.title }}</el-descriptions-item>
          <el-descriptions-item label="数据源">{{ currentOrder.datasource_name }}</el-descriptions-item>
          <el-descriptions-item label="影响行数">{{ currentOrder.affected_rows || 0 }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ currentOrder.created_by }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(currentOrder.created_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="currentOrder.approved_by" label="审批人">{{ currentOrder.approved_by }}</el-descriptions-item>
          <el-descriptions-item v-if="currentOrder.approved_at" label="审批时间">{{ formatDate(currentOrder.approved_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="currentOrder.rejected_by" label="拒绝人">{{ currentOrder.rejected_by }}</el-descriptions-item>
          <el-descriptions-item v-if="currentOrder.rejected_at" label="拒绝时间">{{ formatDate(currentOrder.rejected_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="currentOrder.executed_by" label="执行人">{{ currentOrder.executed_by }}</el-descriptions-item>
          <el-descriptions-item v-if="currentOrder.executed_at" label="执行时间">{{ formatDate(currentOrder.executed_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="currentOrder.rollbacked_by" label="回滚人">{{ currentOrder.rollbacked_by }}</el-descriptions-item>
          <el-descriptions-item v-if="currentOrder.rollbacked_at" label="回滚时间">{{ formatDate(currentOrder.rollbacked_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="currentOrder.description" label="描述" :span="2">{{ currentOrder.description }}</el-descriptions-item>
          <el-descriptions-item v-if="currentOrder.reject_reason" label="拒绝原因" :span="2">
            <span style="color: #f56c6c;">{{ currentOrder.reject_reason }}</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="currentOrder.execution_result" label="执行结果" :span="2">
            <span style="color: #67c23a;">{{ currentOrder.execution_result }}</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="currentOrder.execution_error" label="执行错误" :span="2">
            <span style="color: #f56c6c;">{{ currentOrder.execution_error }}</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="currentOrder.rollback_result" label="回滚结果" :span="2">
            <span style="color: #e6a23c;">{{ currentOrder.rollback_result }}</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="currentOrder.rollback_error" label="回滚错误" :span="2">
            <span style="color: #f56c6c;">{{ currentOrder.rollback_error }}</span>
          </el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">SQL 语句</el-divider>
        <pre class="sql-pre">{{ currentOrder.sql_statement }}</pre>

        <el-divider v-if="currentOrder.rollback_sql" content-position="left">回滚 SQL</el-divider>
        <pre v-if="currentOrder.rollback_sql" class="sql-pre rollback">{{ currentOrder.rollback_sql }}</pre>
      </div>
    </el-dialog>

    <el-dialog v-model="rejectDialogVisible" title="拒绝工单" width="480px">
      <el-form :model="rejectForm" label-width="80px">
        <el-form-item label="拒绝原因">
          <el-input v-model="rejectForm.reject_reason" type="textarea" :rows="4" placeholder="请输入拒绝原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="rejecting" @click="submitReject">确认拒绝</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { workOrderApi, datasourceApi } from '@/api'

const loading = ref(false)
const submitting = ref(false)
const rejecting = ref(false)
const orders = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')
const filterMine = ref(false)
const datasources = ref([])

const createDialogVisible = ref(false)
const createFormRef = ref(null)
const createForm = reactive({
  title: '',
  datasource_id: null,
  sql_statement: '',
  description: ''
})

const detailDialogVisible = ref(false)
const currentOrder = ref(null)

const rejectDialogVisible = ref(false)
const rejectOrder = ref(null)
const rejectForm = reactive({
  reject_reason: ''
})

const currentUser = computed(() => {
  const userStr = localStorage.getItem('user')
  return userStr ? JSON.parse(userStr) : null
})

const isDba = computed(() => {
  return currentUser.value?.role === 'dba'
})

const statusTextMap = {
  pending: '待审批',
  approved: '已通过',
  rejected: '已拒绝',
  executed: '已执行',
  rollbacked: '已回滚'
}

const statusTypeMap = {
  pending: 'warning',
  approved: 'primary',
  rejected: 'danger',
  executed: 'success',
  rollbacked: 'info'
}

const createRules = {
  title: [{ required: true, message: '请输入工单标题', trigger: 'blur' }],
  datasource_id: [{ required: true, message: '请选择数据源', trigger: 'change' }],
  sql_statement: [{ required: true, message: '请输入SQL语句', trigger: 'blur' }]
}

const fetchOrders = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (filterStatus.value) {
      params.status = filterStatus.value
    }
    if (filterMine.value) {
      params.mine = true
    }
    const result = await workOrderApi.list(params)
    orders.value = result.items
    total.value = result.total
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '获取工单列表失败')
  } finally {
    loading.value = false
  }
}

const fetchDatasources = async () => {
  try {
    datasources.value = await datasourceApi.list()
  } catch (e) {
    ElMessage.error('获取数据源列表失败')
  }
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  fetchOrders()
}

const openCreateDialog = () => {
  createForm.title = ''
  createForm.datasource_id = datasources.value.length > 0 ? datasources.value[0].id : null
  createForm.sql_statement = ''
  createForm.description = ''
  createDialogVisible.value = true
}

const submitCreate = async () => {
  if (!createFormRef.value) return
  try {
    await createFormRef.value.validate()
  } catch (e) {
    return
  }
  submitting.value = true
  try {
    await workOrderApi.create(createForm)
    ElMessage.success('工单创建成功')
    createDialogVisible.value = false
    fetchOrders()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

const viewDetail = async (row) => {
  try {
    currentOrder.value = await workOrderApi.get(row.id)
    detailDialogVisible.value = true
  } catch (e) {
    ElMessage.error('获取工单详情失败')
  }
}

const handleApprove = (row) => {
  ElMessageBox.confirm(`确认审批通过工单 #${row.id} "${row.title}" 吗？`, '确认审批', {
    confirmButtonText: '确认通过',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await workOrderApi.approve(row.id)
      ElMessage.success('审批通过')
      fetchOrders()
    } catch (e) {
      ElMessage.error(e?.response?.data?.detail || '审批失败')
    }
  }).catch(() => {})
}

const openRejectDialog = (row) => {
  rejectOrder.value = row
  rejectForm.reject_reason = ''
  rejectDialogVisible.value = true
}

const submitReject = async () => {
  if (!rejectForm.reject_reason.trim()) {
    ElMessage.warning('请输入拒绝原因')
    return
  }
  rejecting.value = true
  try {
    await workOrderApi.reject(rejectOrder.value.id, {
      reject_reason: rejectForm.reject_reason
    })
    ElMessage.success('已拒绝')
    rejectDialogVisible.value = false
    fetchOrders()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    rejecting.value = false
  }
}

const handleExecute = (row) => {
  ElMessageBox.confirm(`确认执行工单 #${row.id} "${row.title}" 吗？执行后将不可撤销（可回滚）。`, '确认执行', {
    confirmButtonText: '确认执行',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      const result = await workOrderApi.execute(row.id)
      ElMessage.success(`执行成功，影响 ${result.affected_rows || 0} 行`)
      fetchOrders()
    } catch (e) {
      ElMessage.error(e?.response?.data?.detail || '执行失败')
    }
  }).catch(() => {})
}

const handleRollback = (row) => {
  ElMessageBox.confirm(`确认回滚工单 #${row.id} "${row.title}" 吗？回滚将撤销本次变更。`, '确认回滚', {
    confirmButtonText: '确认回滚',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      const result = await workOrderApi.rollback(row.id)
      ElMessage.success('回滚成功')
      fetchOrders()
    } catch (e) {
      ElMessage.error(e?.response?.data?.detail || '回滚失败')
    }
  }).catch(() => {})
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确认删除工单 #${row.id} "${row.title}" 吗？`, '确认删除', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await workOrderApi.delete(row.id)
      ElMessage.success('删除成功')
      fetchOrders()
    } catch (e) {
      ElMessage.error(e?.response?.data?.detail || '删除失败')
    }
  }).catch(() => {})
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

onMounted(() => {
  fetchOrders()
  fetchDatasources()
})
</script>

<style scoped>
.work-orders-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card, .list-card {
  padding: 0;
}

.filter-row {
  padding: 14px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 14px;
  color: #606266;
}

.pagination-wrap {
  padding: 16px 18px;
  display: flex;
  justify-content: flex-end;
}

.detail-content {
  font-size: 14px;
}

.sql-pre {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 14px;
  border-radius: 6px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow: auto;
  margin: 0;
}

.sql-pre.rollback {
  background: #fff7e6;
  color: #ad6800;
  border: 1px solid #ffd591;
}
</style>
