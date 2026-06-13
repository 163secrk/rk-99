<template>
  <el-container class="app-container">
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
        <el-menu-item index="/">
          <el-icon><Edit /></el-icon>
          <span>SQL编辑器</span>
        </el-menu-item>
        <el-menu-item index="/datasources">
          <el-icon><Coin /></el-icon>
          <span>数据源管理</span>
        </el-menu-item>
        <el-menu-item index="/risk-rules">
          <el-icon><Warning /></el-icon>
          <span>风险规则</span>
        </el-menu-item>
        <el-menu-item index="/masking-rules">
          <el-icon><Lock /></el-icon>
          <span>脱敏规则</span>
        </el-menu-item>
        <el-menu-item index="/audit-logs">
          <el-icon><Document /></el-icon>
          <span>审计日志</span>
        </el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
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
