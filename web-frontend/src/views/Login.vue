<template>
  <div class="login-container">
    <div class="login-card">
      <!-- Logo 和标题 -->
      <div class="login-header">
        <div class="logo">🏫</div>
        <h1 class="title">校园智能助手</h1>
        <p class="subtitle">钉钉机器人管理后台</p>
      </div>

      <!-- 登录表单 -->
      <div class="login-content">
        <el-form :model="loginForm" :rules="rules" ref="formRef" label-width="0">
          <el-form-item prop="userName">
            <el-input
              v-model="loginForm.userName"
              placeholder="请输入您的姓名"
              size="large"
              prefix-icon="User"
            />
          </el-form-item>
          <el-form-item prop="userId">
            <el-input
              v-model="loginForm.userId"
              placeholder="请输入工号（如：T001）"
              size="large"
              prefix-icon="Ticket"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              size="large"
              class="login-btn"
              @click="handleLogin"
              :loading="loading"
            >
              登录
            </el-button>
          </el-form-item>
        </el-form>

        <!-- 提示信息 -->
        <div class="login-tips">
          <p><el-icon><InfoFilled /></el-icon> 工号格式：教师 T001，学生 S001，管理员 A001</p>
        </div>
      </div>

      <!-- 底部信息 -->
      <div class="login-footer">
        <p>登录后可进行调课审批、查看排课等操作</p>
        <p class="version">v1.0.0</p>
      </div>
    </div>

    <!-- 背景装饰 -->
    <div class="login-bg">
      <div class="bg-circle circle-1"></div>
      <div class="bg-circle circle-2"></div>
      <div class="bg-circle circle-3"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const route = useRoute()

const formRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  userName: '',
  userId: '',
})

const rules = {
  userName: [
    { required: true, message: '请输入您的姓名', trigger: 'blur' },
    { min: 2, max: 20, message: '姓名长度为 2-20 个字符', trigger: 'blur' }
  ],
  userId: [
    { required: true, message: '请输入工号', trigger: 'blur' },
    { pattern: /^[A-Za-z]\d{3,10}$/, message: '工号格式：字母+数字（如 T001）', trigger: 'blur' }
  ]
}

// 登录
const handleLogin = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      const res = await axios.post('/api/auth/simple-login', {
        user_name: loginForm.userName,
        user_id: loginForm.userId,
      })

      const { token, user } = res.data

      // 保存 token 和用户信息
      localStorage.setItem('dingtalk_token', token)
      localStorage.setItem('dingtalk_user_info', JSON.stringify(user))

      ElMessage.success('登录成功')

      // 跳转到之前访问的页面或主页
      const redirect = route.query.redirect || '/dashboard'
      router.push(redirect)
    } catch (error) {
      const msg = error.response?.data?.detail || '登录失败，请重试'
      ElMessage.error(msg)
    } finally {
      loading.value = false
    }
  })
}

onMounted(() => {
  // 检查是否已登录
  const token = localStorage.getItem('dingtalk_token')
  if (token) {
    router.push('/dashboard')
  }
})
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
}

.login-card {
  width: 400px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  padding: 40px;
  position: relative;
  z-index: 10;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo {
  font-size: 64px;
  margin-bottom: 16px;
}

.title {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px 0;
}

.subtitle {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.login-content {
  min-height: 200px;
}

.login-btn {
  width: 100%;
}

.login-tips {
  margin-top: 16px;
  text-align: center;
  color: #909399;
  font-size: 12px;
}

.login-tips p {
  margin: 8px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.login-footer {
  margin-top: 32px;
  text-align: center;
  color: #c0c4cc;
  font-size: 12px;
}

.login-footer p {
  margin: 4px 0;
}

.version {
  margin-top: 8px;
}

/* 背景装饰 */
.login-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
  pointer-events: none;
}

.bg-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
}

.circle-1 {
  width: 400px;
  height: 400px;
  top: -100px;
  right: -100px;
}

.circle-2 {
  width: 300px;
  height: 300px;
  bottom: -80px;
  left: -80px;
}

.circle-3 {
  width: 200px;
  height: 200px;
  bottom: 20%;
  right: 10%;
}
</style>
