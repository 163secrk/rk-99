<template>
  <div class="masking-rules-page">
    <div class="page-header">
      <h2><el-icon><Lock /></el-icon> 数据脱敏规则</h2>
      <div class="header-actions">
        <el-select
          v-model="filterMaskType"
          placeholder="按脱敏类型筛选"
          clearable
          style="width: 180px; margin-right: 10px;"
          @change="fetchRules"
        >
          <el-option label="手机号" value="phone" />
          <el-option label="身份证" value="id_card" />
          <el-option label="薪资" value="salary" />
          <el-option label="姓名" value="name" />
          <el-option label="自定义" value="custom" />
        </el-select>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon> 新建规则
        </el-button>
      </div>
    </div>

    <el-card class="rules-card">
      <el-table :data="filteredRules" v-loading="loading" stripe border>
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="name" label="规则名称" min-width="140" />
        <el-table-column prop="mask_type" label="脱敏类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="maskTypeTagType(row.mask_type)" size="small">
              {{ formatMaskType(row.mask_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="column_pattern" label="列名匹配" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <code class="pattern-code">{{ row.column_pattern }}</code>
          </template>
        </el-table-column>
        <el-table-column label="脱敏预览" width="160" align="center">
          <template #default="{ row }">
            <span class="preview-text">{{ getPreview(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.description">{{ row.description }}</span>
            <span v-else style="color: #c0c4cc;">-</span>
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

      <el-empty v-if="!loading && rules.length === 0" description="暂无脱敏规则，请点击新建规则添加" />
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑脱敏规则' : '新建脱敏规则'"
      width="580px"
      @close="resetForm"
    >
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="110px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="formData.name" placeholder="如：手机号脱敏" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="脱敏类型" prop="mask_type">
          <el-select v-model="formData.mask_type" style="width: 100%;" @change="onMaskTypeChange">
            <el-option label="手机号" value="phone" />
            <el-option label="身份证" value="id_card" />
            <el-option label="薪资" value="salary" />
            <el-option label="姓名" value="name" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="列名匹配" prop="column_pattern">
          <el-input
            v-model="formData.column_pattern"
            placeholder="请输入列名正则表达式，如: phone|mobile|tel"
            maxlength="500"
            show-word-limit
          />
          <div class="form-tip">
            <el-icon class="tip-icon"><InfoFilled /></el-icon>
            <span>使用正则表达式匹配查询结果列名，不区分大小写</span>
          </div>
          <div class="preset-patterns">
            <span class="preset-label">常用列名：</span>
            <el-tag
              v-for="p in presetPatterns"
              :key="p.value"
              size="small"
              class="preset-tag"
              @click="formData.column_pattern = p.value"
            >
              {{ p.label }}
            </el-tag>
          </div>
        </el-form-item>
        <el-form-item label="保留前N位" prop="keep_prefix">
          <el-input-number v-model="formData.keep_prefix" :min="0" :max="20" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="保留后N位" prop="keep_suffix">
          <el-input-number v-model="formData.keep_suffix" :min="0" :max="20" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="掩码字符" prop="mask_char">
          <el-input v-model="formData.mask_char" maxlength="10" style="width: 120px;" />
        </el-form-item>
        <el-form-item label="脱敏预览">
          <div class="preview-box">
            <span class="preview-label">原始值：</span>
            <code>{{ previewOriginal }}</code>
            <span class="preview-arrow">→</span>
            <span class="preview-label">脱敏后：</span>
            <code class="preview-masked">{{ previewMasked }}</code>
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
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Lock, Plus, InfoFilled } from '@element-plus/icons-vue'
import { maskingRuleApi } from '@/api'

const loading = ref(false)
const rules = ref([])
const filterMaskType = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const PRESET_MASK_CONFIGS = {
  phone: { keep_prefix: 3, keep_suffix: 4, mask_char: '*', sample: '13812340001' },
  id_card: { keep_prefix: 3, keep_suffix: 4, mask_char: '*', sample: '110101199001011234' },
  salary: { keep_prefix: 0, keep_suffix: 2, mask_char: '*', sample: '25800' },
  name: { keep_prefix: 1, keep_suffix: 0, mask_char: '*', sample: '张三丰' }
}

const PRESET_PATTERNS_MAP = {
  phone: [
    { label: 'phone/mobile/tel', value: 'phone|mobile|tel|cell' },
    { label: 'phone_number', value: 'phone_number' }
  ],
  id_card: [
    { label: 'id_card/idcard/identity', value: 'id_card|idcard|identity|id_no' },
    { label: '身份证', value: '身份证|身份号' }
  ],
  salary: [
    { label: 'salary/wage/pay', value: 'salary|wage|pay|income|compensation' },
    { label: '薪水', value: '薪资|薪水|工资|收入' }
  ],
  name: [
    { label: 'name/username', value: 'name|username|real_name|full_name' },
    { label: '姓名', value: '姓名|名字' }
  ],
  custom: []
}

const presetPatterns = computed(() => {
  return PRESET_PATTERNS_MAP[formData.value.mask_type] || []
})

const filteredRules = computed(() => {
  if (!filterMaskType.value) return rules.value
  return rules.value.filter(r => r.mask_type === filterMaskType.value)
})

const defaultForm = {
  name: '',
  column_pattern: '',
  mask_type: 'phone',
  keep_prefix: 3,
  keep_suffix: 4,
  mask_char: '*',
  description: '',
  is_active: true
}

const formData = ref({ ...defaultForm })

const formRules = {
  name: [
    { required: true, message: '请输入规则名称', trigger: 'blur' },
    { min: 1, max: 255, message: '长度在 1 到 255 个字符', trigger: 'blur' }
  ],
  mask_type: [
    { required: true, message: '请选择脱敏类型', trigger: 'change' }
  ],
  column_pattern: [
    { required: true, message: '请输入列名匹配规则', trigger: 'blur' }
  ]
}

const previewOriginal = computed(() => {
  const config = PRESET_MASK_CONFIGS[formData.value.mask_type]
  return config ? config.sample : '示例文本'
})

const previewMasked = computed(() => {
  const text = previewOriginal.value
  const keepPrefix = formData.value.keep_prefix
  const keepSuffix = formData.value.keep_suffix
  const maskChar = formData.value.mask_char || '*'
  const totalLen = text.length
  const prefixPart = keepPrefix > 0 ? text.substring(0, keepPrefix) : ''
  const suffixPart = keepSuffix > 0 ? text.substring(totalLen - keepSuffix) : ''
  const middleLen = totalLen - keepPrefix - keepSuffix
  if (middleLen <= 0) return text
  return prefixPart + maskChar.repeat(middleLen) + suffixPart
})

const fetchRules = async () => {
  loading.value = true
  try {
    rules.value = await maskingRuleApi.list()
  } catch (e) {
    ElMessage.error('获取脱敏规则列表失败')
  } finally {
    loading.value = false
  }
}

const formatMaskType = (type) => {
  const map = {
    phone: '手机号',
    id_card: '身份证',
    salary: '薪资',
    name: '姓名',
    custom: '自定义'
  }
  return map[type] || type
}

const maskTypeTagType = (type) => {
  const map = {
    phone: 'danger',
    id_card: 'warning',
    salary: 'success',
    name: '',
    custom: 'info'
  }
  return map[type] || 'info'
}

const formatTime = (t) => {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

const getPreview = (row) => {
  const config = PRESET_MASK_CONFIGS[row.mask_type]
  const sample = config ? config.sample : '示例文本'
  const text = sample
  const keepPrefix = row.keep_prefix
  const keepSuffix = row.keep_suffix
  const maskChar = row.mask_char || '*'
  const totalLen = text.length
  const prefixPart = keepPrefix > 0 ? text.substring(0, keepPrefix) : ''
  const suffixPart = keepSuffix > 0 ? text.substring(totalLen - keepSuffix) : ''
  const middleLen = totalLen - keepPrefix - keepSuffix
  if (middleLen <= 0) return text
  return prefixPart + maskChar.repeat(middleLen) + suffixPart
}

const onMaskTypeChange = (type) => {
  const config = PRESET_MASK_CONFIGS[type]
  if (config) {
    formData.value.keep_prefix = config.keep_prefix
    formData.value.keep_suffix = config.keep_suffix
    formData.value.mask_char = config.mask_char
  }
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

const toggleRule = async (row) => {
  try {
    await maskingRuleApi.update(row.id, {
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
      await maskingRuleApi.update(formData.value.id, formData.value)
      ElMessage.success('更新成功')
    } else {
      await maskingRuleApi.create(formData.value)
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
    `确定要删除脱敏规则 "${row.name}" 吗？删除后相关列将不再脱敏。`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await maskingRuleApi.delete(row.id)
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
.masking-rules-page {
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
  color: #409eff;
}

.preview-text {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  color: #e6a23c;
  background: #fdf6ec;
  padding: 2px 8px;
  border-radius: 3px;
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

.preset-patterns {
  margin-top: 8px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.preset-label {
  font-size: 12px;
  color: #909399;
}

.preset-tag {
  cursor: pointer;
}

.preset-tag:hover {
  opacity: 0.8;
}

.preview-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 13px;
}

.preview-label {
  color: #909399;
}

.preview-arrow {
  color: #c0c4cc;
  font-weight: bold;
}

.preview-masked {
  color: #e6a23c;
  font-weight: 600;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}
</style>
