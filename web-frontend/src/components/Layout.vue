<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <span v-if="!isCollapse">🤖 钉钉助手管理</span>
        <span v-else>🤖</span>
      </div>
      <el-menu
        :default-active="currentRoute"
        :collapse="isCollapse"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>
        <el-menu-item index="/knowledge">
          <el-icon><Collection /></el-icon>
          <template #title>知识库</template>
        </el-menu-item>
        <el-menu-item index="/messages">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>消息日志</template>
        </el-menu-item>
        <el-menu-item index="/users">
          <el-icon><User /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>
        <el-menu-item index="/scheduling">
          <el-icon><Calendar /></el-icon>
          <template #title>排课系统</template>
        </el-menu-item>
        <el-menu-item index="/inspection">
          <el-icon><Warning /></el-icon>
          <template #title>巡检管理</template>
        </el-menu-item>
        <el-menu-item index="/assets">
          <el-icon><Box /></el-icon>
          <template #title>资产管理</template>
        </el-menu-item>
        <el-menu-item index="/debug">
          <el-icon><Monitor /></el-icon>
          <template #title>对话调试</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon
            class="collapse-btn"
            @click="isCollapse = !isCollapse"
          >
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <span class="page-title">{{ currentTitle }}</span>
        </div>
        <div class="header-right">
          <!-- 组织选择器 -->
          <div class="org-selector">
            <el-select
              v-model="currentOrg"
              placeholder="选择组织"
              :teleported="false"
              @change="handleOrgChange"
            >
              <el-option
                label="全部组织"
                value=""
              >
                <span style="display: flex; align-items: center; gap: 8px;">
                  <el-icon><OfficeBuilding /></el-icon>
                  <span>全部组织</span>
                </span>
              </el-option>
              <el-option
                v-for="org in organizations"
                :key="org.corp_id"
                :label="org.name"
                :value="org.corp_id"
              >
                <span style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
                  <span style="display: flex; align-items: center; gap: 8px;">
                    <el-icon><OfficeBuilding /></el-icon>
                    <span>{{ org.name }}</span>
                  </span>
                  <el-tag size="small" type="info">{{ org.message_count + org.file_count }}</el-tag>
                </span>
              </el-option>
            </el-select>
          </div>
          <!-- 修改组织名称按钮 -->
          <el-button
            v-if="currentOrg"
            type="primary"
            link
            @click="showEditOrgDialog"
          >
            <el-icon><Edit /></el-icon> 修改名称
          </el-button>
          <!-- 用户信息 -->
          <el-dropdown @command="handleUserCommand">
            <span class="user-dropdown">
              <el-icon><User /></el-icon>
              {{ currentUserName || '未登录' }}
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon> 个人信息
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-tag type="success" effect="plain">运行中</el-tag>
        </div>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>

    <!-- 修改组织名称对话框 -->
    <el-dialog
      v-model="editOrgVisible"
      title="修改组织名称"
      width="400px"
    >
      <el-form :model="editOrgForm" label-width="80px">
        <el-form-item label="组织ID">
          <el-input :value="editOrgForm.corp_id" disabled />
        </el-form-item>
        <el-form-item label="组织名称">
          <el-input v-model="editOrgForm.name" placeholder="请输入组织名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editOrgVisible = false">取消</el-button>
        <el-button type="primary" @click="saveOrgName" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 用户身份设置对话框 -->
    <el-dialog
      v-model="userDialogVisible"
      title="设置您的身份"
      width="400px"
    >
      <div class="user-dialog-tip">
        <el-icon><InfoFilled /></el-icon>
        <span>设置您的身份信息后，调课审批等操作将显示您的真实姓名</span>
      </div>
      <el-form :model="userForm" label-width="80px" style="margin-top: 16px;">
        <el-form-item label="您的姓名">
          <el-input v-model="userForm.userName" placeholder="请输入您的姓名" />
        </el-form-item>
        <el-form-item label="用户ID">
          <el-input v-model="userForm.userId" placeholder="请输入工号或用户ID（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveUserInfo">保存</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, provide } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { organizationApi, userInfo } from '../api'

const route = useRoute()
const isCollapse = ref(false)
const organizations = ref([])
const currentOrg = ref(localStorage.getItem('currentOrg') || '')

// 修改组织名称相关
const editOrgVisible = ref(false)
const editOrgForm = ref({
  corp_id: '',
  name: '',
})
const saving = ref(false)

// 用户信息相关
const userDialogVisible = ref(false)
const currentUserName = ref('')
const userForm = ref({
  userName: '',
  userId: '',
})

// 提供当前组织给子组件
provide('currentOrg', currentOrg)
provide('organizations', organizations)

const currentRoute = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '首页')

const loadOrganizations = async () => {
  try {
    const res = await organizationApi.getList()
    organizations.value = res.organizations || []
  } catch (error) {
    console.error('加载组织列表失败:', error)
  }
}

const handleOrgChange = (value) => {
  localStorage.setItem('currentOrg', value || '')
  console.log('组织切换:', value || '全部')
}

const showEditOrgDialog = () => {
  const org = organizations.value.find(o => o.corp_id === currentOrg.value)
  if (org) {
    editOrgForm.value = {
      corp_id: org.corp_id,
      name: org.name,
    }
    editOrgVisible.value = true
  }
}

const saveOrgName = async () => {
  if (!editOrgForm.value.name.trim()) {
    ElMessage.warning('请输入组织名称')
    return
  }

  saving.value = true
  try {
    await organizationApi.updateName(editOrgForm.value.corp_id, editOrgForm.value.name)
    ElMessage.success('修改成功')
    editOrgVisible.value = false
    // 重新加载组织列表
    await loadOrganizations()
  } catch (error) {
    ElMessage.error('修改失败')
    console.error('修改组织名称失败:', error)
  } finally {
    saving.value = false
  }
}

// 用户信息相关方法
const showUserDialog = () => {
  const stored = userInfo.get()
  userForm.value = {
    userName: stored?.user_name || '',
    userId: stored?.user_id || '',
  }
  userDialogVisible.value = true
}

const saveUserInfo = () => {
  if (!userForm.value.userName.trim()) {
    ElMessage.warning('请输入您的姓名')
    return
  }
  userInfo.set(userForm.value.userId || 'web_user', userForm.value.userName)
  currentUserName.value = userForm.value.userName
  userDialogVisible.value = false
  ElMessage.success('身份信息已保存')
}

const loadUserInfo = () => {
  const stored = userInfo.get()
  currentUserName.value = stored?.user_name || ''
}

// 用户下拉菜单命令处理
const handleUserCommand = (command) => {
  if (command === 'profile') {
    showUserDialog()
  } else if (command === 'logout') {
    handleLogout()
  }
}

// 退出登录
const handleLogout = async () => {
  try {
    // 调用后端退出登录 API
    const token = localStorage.getItem('dingtalk_token')
    if (token) {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }).catch(() => {})
    }
  } finally {
    // 清除本地存储
    localStorage.removeItem('dingtalk_token')
    localStorage.removeItem('dingtalk_user_info')

    ElMessage.success('已退出登录')

    // 跳转到登录页
    router.push('/login')
  }
}

onMounted(() => {
  loadOrganizations()
  loadUserInfo()
})
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.aside {
  background-color: #304156;
  transition: width 0.3s;
  overflow: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid #3d4a5a;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  box-shadow: 0 1px 4px rgba(0,21,41,.08);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #666;
}

.collapse-btn:hover {
  color: #409eff;
}

.page-title {
  font-size: 18px;
  font-weight: 500;
  color: #333;
}

.org-selector {
  width: 200px;
}

.main {
  background-color: #f0f2f5;
  padding: 20px;
}

.el-menu {
  border-right: none;
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 4px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: #606266;
  font-size: 14px;
}

.user-dropdown:hover {
  color: #409eff;
}

.user-dialog-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: #f0f9ff;
  border-radius: 6px;
  color: #409eff;
  font-size: 13px;
}
</style>
