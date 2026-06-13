<template>
  <div v-if="!isLoggedIn">
    <router-view />
  </div>
  <el-container v-else class="app-container">
    <el-header class="app-header">
      <div class="header-left">
        <el-icon class="logo-icon" :size="28" color="#409eff"><Monitor /></el-icon>
        <h1 class="app-title">数据库查询审计系统</h1>
      </div>
      <el-menu
        mode="horizontal"
        :router="true"
        :default-active="$route.path"
        class="header-menu"
        background-color="transparent"
        text-color="#fff"
        active-text-color="#ffd04b"
      >
        <el-menu-item v-if="isDba" index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>审计看板</span>
        </el-menu-item>
        <el-menu-item index="/">
          <el-icon><Edit /></el-icon>
          <span>SQL编辑器</span>
        </el-menu-item>
        <el-menu-item index="/my-logs">
          <el-icon><Memo /></el-icon>
          <span>我的记录</span>
        </el-menu-item>
        <el-menu-item v-if="isDba" index="/datasources">
          <el-icon><Coin /></el-icon>
          <span>数据源管理</span>
        </el-menu-item>
        <el-menu-item v-if="isDba" index="/risk-rules">
          <el-icon><Warning /></el-icon>
          <span>风险规则</span>
        </el-menu-item>
        <el-menu-item v-if="isDba" index="/masking-rules">
          <el-icon><Lock /></el-icon>
          <span>脱敏规则</span>
        </el-menu-item>
        <el-menu-item v-if="isDba" index="/audit-logs">
          <el-icon><Document /></el-icon>
          <span>审计日志</span>
        </el-menu-item>
        <el-menu-item v-if="isDba" index="/users">
          <el-icon><UserFilled /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
      </el-menu>
      <div class="header-right">
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-icon><User /></el-icon>
            <span class="username">{{ currentUser?.username }}</span>
            <el-tag size="small" :type="isDba ? 'danger' : 'success'">
              {{ isDba ? 'DBA' : '开发者' }}
            </el-tag>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>个人信息
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Monitor, Edit, Memo, Coin, Warning, Lock, Document, User, UserFilled, ArrowDown, SwitchButton, DataAnalysis } from '@element-plus/icons-vue'

const router = useRouter()
const currentUser = ref(null)

const isLoggedIn = computed(() => {
  const token = localStorage.getItem('token')
  const userStr = localStorage.getItem('user')
  if (token && userStr) {
    if (!currentUser.value) {
      currentUser.value = JSON.parse(userStr)
    }
    return true
  }
  return false
})

const isDba = computed(() => {
  return currentUser.value?.role === 'dba'
})

const loadUser = () => {
  const userStr = localStorage.getItem('user')
  if (userStr) {
    currentUser.value = JSON.parse(userStr)
  }
}

const handleCommand = (command) => {
  if (command === 'logout') {
    handleLogout()
  } else if (command === 'profile') {
    ElMessageBox.alert(
      `用户名：${currentUser.value?.username}\n角色：${currentUser.value?.role === 'dba' ? 'DBA' : '开发者'}\n状态：${currentUser.value?.is_active ? '正常' : '禁用'}`,
      '个人信息',
      {
        confirmButtonText: '确定',
        type: 'info'
      }
    )
  }
}

const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    currentUser.value = null
    ElMessage.success('已退出登录')
    router.push('/login')
  }).catch(() => {})
}

onMounted(() => {
  loadUser()
})
</script>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  padding: 0 24px;
  color: #fff;
  height: 64px !important;
}

.header-left {
  display: flex;
  align-items: center;
  margin-right: 40px;
}

.logo-icon {
  margin-right: 12px;
}

.app-title {
  font-size: 20px;
  margin: 0;
  font-weight: 600;
  white-space: nowrap;
}

.header-menu {
  border-bottom: none;
  flex: 1;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #fff;
  padding: 0 8px;
}

.user-info:hover {
  opacity: 0.8;
}

.username {
  font-size: 14px;
}

:deep(.el-menu--horizontal > .el-menu-item) {
  color: #fff !important;
  border-bottom: none;
  height: 64px;
  line-height: 64px;
}

:deep(.el-menu--horizontal > .el-menu-item:hover) {
  background-color: rgba(255, 255, 255, 0.1);
}

:deep(.el-menu--horizontal > .el-menu-item.is-active) {
  color: #ffd04b !important;
  border-bottom: none;
}

.app-main {
  padding: 20px;
  background: #f5f7fa;
  flex: 1;
  overflow: auto;
}
</style>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body, html {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

#app {
  height: 100%;
}
</style>
