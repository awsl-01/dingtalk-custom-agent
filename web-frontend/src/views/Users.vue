<template>
  <div class="users">
    <!-- 未选择组织提示 -->
    <el-empty v-if="!currentOrg" description="请先在右上角选择一个组织">
      <el-button type="primary" @click="goToDashboard">返回仪表盘</el-button>
    </el-empty>

    <template v-else>
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409eff">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ userStats.total || 0 }}</div>
              <div class="stat-label">总用户数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #f56c6c">
              <el-icon><UserFilled /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ userStats.by_role?.admin || 0 }}</div>
              <div class="stat-label">管理员</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67c23a">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ userStats.by_role?.teacher || 0 }}</div>
              <div class="stat-label">教师</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #e6a23c">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ userStats.by_role?.student || 0 }}</div>
              <div class="stat-label">学生</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选和操作 -->
    <el-card class="filter-card">
      <el-form :inline="true">
        <el-form-item label="角色筛选">
          <el-select v-model="filterRole" placeholder="全部角色" clearable @change="loadUsers">
            <el-option
              v-for="(role, key) in rolesConfig"
              :key="key"
              :label="role.name"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadUsers">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
          <el-button type="success" @click="showAddUser">
            <el-icon><Plus /></el-icon> 添加用户
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 用户列表 -->
    <el-card class="list-card">
      <template #header>
        <div class="card-header">
          <span>用户列表 ({{ users.length }} 人)</span>
        </div>
      </template>

      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="user_id" label="用户ID" width="140" show-overflow-tooltip />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="role_name" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="getRoleType(row.role)" size="small">
              {{ row.role_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="department" label="部门" width="120">
          <template #default="{ row }">
            {{ row.department || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="权限" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="perm in row.permission_names"
              :key="perm"
              size="small"
              type="info"
              style="margin-right: 4px; margin-bottom: 4px;"
            >
              {{ perm }}
            </el-tag>
            <span v-if="!row.permissions?.length">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showEditUser(row)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button type="warning" link size="small" @click="showPermissionDialog(row)">
              <el-icon><Lock /></el-icon> 权限
            </el-button>
            <el-popconfirm
              title="确定要删除这个用户吗？"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button type="danger" link size="small">
                  <el-icon><Delete /></el-icon> 删除
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑用户对话框 -->
    <el-dialog
      v-model="userDialogVisible"
      :title="isEdit ? '编辑用户' : '添加用户'"
      width="500px"
    >
      <el-form :model="userForm" label-width="80px">
        <el-form-item label="用户ID">
          <el-input v-model="userForm.user_id" :disabled="isEdit" placeholder="请输入用户ID" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="userForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userForm.role" placeholder="请选择角色">
            <el-option
              v-for="(role, key) in rolesConfig"
              :key="key"
              :label="role.name"
              :value="key"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="userForm.department" placeholder="请输入部门" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveUser" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 权限管理对话框 -->
    <el-dialog
      v-model="permissionDialogVisible"
      title="管理权限"
      width="500px"
    >
      <div v-if="currentEditUser" class="permission-dialog">
        <div class="user-info">
          <p><strong>用户：</strong>{{ currentEditUser.name }} ({{ currentEditUser.user_id }})</p>
          <p><strong>当前角色：</strong>{{ currentEditUser.role_name }}</p>
        </div>
        <el-divider />
        <div class="permission-list">
          <p><strong>访问权限：</strong></p>
          <el-checkbox-group v-model="selectedPermissions">
            <el-checkbox
              v-for="(perm, key) in permissionsConfig"
              :key="key"
              :label="key"
              :disabled="key === 'admin' && !isAdmin"
            >
              {{ perm.name }} - {{ perm.description }}
            </el-checkbox>
          </el-checkbox-group>
        </div>
        <el-divider />
        <div class="role-change" v-if="isAdmin">
          <p><strong>修改角色：</strong></p>
          <el-select v-model="selectedRole" placeholder="选择新角色">
            <el-option
              v-for="(role, key) in rolesConfig"
              :key="key"
              :label="role.name"
              :value="key"
            />
          </el-select>
        </div>
      </div>
      <template #footer>
        <el-button @click="permissionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="savePermissions" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { userApi } from '../api'

const router = useRouter()
const currentOrg = inject('currentOrg', ref(''))

const loading = ref(false)
const saving = ref(false)
const users = ref([])
const userStats = ref({})
const rolesConfig = ref({})
const permissionsConfig = ref({})
const filterRole = ref('')

// 用户表单
const userDialogVisible = ref(false)
const isEdit = ref(false)
const userForm = ref({
  user_id: '',
  name: '',
  role: 'teacher',
  department: '',
})

// 权限管理
const permissionDialogVisible = ref(false)
const currentEditUser = ref(null)
const selectedPermissions = ref([])
const selectedRole = ref('')

const isAdmin = computed(() => {
  // 检查当前用户是否是管理员（这里简化处理，实际应该从登录状态获取）
  return true
})

const getRoleType = (role) => {
  const types = {
    admin: 'danger',
    principal: 'warning',
    director: '',
    teacher: 'success',
    student: 'info',
  }
  return types[role] || 'info'
}

const goToDashboard = () => {
  router.push('/dashboard')
}

const loadUsers = async () => {
  if (!currentOrg.value) {
    users.value = []
    return
  }

  loading.value = true
  try {
    const [usersRes, statsRes, rolesRes, permsRes] = await Promise.all([
      userApi.getList(currentOrg.value, { role: filterRole.value || undefined }),
      userApi.getStats(currentOrg.value),
      userApi.getRoles(),
      userApi.getPermissions(),
    ])
    users.value = usersRes.users || []
    userStats.value = statsRes
    rolesConfig.value = rolesRes.roles || {}
    permissionsConfig.value = permsRes.permissions || {}
  } catch (error) {
    console.error('加载用户数据失败:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const showAddUser = () => {
  isEdit.value = false
  userForm.value = {
    user_id: '',
    name: '',
    role: 'teacher',
    department: '',
  }
  userDialogVisible.value = true
}

const showEditUser = (user) => {
  isEdit.value = true
  userForm.value = {
    user_id: user.user_id,
    name: user.name,
    role: user.role,
    department: user.department || '',
  }
  userDialogVisible.value = true
}

const saveUser = async () => {
  if (!userForm.value.user_id || !userForm.value.name) {
    ElMessage.warning('请填写必要信息')
    return
  }

  saving.value = true
  try {
    if (isEdit.value) {
      await userApi.update(userForm.value.user_id, currentOrg.value, {
        name: userForm.value.name,
        role: userForm.value.role,
        department: userForm.value.department,
      })
    } else {
      await userApi.create(currentOrg.value, userForm.value)
    }
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    userDialogVisible.value = false
    loadUsers()
  } catch (error) {
    ElMessage.error('操作失败')
    console.error('保存用户失败:', error)
  } finally {
    saving.value = false
  }
}

const handleDelete = async (user) => {
  try {
    await userApi.delete(user.user_id, currentOrg.value)
    ElMessage.success('删除成功')
    loadUsers()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const showPermissionDialog = (user) => {
  currentEditUser.value = user
  selectedPermissions.value = [...(user.permissions || [])]
  selectedRole.value = user.role
  permissionDialogVisible.value = true
}

const savePermissions = async () => {
  saving.value = true
  try {
    await userApi.update(currentEditUser.value.user_id, currentOrg.value, {
      permissions: selectedPermissions.value,
      role: selectedRole.value,
    })
    ElMessage.success('权限更新成功')
    permissionDialogVisible.value = false
    loadUsers()
  } catch (error) {
    ElMessage.error('更新失败')
    console.error('保存权限失败:', error)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.users {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stats-row {
  margin-bottom: 0;
}

.stat-card {
  height: 100%;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.filter-card :deep(.el-card__body) {
  padding-bottom: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.permission-dialog .user-info {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 8px;
}

.permission-dialog .user-info p {
  margin: 4px 0;
}

.permission-dialog .permission-list {
  margin: 16px 0;
}

.permission-dialog .permission-list .el-checkbox {
  display: block;
  margin-bottom: 8px;
}

.permission-dialog .role-change {
  margin-top: 16px;
}
</style>
