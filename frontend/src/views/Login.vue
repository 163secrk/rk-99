<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <el-icon class="logo-icon" :size="48" color="#409eff"><Monitor /></el-icon>
        <h1 class="app-title">数据库查询审计系统</h1>
        <p class="app-subtitle">Database Query Audit System</p>
      </div>

      <el-card class="login-card">
        <el-tabs v-model="activeTab" class="login-tabs">
          <el-tab-pane label="登录" name="login">
            <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" label-width="0">
              <el-form-item prop="username">
                <el-input v-model="loginForm.username" placeholder="用户名" size="large" :prefix-icon="User">
                </el-input>
              </el-form-item>
              <el-form-item prop="password">
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  placeholder="密码"
                  size="large"
                  show-password
                  :prefix-icon="Lock"
                  @keyup.enter="handleLogin"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" size="large" style="width: 100%" :loading="loggingIn" @click="handleLogin">
                  登 录
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="注册" name="register">
            <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" label-width="0">
              <el-form-item prop="username">
                <el-input v-model="registerForm.username" placeholder="用户名" size="large" :prefix-icon="User">
                </el-input>
              </el-form-item>
              <el-form-item prop="password">
                <el-input
                  v-model="registerForm.password"
                  type="password"
                  placeholder="密码"
                  size="large"
                  show-password
                  :prefix-icon="Lock"
                />
              </el-form-item>
              <el-form-item prop="confirmPassword">
                <el-input
                  v-model="registerForm.confirmPassword"
                  type="password"
                  placeholder="确认密码"
                  size="large"
                  show-password
                  :prefix-icon="Lock"
                  @keyup.enter="handleRegister"
                />
              </el-form-item>
              <el-form-item>
                <el-radio-group v-model="registerForm.role" size="large" style="width: 100%" disabled>
                  <el-radio value="developer">开发者</el-radio>
                </el-radio-group>
                <div class="role-tip">注册默认为开发者角色，DBA角色由管理员分配</div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" size="large" style="width: 100%" :loading="registering" @click="handleRegister">
                  注 册
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>

        <div class="login-tips">
          <p>测试账号：</p>
          <p>DBA：admin / admin123</p>
          <p>开发者：developer / dev123456</p>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Monitor, User, Lock } from '@element-plus/icons-vue'
import { authApi } from '@/api'

const router = useRouter()
const activeTab = ref('login')
const loginFormRef = ref(null)
const registerFormRef = ref(null)
const loggingIn = ref(false)
const registering = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  role: 'developer'
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为 3-50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 100, message: '密码长度为 6-100 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  try {
    await loginFormRef.value.validate()
  } catch (e) {
    return
  }

  loggingIn.value = true
  try {
    const result = await authApi.login(loginForm.username, loginForm.password)
    localStorage.setItem('token', result.access_token)
    localStorage.setItem('user', JSON.stringify(result.user))
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '登录失败'
    ElMessage.error(msg)
  } finally {
    loggingIn.value = false
  }
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  try {
    await registerFormRef.value.validate()
  } catch (e) {
    return
  }

  registering.value = true
  try {
    const result = await authApi.register({
      username: registerForm.username,
      password: registerForm.password,
      role: registerForm.role
    })
    localStorage.setItem('token', result.access_token)
    localStorage.setItem('user', JSON.stringify(result.user))
    ElMessage.success('注册成功')
    router.push('/')
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '注册失败'
    ElMessage.error(msg)
  } finally {
    registering.value = false
  }
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-container {
  text-align: center;
}

.login-header {
  margin-bottom: 24px;
}

.logo-icon {
  margin-bottom: 12px;
}

.app-title {
  font-size: 28px;
  color: #fff;
  margin: 0 0 8px 0;
  font-weight: 600;
}

.app-subtitle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
}

.login-card {
  width: 400px;
  padding: 12px 8px;
}

.login-tabs {
  margin-bottom: 8px;
}

.login-tips {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
  font-size: 12px;
  color: #909399;
  text-align: left;
}

.login-tips p {
  margin: 4px 0;
}

.role-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
