<template>
  <div class="risk-rules-page">
    <div class="page-header">
      <h2><el-icon><Warning /></el-icon> 风险规则管理</h2>
      <div class="header-actions">
        <el-select
          v-model="filterRuleType"
          placeholder="按规则类型筛选"
          clearable
          style="width: 180px; margin-right: 10px;"
          @change="fetchRules"
        >
          <el-option label="敏感表规则" value="sensitive_table" />
        </el-select>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon> 新建规则
        </el-button>
      </div>
    </div>

    <el-card class="rules-card">
      <el-table :data="rules" v-loading="loading" stripe border>
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="name" label="规则名称" min-width="160" />
        <el-table-column prop="rule_type" label="规则类型" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="warning">{{ formatRuleType(row.rule_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="pattern" label="匹配规则" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <code class="pattern-code">{{ row.pattern }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.description">{{ row.description }}</span>
            <span v-else style="color: #c0c4cc;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="风险等级" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="severityTagType(row.severity)" size="small">
              {{ formatSeverity(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              @change="toggleRule(row)"
              active-text="启用"
              inactive-text="禁用"
              inline-prompt
            />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" align="center">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openEditDialog(row)">
              编辑
            </el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && rules.length === 0" description="暂无风险规则" />
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑规则' : '新建规则'"
      width="560px"
      @close="resetForm"
    >
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入规则名称" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="规则类型" prop="rule_type">
          <el-select v-model="formData.rule_type" style="width: 100%;" @change="onRuleTypeChange">
            <el-option label="敏感表规则" value="sensitive_table" />
          </el-select>
        </el-form-item>
        <el-form-item label="匹配规则" prop="pattern">
          <el-input
            v-model="formData.pattern"
            type="textarea"
            :rows="3"
            placeholder="请输入正则表达式，例如: (user|member|account).*"
            maxlength="1000"
            show-word-limit
          />
          <div class="form-tip">
            <el-icon class="tip-icon"><InfoFilled /></el-icon>
            <span>敏感表规则使用正则表达式匹配表名，不区分大小写</span>
          </div>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="2"
            placeholder="请输入规则描述（可选）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="风险等级" prop="severity">
          <el-radio-group v-model="formData.severity">
            <el-radio value="low">低</el-radio>
            <el-radio value="medium">中</el-radio>
            <el-radio value="high">高</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="formData.is_active" active-text="启用" inactive-text="禁用" inline-prompt />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Warning, Plus, InfoFilled } from '@element-plus/icons-vue'
import { riskRuleApi } from '@/api'

const loading = ref(false)
const rules = ref([])
const filterRuleType = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const defaultForm = {
  name: '',
  rule_type: 'sensitive_table',
  pattern: '',
  description: '',
  severity: 'high',
  is_active: true
}

const formData = ref({ ...defaultForm })

const formRules = {
  name: [
    { required: true, message: '请输入规则名称', trigger: 'blur' },
    { min: 1, max: 255, message: '长度在 1 到 255 个字符', trigger: 'blur' }
  ],
  rule_type: [
    { required: true, message: '请选择规则类型', trigger: 'change' }
  ],
  pattern: [
    { required: true, message: '请输入匹配规则', trigger: 'blur' }
  ],
  severity: [
    { required: true, message: '请选择风险等级', trigger: 'change' }
  ]
}

const fetchRules = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterRuleType.value) params.rule_type = filterRuleType.value
    rules.value = await riskRuleApi.list(params)
  } catch (e) {
    ElMessage.error('获取规则列表失败')
  } finally {
    loading.value = false
  }
}

const formatRuleType = (type) => {
  const map = {
    sensitive_table: '敏感表'
  }
  return map[type] || type
}

const formatSeverity = (sev) => {
  const map = { low: '低', medium: '中', high: '高' }
  return map[sev] || sev
}

const severityTagType = (sev) => {
  const map = { low: 'info', medium: 'warning', high: 'danger' }
  return map[sev] || 'info'
}

const formatTime = (t) => {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

const openCreateDialog = () => {
  isEdit.value = false
  formData.value = { ...defaultForm }
  dialogVisible.value = true
}

const openEditDialog = (row) => {
  isEdit.value = true
  formData.value = { ...row }
  dialogVisible.value = true
}

const resetForm = () => {
  formRef.value?.resetFields()
  formData.value = { ...defaultForm }
}

const onRuleTypeChange = () => {
}

const toggleRule = async (row) => {
  try {
    await riskRuleApi.update(row.id, {
      ...row,
      is_active: row.is_active
    })
    ElMessage.success(row.is_active ? '已启用' : '已禁用')
  } catch (e) {
    row.is_active = !row.is_active
    ElMessage.error('操作失败')
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch (e) {
    return
  }

  submitting.value = true
  try {
    if (isEdit.value) {
      await riskRuleApi.update(formData.value.id, formData.value)
      ElMessage.success('更新成功')
    } else {
      await riskRuleApi.create(formData.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchRules()
  } catch (e) {
    const msg = e?.response?.data?.detail || '操作失败'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除规则 "${row.name}" 吗？`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await riskRuleApi.delete(row.id)
      ElMessage.success('删除成功')
      fetchRules()
    } catch (e) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

onMounted(fetchRules)
</script>

<style scoped>
.risk-rules-page {
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

.header-actions {
  display: flex;
  align-items: center;
}

.rules-card {
  background: #fff;
  padding: 0;
}

.pattern-code {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  color: #e6a23c;
}

.form-tip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}

.tip-icon {
  font-size: 14px;
}
</style>
