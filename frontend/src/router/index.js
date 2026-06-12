import { createRouter, createWebHistory } from 'vue-router'
import SqlEditor from '@/views/SqlEditor.vue'
import DataSources from '@/views/DataSources.vue'
import AuditLogs from '@/views/AuditLogs.vue'

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
