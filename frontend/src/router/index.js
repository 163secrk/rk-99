import { createRouter, createWebHistory } from 'vue-router'
import SqlEditor from '@/views/SqlEditor.vue'
import DataSources from '@/views/DataSources.vue'
import AuditLogs from '@/views/AuditLogs.vue'
import RiskRules from '@/views/RiskRules.vue'
import MaskingRules from '@/views/MaskingRules.vue'
import Login from '@/views/Login.vue'
import UserManagement from '@/views/UserManagement.vue'
import MyLogs from '@/views/MyLogs.vue'
import Dashboard from '@/views/Dashboard.vue'
import WorkOrders from '@/views/WorkOrders.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: Login,
    meta: { title: '登录', public: true }
  },
  {
    path: '/',
    name: 'editor',
    component: SqlEditor,
    meta: { title: 'SQL编辑器', roles: ['dba', 'developer'] }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: Dashboard,
    meta: { title: '审计分析看板', roles: ['dba'] }
  },
  {
    path: '/my-logs',
    name: 'my-logs',
    component: MyLogs,
    meta: { title: '我的记录', roles: ['dba', 'developer'] }
  },
  {
    path: '/work-orders',
    name: 'work-orders',
    component: WorkOrders,
    meta: { title: '变更工单', roles: ['dba', 'developer'] }
  },
  {
    path: '/datasources',
    name: 'datasources',
    component: DataSources,
    meta: { title: '数据源管理', roles: ['dba'] }
  },
  {
    path: '/audit-logs',
    name: 'audit-logs',
    component: AuditLogs,
    meta: { title: '审计日志', roles: ['dba'] }
  },
  {
    path: '/risk-rules',
    name: 'risk-rules',
    component: RiskRules,
    meta: { title: '风险规则', roles: ['dba'] }
  },
  {
    path: '/masking-rules',
    name: 'masking-rules',
    component: MaskingRules,
    meta: { title: '脱敏规则', roles: ['dba'] }
  },
  {
    path: '/users',
    name: 'users',
    component: UserManagement,
    meta: { title: '用户管理', roles: ['dba'] }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const userStr = localStorage.getItem('user')
  const user = userStr ? JSON.parse(userStr) : null

  if (to.meta.public) {
    if (token && user) {
      next('/')
    } else {
      next()
    }
    return
  }

  if (!token || !user) {
    next('/login')
    return
  }

  if (to.meta.roles && to.meta.roles.length > 0) {
    if (!to.meta.roles.includes(user.role)) {
      next('/')
      return
    }
  }

  next()
})

export default router
