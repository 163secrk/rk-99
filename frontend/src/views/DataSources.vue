<template>
  <div class="datasources-page">
    <div class="page-header">
      <h2><el-icon><Coin /></el-icon> 数据源管理</h2>
      <el-button type="primary" @click="openDialog()">
        <el-icon><Plus /></el-icon> 新增数据源
      </el-button>
    </div>

    <el-card class="table-card">
      <el-table :data="datasources" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="name" label="数据源名称" min-width="140">
          <template #default="{ row }">
            <span style="font-weight: 500;">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="host" label="主机" min-width="130" />
        <el-table-column prop="port" label="端口" width="80" align="center" />
        <el-table-column prop="username" label="用户名" width="110" />
        <el-table-column prop="database" label="数据库" width="120" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right" align="center">
          <template #default="{ row }">
            <el-button size="small" type="info" @click="testConnection(row)">
              <el-icon><Connection /></el-icon> 测试
            </el-button>
            <el-button size="small" type="primary" @click="openDialog(row)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && datasources.length === 0" description="暂无数据源，请添加" />
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑数据源' : '新增数据源'"
      width="580px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="90px"
      >
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="名称" prop="name">
              <el-input v-model="formData.name" placeholder="请输入数据源名称" maxlength="50" />
            </el-form-item>
          </el-col>
          <el-col :span="14">
            <el-form-item label="主机" prop="host">
              <el-input v-model="formData.host" placeholder="例如: 127.0.0.1" />
            </el-form-item>
          </el-col>
          <el-col :span="10">
            <el-form-item label="端口" prop="port">
              <el-input-number v-model="formData.port" :min="1" :max="65535" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="用户名" prop="username">
              <el-input v-model="formData.username" placeholder="MySQL用户名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="密码" prop="password">
              <el-input v-model="formData.password" type="password" placeholder="MySQL密码" show-password />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="数据库" prop="database">
              <el-input v-model="formData.database" placeholder="要连接的数据库名称" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="描述" prop="description">
              <el-input v-model="formData.description" type="textarea" :rows="2" placeholder="选填" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="状态" prop="is_active">
              <el-switch v-model="formData.is_active" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="info" @click="testConnectionFromForm">
          <el-icon><Connection /></el-icon> 测试连接
        </el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { datasourceApi } from '@/api'

const loading = ref(false)
const datasources = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const formRef = ref(null)

const formData = ref({
  name: '',
  host: '',
  port: 3306,
  username: '',
  password: '',
  database: '',
  description: '',
  is_active: true
})

const formRules = {
  name: [{ required: true, message: '请输入数据源名称', trigger: 'blur' }],
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  database: [{ required: true, message: '请输入数据库名', trigger: 'blur' }]
}

const fetchList = async () => {
  loading.value = true
  try {
    datasources.value = await datasourceApi.list()
  } catch (e) {
    ElMessage.error('获取数据源列表失败')
  } finally {
    loading.value = false
  }
}

const openDialog = (row = null) => {
  if (row) {
    isEdit.value = true
    editId.value = row.id
    formData.value = { ...row }
  } else {
    isEdit.value = false
    editId.value = null
    formData.value = {
      name: '',
      host: '',
      port: 3306,
      username: '',
      password: '',
      database: '',
      description: '',
      is_active: true
    }
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
    if (isEdit.value) {
      await datasourceApi.update(editId.value, formData.value)
      ElMessage.success('更新成功')
    } else {
      await datasourceApi.create(formData.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchList()
  } catch (e) {
    if (e?.message) ElMessage.error(e.message)
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除数据源"${row.name}"吗？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await datasourceApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchList()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const testConnection = async (row) => {
  const data = {
    name: row.name,
    host: row.host,
    port: row.port,
    username: row.username,
    password: row.password,
    database: row.database
  }
  const result = await datasourceApi.test(data)
  if (result.success) {
    ElMessage.success(result.message || '连接成功')
  } else {
    ElMessage.error(result.message || '连接失败')
  }
}

const testConnectionFromForm = async () => {
  const result = await datasourceApi.test(formData.value)
  if (result.success) {
    ElMessage.success(result.message || '连接成功')
  } else {
    ElMessage.error(result.message || '连接失败')
  }
}

const formatTime = (t) => {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

onMounted(fetchList)
</script>

<style scoped>
.datasources-page {
  max-width: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h2 {
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.table-card {
  background: #fff;
}
</style>
