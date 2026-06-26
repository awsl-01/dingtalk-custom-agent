<template>
  <div class="assets-page">
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
                <el-icon><Box /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.total || 0 }}</div>
                <div class="stat-label">资产总数</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="background: #67c23a">
                <el-icon><CircleCheck /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.status_count?.['在用'] || 0 }}</div>
                <div class="stat-label">在用</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="background: #e6a23c">
                <el-icon><Warning /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.status_count?.['借用中'] || 0 }}</div>
                <div class="stat-label">借用中</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="background: #f56c6c">
                <el-icon><CircleClose /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ (stats.status_count?.['闲置'] || 0) + (stats.status_count?.['维修中'] || 0) + (stats.status_count?.['报废'] || 0) }}</div>
                <div class="stat-label">闲置/维修/报废</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 资产列表 -->
      <el-card>
        <!-- 工具栏 -->
        <div class="tab-toolbar">
          <el-input v-model="searchKeyword" placeholder="搜索资产名称/编号/位置" clearable style="width: 260px" @clear="loadAssets" @keyup.enter="loadAssets">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="filterCategory" placeholder="分类筛选" clearable @change="loadAssets" style="width: 140px; margin-left: 12px;">
            <el-option label="教学设备" value="教学设备" />
            <el-option label="办公设备" value="办公设备" />
            <el-option label="家具" value="家具" />
            <el-option label="教材" value="教材" />
            <el-option label="其他" value="其他" />
          </el-select>
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable @change="loadAssets" style="width: 120px; margin-left: 12px;">
            <el-option label="在用" value="在用" />
            <el-option label="借用中" value="借用中" />
            <el-option label="闲置" value="闲置" />
            <el-option label="维修中" value="维修中" />
            <el-option label="报废" value="报废" />
          </el-select>
          <el-button type="primary" style="margin-left: 12px" @click="showAddDialog">
            <el-icon><Plus /></el-icon> 新增资产
          </el-button>
          <el-button type="danger" :disabled="!selectedIds.length" @click="batchDelete">
            <el-icon><Delete /></el-icon> 批量删除 ({{ selectedIds.length }})
          </el-button>
        </div>

        <!-- 表格 -->
        <el-table :data="assets" v-loading="loading" stripe style="width: 100%" @selection-change="(val) => selectedIds = val.map(r => r.id)">
          <el-table-column type="selection" width="50" />
          <el-table-column prop="id" label="资产编号" min-width="170" show-overflow-tooltip />
          <el-table-column prop="name" label="资产名称" min-width="130" />
          <el-table-column prop="category" label="分类" min-width="100" />
          <el-table-column prop="location" label="存放位置" min-width="120" show-overflow-tooltip />
          <el-table-column prop="responsible_user" label="负责人" min-width="90" />
          <el-table-column label="状态" min-width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="使用班级" min-width="120" align="center">
            <template #default="{ row }">
              <template v-if="row.status === '在用' && row.class_name">
                <el-tag type="success" size="small">{{ row.class_name }} 使用中</el-tag>
              </template>
              <template v-else-if="row.status === '借用中' && row.class_name">
                <el-tag type="warning" size="small">{{ row.class_name }} 借用</el-tag>
              </template>
              <template v-else>
                <span style="color: #909399;">-</span>
              </template>
            </template>
          </el-table-column>
          <el-table-column prop="purchase_date" label="采购日期" min-width="110" />
          <el-table-column label="操作" width="200" fixed="right" align="center">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button type="primary" link size="small" @click="editItem(row)">
                  <el-icon><Edit /></el-icon> 编辑
                </el-button>
                <el-button type="info" link size="small" @click="viewDetail(row)">
                  <el-icon><View /></el-icon> 详情
                </el-button>
                <el-button v-if="row.status === '在用'" type="warning" link size="small" @click="borrowItem(row)">
                  <el-icon><Unlock /></el-icon> 借用
                </el-button>
                <el-button v-if="row.status === '借用中'" type="success" link size="small" @click="returnItem(row)">
                  <el-icon><Lock /></el-icon> 归还
                </el-button>
                <el-dropdown trigger="click" @command="(cmd) => changeStatus(row, cmd)">
                  <el-button type="warning" link size="small">
                    <el-icon><Setting /></el-icon> 状态
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item v-if="row.status !== '在用'" command="在用">设为 在用</el-dropdown-item>
                      <el-dropdown-item v-if="row.status !== '借用中'" command="借用中">设为 借用中</el-dropdown-item>
                      <el-dropdown-item v-if="row.status !== '闲置'" command="闲置">设为 闲置</el-dropdown-item>
                      <el-dropdown-item v-if="row.status !== '维修中'" command="维修中">设为 维修中</el-dropdown-item>
                      <el-dropdown-item v-if="row.status !== '报废'" command="报废">设为 报废</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-button type="danger" link size="small" @click="deleteSingle(row.id)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- ========== 新增/编辑弹窗 ========== -->
      <el-dialog v-model="editDialogVisible" :title="isEdit ? '编辑资产' : '新增资产'" width="560px" @close="resetForm">
        <el-form :model="editForm" label-width="100px">
          <el-form-item label="资产名称" required>
            <el-input v-model="editForm.name" placeholder="请输入资产名称" />
          </el-form-item>
          <el-form-item label="分类">
            <el-select v-model="editForm.category" placeholder="选择分类">
              <el-option label="教学设备" value="教学设备" />
              <el-option label="办公设备" value="办公设备" />
              <el-option label="家具" value="家具" />
              <el-option label="教材" value="教材" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>
          <el-form-item label="存放位置">
            <el-input v-model="editForm.location" placeholder="如：301教室、办公室" />
          </el-form-item>
          <el-form-item label="负责人">
            <el-input v-model="editForm.responsible_user" placeholder="请输入负责人" />
          </el-form-item>
          <el-form-item label="使用班级">
            <el-input v-model="editForm.class_name" placeholder="如：三年级1班" />
          </el-form-item>
          <el-form-item label="采购日期">
            <el-input v-model="editForm.purchase_date" placeholder="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="editForm.description" type="textarea" :rows="2" placeholder="资产补充描述" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitEdit" :loading="submitting">保存</el-button>
        </template>
      </el-dialog>

      <!-- ========== 借用弹窗 ========== -->
      <el-dialog v-model="borrowDialogVisible" title="借用资产" width="400px">
        <el-form :model="borrowForm" label-width="80px">
          <el-form-item label="资产编号">
            <el-input :value="borrowForm.asset_id" disabled />
          </el-form-item>
          <el-form-item label="资产名称">
            <el-input :value="borrowForm.asset_name" disabled />
          </el-form-item>
          <el-form-item label="借用人" required>
            <el-input v-model="borrowForm.borrower" placeholder="请输入借用人姓名" />
          </el-form-item>
          <el-form-item label="借用班级">
            <el-input v-model="borrowForm.class_name" placeholder="如：三年级1班" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="borrowDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitBorrow" :loading="submitting">确认借用</el-button>
        </template>
      </el-dialog>

      <!-- ========== 详情弹窗 ========== -->
      <el-dialog v-model="detailDialogVisible" title="资产详情" width="600px">
        <template v-if="detailAsset">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="资产编号">{{ detailAsset.id }}</el-descriptions-item>
            <el-descriptions-item label="资产名称">{{ detailAsset.name }}</el-descriptions-item>
            <el-descriptions-item label="分类">{{ detailAsset.category }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="getStatusType(detailAsset.status)" size="small">{{ detailAsset.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="存放位置">{{ detailAsset.location }}</el-descriptions-item>
            <el-descriptions-item label="负责人">{{ detailAsset.responsible_user }}</el-descriptions-item>
            <el-descriptions-item label="使用班级">
              <template v-if="detailAsset.status === '在用' && detailAsset.class_name">
                <el-tag type="success" size="small">{{ detailAsset.class_name }} 使用中</el-tag>
              </template>
              <template v-else-if="detailAsset.status === '借用中' && detailAsset.class_name">
                <el-tag type="warning" size="small">{{ detailAsset.class_name }} 借用中</el-tag>
              </template>
              <template v-else>
                <span style="color: #909399;">-</span>
              </template>
            </el-descriptions-item>
            <el-descriptions-item label="采购日期">{{ detailAsset.purchase_date }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ detailAsset.created_at }}</el-descriptions-item>
            <el-descriptions-item label="更新时间" :span="2">{{ detailAsset.updated_at }}</el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">{{ detailAsset.description || '无' }}</el-descriptions-item>
          </el-descriptions>

          <!-- 借用记录 -->
          <div v-if="detailAsset.borrow_records?.length" style="margin-top: 16px;">
            <h4>借用记录</h4>
            <el-table :data="detailAsset.borrow_records" stripe size="small">
              <el-table-column prop="borrower" label="借用人" width="120" />
              <el-table-column prop="borrow_date" label="借用时间" min-width="160" />
              <el-table-column label="归还时间" min-width="160">
                <template #default="{ row }">
                  <el-tag v-if="row.return_date" type="success" size="small">{{ row.return_date }}</el-tag>
                  <el-tag v-else type="warning" size="small">未归还</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, inject, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const currentOrg = inject('currentOrg', ref(''))

const loading = ref(false)
const submitting = ref(false)
const assets = ref([])
const stats = ref({})
const selectedIds = ref([])

// 筛选
const searchKeyword = ref('')
const filterCategory = ref('')
const filterStatus = ref('')

// 编辑弹窗
const editDialogVisible = ref(false)
const isEdit = ref(false)
const editForm = ref({})
const editItemId = ref('')

// 借用弹窗
const borrowDialogVisible = ref(false)
const borrowForm = ref({ asset_id: '', asset_name: '', borrower: '', class_name: '' })

// 详情弹窗
const detailDialogVisible = ref(false)
const detailAsset = ref(null)

const goToDashboard = () => router.push('/dashboard')

const getStatusType = (s) => ({
  '在用': 'success', '借用中': 'warning', '闲置': 'info', '维修中': 'danger', '报废': 'danger'
})[s] || 'info'

// ========== 数据加载 ==========
const loadAssets = async () => {
  loading.value = true
  try {
    const params = {}
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (filterCategory.value) params.category = filterCategory.value
    if (filterStatus.value) params.status = filterStatus.value
    const res = await axios.get('/api/assets/list', { params })
    assets.value = res.data.assets || []
  } catch (e) { console.error('加载资产失败:', e) }
  finally { loading.value = false }
}

const loadStats = async () => {
  try {
    const res = await axios.get('/api/assets/stats')
    stats.value = res.data
  } catch (e) { console.error('加载统计失败:', e) }
}

const loadAll = () => { loadAssets(); loadStats() }

// ========== 状态变更 ==========
const changeStatus = async (row, newStatus) => {
  const labels = { '在用': '在用', '借用中': '借用中', '闲置': '闲置', '维修中': '维修中', '报废': '报废' }
  try {
    await ElMessageBox.confirm(
      `确定要将资产「${row.name}」状态变更为「${labels[newStatus] || newStatus}」吗？`,
      '变更状态',
      { type: 'warning' }
    )
    await axios.put(`/api/assets/update/${row.id}`, { status: newStatus })
    ElMessage.success(`状态已变更为「${labels[newStatus]}」`)
    loadAll()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('变更失败')
  }
}

// ========== 新增/编辑 ==========
const showAddDialog = () => {
  isEdit.value = false
  editForm.value = { name: '', category: '教学设备', location: '', responsible_user: '', purchase_date: '', description: '', class_name: '' }
  editDialogVisible.value = true
}

const editItem = (row) => {
  isEdit.value = true
  editItemId.value = row.id
  editForm.value = { ...row }
  editDialogVisible.value = true
}

const resetForm = () => { editForm.value = {}; submitting.value = false }

const submitEdit = async () => {
  if (!editForm.value.name?.trim()) {
    ElMessage.warning('请输入资产名称')
    return
  }
  submitting.value = true
  try {
    if (isEdit.value) {
      await axios.put(`/api/assets/update/${editItemId.value}`, editForm.value)
      ElMessage.success('更新成功')
    } else {
      await axios.post('/api/assets/create', editForm.value)
      ElMessage.success('新增成功')
    }
    editDialogVisible.value = false
    loadAll()
  } catch (e) {
    ElMessage.error('操作失败: ' + (e.response?.data?.detail || e.message))
  } finally { submitting.value = false }
}

// ========== 借用/归还 ==========
const borrowItem = (row) => {
  borrowForm.value = { asset_id: row.id, asset_name: row.name, borrower: '', class_name: row.class_name || '' }
  borrowDialogVisible.value = true
}

const submitBorrow = async () => {
  if (!borrowForm.value.borrower?.trim()) {
    ElMessage.warning('请输入借用人')
    return
  }
  submitting.value = true
  try {
    await axios.post(`/api/assets/borrow/${borrowForm.value.asset_id}`, {
      borrower: borrowForm.value.borrower,
      class_name: borrowForm.value.class_name
    })
    ElMessage.success('借用成功')
    borrowDialogVisible.value = false
    loadAll()
  } catch (e) {
    ElMessage.error('借用失败: ' + (e.response?.data?.detail || e.message))
  } finally { submitting.value = false }
}

const returnItem = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要归还资产「${row.name}」吗？`, '归还确认', { type: 'warning' })
    await axios.post(`/api/assets/return/${row.id}`)
    ElMessage.success('归还成功')
    loadAll()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('归还失败')
  }
}

// ========== 详情 ==========
const viewDetail = async (row) => {
  try {
    const res = await axios.get(`/api/assets/detail/${row.id}`)
    detailAsset.value = res.data
    detailDialogVisible.value = true
  } catch (e) {
    ElMessage.error('加载详情失败')
  }
}

// ========== 删除 ==========
const deleteSingle = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这条资产记录吗？', '确认删除', { type: 'warning' })
    await axios.delete(`/api/assets/delete/${id}`)
    ElMessage.success('已删除')
    loadAll()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const batchDelete = async () => {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedIds.value.length} 条记录吗？`, '批量删除', { type: 'warning' })
    const res = await axios.delete('/api/assets/batch', { data: { ids: selectedIds.value } })
    ElMessage.success(`已删除 ${res.data.deleted || selectedIds.value.length} 条`)
    selectedIds.value = []
    loadAll()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('批量删除失败')
  }
}

// ========== 生命周期 ==========
watch(currentOrg, () => loadAll())
onMounted(() => loadAll())
</script>

<style scoped>
.assets-page { display: flex; flex-direction: column; gap: 16px; }
.stats-row { margin-bottom: 0; }
.stat-card { height: 100%; }
.stat-content { display: flex; align-items: center; gap: 16px; }
.stat-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: white; font-size: 24px; }
.action-buttons { display: flex; flex-wrap: wrap; justify-content: center; gap: 2px 4px; }
.stat-info { flex: 1; }
.stat-value { font-size: 24px; font-weight: 600; color: #303133; }
.stat-label { font-size: 14px; color: #909399; margin-top: 4px; }
.tab-toolbar { display: flex; justify-content: flex-start; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
</style>
