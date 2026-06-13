import { createRouter, createWebHistory } from 'vue-router'
import SqlEditor from '@/views/SqlEditor.vue'
import DataSources from '@/views/DataSources.vue'
import AuditLogs from '@/views/AuditLogs.vue'
import RiskRules from '@/views/RiskRules.vue'
import MaskingRules from '@/views/MaskingRules.vue'

const routes = [
  {
    path: '/',
    name: 'editor',
    component: SqlEditor,
    meta: { title: 'SQL编辑器' }
  },
  {
    path: '/datasources',
    name: 'datasources',
    component: DataSources,
    meta: { title: '数据源管理' }
  },
  {
    path: '/audit-logs',
    name: 'audit-logs',
    component: AuditLogs,
    meta: { title: '审计日志' }
  },
  {
    path: '/risk-rules',
    name: 'risk-rules',
    component: RiskRules,
    meta: { title: '风险规则' }
  },
  {
    path: '/masking-rules',
    name: 'masking-rules',
    component: MaskingRules,
    meta: { title: '脱敏规则' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
