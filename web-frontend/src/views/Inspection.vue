<template>
  <div class="inspection">
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
                <el-icon><Calendar /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.active_plans || 0 }}</div>
                <div class="stat-label">进行中计划</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="background: #67c23a">
                <el-icon><Location /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.total_points || 0 }}</div>
                <div class="stat-label">巡检点位</div>
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
                <div class="stat-value">{{ stats.pending_issues || 0 }}</div>
                <div class="stat-label">待处理问题</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="background: #f56c6c">
                <el-icon><Document /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ stats.pending_orders || 0 }}</div>
                <div class="stat-label">待处理工单</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 标签页 -->
      <el-card class="tabs-card">
        <el-tabs v-model="activeTab">
          <!-- ========== 巡检计划 ========== -->
          <el-tab-pane label="巡检计划" name="plans">
            <div class="tab-toolbar">
              <el-select v-model="planStatusFilter" placeholder="状态筛选" clearable @change="loadPlans">
                <el-option label="草稿" value="draft" />
                <el-option label="进行中" value="active" />
                <el-option label="已完成" value="completed" />
                <el-option label="已取消" value="cancelled" />
              </el-select>
              <el-button type="danger" :disabled="!selectedPlanIds.length" style="margin-left: 12px" @click="batchDelete('plan')">
                批量删除 ({{ selectedPlanIds.length }})
              </el-button>
            </div>
            <el-table :data="plans" v-loading="loading" stripe style="width: 100%" @selection-change="(val) => selectedPlanIds = val.map(r => r.plan_id)">
              <el-table-column type="selection" width="50" />
              <el-table-column prop="plan_name" label="计划名称" min-width="180" show-overflow-tooltip />
              <el-table-column prop="area_name" label="区域类型" min-width="110" />
              <el-table-column prop="category_name" label="检查类别" min-width="110" />
              <el-table-column label="状态" min-width="100" align="center">
                <template #default="{ row }">
                  <el-tag :type="getPlanStatusType(row.status)" size="small">{{ row.status_name }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="start_date" label="开始日期" min-width="130" />
              <el-table-column prop="end_date" label="结束日期" min-width="130" />
              <el-table-column label="操作" width="180" fixed="right" align="center">
                <template #default="{ row }">
                  <el-button type="primary" link size="small" @click="editItem('plan', row)">
                    <el-icon><Edit /></el-icon> 编辑
                  </el-button>
                  <el-button type="danger" link size="small" @click="deleteSingle('plan', row.plan_id)">
                    <el-icon><Delete /></el-icon> 删除
                  </el-button>
                  <el-button v-if="row.status === 'draft'" type="success" link size="small" @click="activatePlan(row)">
                    <el-icon><VideoPlay /></el-icon> 激活
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- ========== 巡检点位 ========== -->
          <el-tab-pane label="巡检点位" name="points">
            <div class="tab-toolbar">
              <el-button type="danger" :disabled="!selectedPointIds.length" @click="batchDelete('point')">
                批量删除 ({{ selectedPointIds.length }})
              </el-button>
            </div>
            <el-table :data="points" v-loading="loading" stripe style="width: 100%" @selection-change="(val) => selectedPointIds = val.map(r => r.point_id)">
              <el-table-column type="selection" width="50" />
              <el-table-column prop="point_name" label="点位名称" min-width="180" show-overflow-tooltip />
              <el-table-column prop="area_name" label="区域类型" min-width="120" />
              <el-table-column prop="location" label="位置" min-width="220" show-overflow-tooltip />
              <el-table-column label="状态" min-width="90" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="要求" min-width="140" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.requires_photo" size="small" type="warning" style="margin-right: 4px;">拍照</el-tag>
                  <el-tag v-if="row.requires_location" size="small" type="warning">定位</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150" fixed="right" align="center">
                <template #default="{ row }">
                  <el-button type="primary" link size="small" @click="editItem('point', row)">
                    <el-icon><Edit /></el-icon> 编辑
                  </el-button>
                  <el-button type="danger" link size="small" @click="deleteSingle('point', row.point_id)">
                    <el-icon><Delete /></el-icon> 删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- ========== 巡检记录 ========== -->
          <el-tab-pane label="巡检记录" name="records">
            <div class="tab-toolbar">
              <el-date-picker v-model="recordDateFilter" type="date" placeholder="选择日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" clearable @change="loadRecords" />
              <el-button type="danger" :disabled="!selectedRecordIds.length" style="margin-left: 12px" @click="batchDelete('record')">
                批量删除 ({{ selectedRecordIds.length }})
              </el-button>
            </div>
            <el-table :data="records" v-loading="loading" stripe style="width: 100%" @selection-change="(val) => selectedRecordIds = val.map(r => r.record_id)">
              <el-table-column type="selection" width="50" />
              <el-table-column prop="record_id" label="记录ID" min-width="160" show-overflow-tooltip />
              <el-table-column prop="inspector_name" label="巡检员" min-width="100" />
              <el-table-column prop="point_name" label="点位" min-width="140" show-overflow-tooltip />
              <el-table-column prop="check_in_time_str" label="签到时间" min-width="170" />
              <el-table-column prop="check_out_time_str" label="签退时间" min-width="170" />
              <el-table-column label="状态" min-width="100" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.check_out_time ? 'success' : 'warning'" size="small">
                    {{ row.check_out_time ? '已完成' : '进行中' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="照片" min-width="220">
                <template #default="{ row }">
                  <div v-if="row.photo_urls && row.photo_urls.length > 0" class="photo-cell">
                    <el-image v-for="(url, idx) in row.photo_urls.slice(0, 3)" :key="idx" :src="url" :preview-src-list="row.photo_urls" :initial-index="idx" fit="cover" class="record-photo" preview-teleported />
                    <el-tag v-if="row.photo_urls.length > 3" size="small" type="info" class="photo-more">+{{ row.photo_urls.length - 3 }}</el-tag>
                  </div>
                  <span v-else class="no-photo">无照片</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150" fixed="right" align="center">
                <template #default="{ row }">
                  <el-button type="primary" link size="small" @click="editItem('record', row)">
                    <el-icon><Edit /></el-icon> 编辑
                  </el-button>
                  <el-button type="danger" link size="small" @click="deleteSingle('record', row.record_id)">
                    <el-icon><Delete /></el-icon> 删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- ========== 问题管理 ========== -->
          <el-tab-pane label="问题管理" name="issues">
            <div class="tab-toolbar">
              <el-select v-model="issueStatusFilter" placeholder="状态筛选" clearable @change="loadIssues">
                <el-option label="待处理" value="pending" />
                <el-option label="已派单" value="assigned" />
                <el-option label="整改中" value="in_progress" />
                <el-option label="待复查" value="pending_review" />
                <el-option label="已解决" value="resolved" />
              </el-select>
              <el-select v-model="issueCategoryFilter" placeholder="分类筛选" clearable @change="loadIssues" style="margin-left: 12px;">
                <el-option label="安全隐患" value="safety_hazard" />
                <el-option label="卫生问题" value="hygiene_issue" />
                <el-option label="设施损坏" value="facility_damage" />
                <el-option label="纪律违规" value="discipline_violation" />
                <el-option label="消防安全" value="fire_safety" />
              </el-select>
              <el-button type="danger" :disabled="!selectedIssueIds.length" style="margin-left: 12px" @click="batchDelete('issue')">
                批量删除 ({{ selectedIssueIds.length }})
              </el-button>
            </div>
            <el-table :data="issues" v-loading="loading" stripe style="width: 100%" @selection-change="(val) => selectedIssueIds = val.map(r => r.issue_id)">
              <el-table-column type="selection" width="50" />
              <el-table-column prop="issue_id" label="问题编号" min-width="160" show-overflow-tooltip />
              <el-table-column prop="title" label="问题标题" min-width="220" show-overflow-tooltip />
              <el-table-column prop="category_name" label="分类" min-width="110" />
              <el-table-column label="严重程度" min-width="110" align="center">
                <template #default="{ row }">
                  <el-tag :type="getSeverityType(row.severity)" size="small">{{ row.severity_name }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="状态" min-width="110" align="center">
                <template #default="{ row }">
                  <el-tag :type="getIssueStatusType(row.status)" size="small">{{ row.status_name }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="reported_by_name" label="上报人" min-width="100" />
              <el-table-column prop="reported_at_str" label="上报时间" min-width="170" />
              <el-table-column label="操作" width="150" fixed="right" align="center">
                <template #default="{ row }">
                  <el-button type="primary" link size="small" @click="editItem('issue', row)">
                    <el-icon><Edit /></el-icon> 编辑
                  </el-button>
                  <el-button type="danger" link size="small" @click="deleteSingle('issue', row.issue_id)">
                    <el-icon><Delete /></el-icon> 删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- ========== 工单管理 ========== -->
          <el-tab-pane label="工单管理" name="orders">
            <div class="tab-toolbar">
              <el-select v-model="orderStatusFilter" placeholder="状态筛选" clearable @change="loadOrders">
                <el-option label="待处理" value="pending" />
                <el-option label="已派单" value="assigned" />
                <el-option label="整改中" value="in_progress" />
                <el-option label="待复查" value="pending_review" />
                <el-option label="已解决" value="resolved" />
              </el-select>
              <el-button type="danger" :disabled="!selectedOrderIds.length" style="margin-left: 12px" @click="batchDelete('order')">
                批量删除 ({{ selectedOrderIds.length }})
              </el-button>
            </div>
            <el-table :data="orders" v-loading="loading" stripe style="width: 100%" @selection-change="(val) => selectedOrderIds = val.map(r => r.order_id)">
              <el-table-column type="selection" width="50" />
              <el-table-column prop="order_id" label="工单编号" min-width="160" show-overflow-tooltip />
              <el-table-column prop="issue_id" label="关联问题" min-width="160" show-overflow-tooltip />
              <el-table-column prop="assigned_to_name" label="负责人" min-width="120" />
              <el-table-column label="状态" min-width="120" align="center">
                <template #default="{ row }">
                  <el-tag :type="getOrderStatusType(row.status)" size="small">{{ row.status_name }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at_str" label="创建时间" min-width="180" />
              <el-table-column label="操作" width="100" fixed="right" align="center">
                <template #default="{ row }">
                  <el-button type="danger" link size="small" @click="deleteSingle('order', row.order_id)">
                    <el-icon><Delete /></el-icon> 删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <!-- ========== 编辑弹窗 ========== -->
      <el-dialog v-model="editDialogVisible" :title="editDialogTitle" width="560px" @close="resetEditForm">
        <!-- 计划编辑 -->
        <template v-if="editType === 'plan'">
          <el-form :model="editForm" label-width="100px">
            <el-form-item label="计划名称"><el-input v-model="editForm.plan_name" /></el-form-item>
            <el-form-item label="开始日期"><el-input v-model="editForm.start_date" placeholder="YYYY-MM-DD" /></el-form-item>
            <el-form-item label="结束日期"><el-input v-model="editForm.end_date" placeholder="YYYY-MM-DD" /></el-form-item>
            <el-form-item label="描述"><el-input v-model="editForm.description" type="textarea" :rows="3" /></el-form-item>
          </el-form>
        </template>
        <!-- 点位编辑 -->
        <template v-else-if="editType === 'point'">
          <el-form :model="editForm" label-width="100px">
            <el-form-item label="点位名称"><el-input v-model="editForm.point_name" /></el-form-item>
            <el-form-item label="区域类型">
              <el-select v-model="editForm.area_type">
                <el-option label="教学区" value="teaching" />
                <el-option label="宿舍区" value="dormitory" />
                <el-option label="食堂" value="canteen" />
                <el-option label="操场" value="playground" />
                <el-option label="消防" value="fire" />
                <el-option label="公共区域" value="public" />
              </el-select>
            </el-form-item>
            <el-form-item label="位置"><el-input v-model="editForm.location" /></el-form-item>
            <el-form-item label="要求拍照"><el-switch v-model="editForm.requires_photo" /></el-form-item>
            <el-form-item label="要求定位"><el-switch v-model="editForm.requires_location" /></el-form-item>
            <el-form-item label="启用"><el-switch v-model="editForm.is_active" /></el-form-item>
          </el-form>
        </template>
        <!-- 记录编辑 -->
        <template v-else-if="editType === 'record'">
          <el-form :model="editForm" label-width="100px">
            <el-form-item label="备注"><el-input v-model="editForm.notes" type="textarea" :rows="3" /></el-form-item>
            <el-form-item label="总体状态">
              <el-select v-model="editForm.overall_status">
                <el-option label="正常" value="normal" />
                <el-option label="有问题" value="has_issues" />
              </el-select>
            </el-form-item>
          </el-form>
        </template>
        <!-- 问题编辑 -->
        <template v-else-if="editType === 'issue'">
          <el-form :model="editForm" label-width="100px">
            <el-form-item label="问题标题"><el-input v-model="editForm.title" /></el-form-item>
            <el-form-item label="问题描述"><el-input v-model="editForm.description" type="textarea" :rows="3" /></el-form-item>
            <el-form-item label="分类">
              <el-select v-model="editForm.category">
                <el-option label="安全隐患" value="safety_hazard" />
                <el-option label="卫生问题" value="hygiene_issue" />
                <el-option label="设施损坏" value="facility_damage" />
                <el-option label="纪律违规" value="discipline_violation" />
                <el-option label="消防安全" value="fire_safety" />
              </el-select>
            </el-form-item>
            <el-form-item label="严重程度">
              <el-select v-model="editForm.severity">
                <el-option label="低" value="low" />
                <el-option label="中" value="medium" />
                <el-option label="高" value="high" />
                <el-option label="严重" value="critical" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="editForm.status">
                <el-option label="待处理" value="pending" />
                <el-option label="已派单" value="assigned" />
                <el-option label="整改中" value="in_progress" />
                <el-option label="待复查" value="pending_review" />
                <el-option label="已解决" value="resolved" />
                <el-option label="已关闭" value="closed" />
              </el-select>
            </el-form-item>
          </el-form>
        </template>
        <template #footer>
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitEdit" :loading="editSubmitting">保存</el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, inject, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const currentOrg = inject('currentOrg', ref(''))

const loading = ref(false)
const activeTab = ref('plans')

// 统计数据
const stats = ref({})

// 数据
const plans = ref([])
const planStatusFilter = ref('')
const points = ref([])
const records = ref([])
const recordDateFilter = ref('')
const issues = ref([])
const issueStatusFilter = ref('')
const issueCategoryFilter = ref('')
const orders = ref([])
const orderStatusFilter = ref('')

// 批量选择
const selectedPlanIds = ref([])
const selectedPointIds = ref([])
const selectedRecordIds = ref([])
const selectedIssueIds = ref([])
const selectedOrderIds = ref([])

// 编辑弹窗
const editDialogVisible = ref(false)
const editDialogTitle = ref('')
const editType = ref('')
const editItemId = ref('')
const editForm = ref({})
const editSubmitting = ref(false)

// 自动同步定时器
let syncTimer = null

const goToDashboard = () => router.push('/dashboard')

// ========== 状态样式 ==========
const getPlanStatusType = (s) => ({ draft: 'info', active: 'success', completed: '', cancelled: 'danger' })[s] || 'info'
const getSeverityType = (s) => ({ low: 'info', medium: 'warning', high: 'danger', critical: 'danger' })[s] || 'info'
const getIssueStatusType = (s) => ({ pending: 'warning', assigned: '', in_progress: '', pending_review: 'warning', resolved: 'success', closed: 'info', rejected: 'danger' })[s] || 'info'
const getOrderStatusType = (s) => ({ pending: 'warning', assigned: '', in_progress: '', pending_review: 'warning', resolved: 'success', closed: 'info' })[s] || 'info'

// ========== 数据加载 ==========
const loadStats = async () => {
  if (!currentOrg.value) return
  try {
    const res = await axios.get('/api/inspection/stats', { params: { corp_id: currentOrg.value } })
    stats.value = res.data
  } catch (e) { console.error('加载巡检统计失败:', e) }
}

const loadPlans = async () => {
  if (!currentOrg.value) return
  loading.value = true
  try {
    const res = await axios.get('/api/inspection/plans', { params: { corp_id: currentOrg.value, status: planStatusFilter.value || undefined } })
    plans.value = res.data.plans || []
  } catch (e) { console.error('加载巡检计划失败:', e) }
  finally { loading.value = false }
}

const loadPoints = async () => {
  if (!currentOrg.value) return
  loading.value = true
  try {
    const res = await axios.get('/api/inspection/points', { params: { corp_id: currentOrg.value } })
    points.value = res.data.points || []
  } catch (e) { console.error('加载巡检点位失败:', e) }
  finally { loading.value = false }
}

const loadRecords = async () => {
  if (!currentOrg.value) return
  loading.value = true
  try {
    const res = await axios.get('/api/inspection/records', { params: { corp_id: currentOrg.value, date: recordDateFilter.value || undefined } })
    records.value = res.data.records || []
  } catch (e) { console.error('加载巡检记录失败:', e) }
  finally { loading.value = false }
}

const loadIssues = async () => {
  if (!currentOrg.value) return
  loading.value = true
  try {
    const res = await axios.get('/api/inspection/issues', {
      params: { corp_id: currentOrg.value, status: issueStatusFilter.value || undefined, category: issueCategoryFilter.value || undefined }
    })
    issues.value = res.data.issues || []
  } catch (e) { console.error('加载问题列表失败:', e) }
  finally { loading.value = false }
}

const loadOrders = async () => {
  if (!currentOrg.value) return
  loading.value = true
  try {
    const res = await axios.get('/api/inspection/orders', { params: { corp_id: currentOrg.value, status: orderStatusFilter.value || undefined } })
    orders.value = res.data.orders || []
  } catch (e) { console.error('加载工单列表失败:', e) }
  finally { loading.value = false }
}

// 当前标签页的加载函数映射
const loadFunctions = { plans: loadPlans, points: loadPoints, records: loadRecords, issues: loadIssues, orders: loadOrders }

const loadAll = () => { loadStats(); loadPlans(); loadPoints(); loadRecords(); loadIssues(); loadOrders() }

// ========== 自动同步 ==========
const startAutoSync = () => {
  stopAutoSync()
  syncTimer = setInterval(() => {
    if (!currentOrg.value) return
    // 只刷新当前激活的标签页数据，静默刷新不显示loading
    const fn = loadFunctions[activeTab.value]
    if (fn) fn()
    loadStats()
  }, 10000) // 每10秒同步一次
}

const stopAutoSync = () => {
  if (syncTimer) { clearInterval(syncTimer); syncTimer = null }
}

// ========== 操作 ==========
const activatePlan = async (plan) => {
  try {
    await axios.put(`/api/inspection/plans/${plan.plan_id}/status`, { status: 'active' })
    ElMessage.success('计划已激活')
    loadPlans(); loadStats()
  } catch (e) { ElMessage.error('激活失败') }
}

// ========== 编辑 ==========
const editItem = (type, row) => {
  editType.value = type
  editItemId.value = row[`${type}_id`] || row.record_id || row.issue_id || row.order_id
  // 深拷贝行数据作为表单初始值
  editForm.value = JSON.parse(JSON.stringify(row))
  const titles = { plan: '编辑计划', point: '编辑点位', record: '编辑记录', issue: '编辑问题' }
  editDialogTitle.value = titles[type] || '编辑'
  editDialogVisible.value = true
}

const resetEditForm = () => { editForm.value = {}; editSubmitting.value = false }

const submitEdit = async () => {
  editSubmitting.value = true
  try {
    const type = editType.value
    const id = editItemId.value
    // 根据类型提取需要的字段
    let payload = {}
    if (type === 'plan') {
      payload = { plan_name: editForm.value.plan_name, start_date: editForm.value.start_date, end_date: editForm.value.end_date, description: editForm.value.description }
    } else if (type === 'point') {
      payload = { point_name: editForm.value.point_name, area_type: editForm.value.area_type, location: editForm.value.location, requires_photo: editForm.value.requires_photo, requires_location: editForm.value.requires_location, is_active: editForm.value.is_active }
    } else if (type === 'record') {
      payload = { notes: editForm.value.notes, overall_status: editForm.value.overall_status }
    } else if (type === 'issue') {
      payload = { title: editForm.value.title, description: editForm.value.description, category: editForm.value.category, severity: editForm.value.severity, status: editForm.value.status }
    }
    await axios.put(`/api/inspection/${type}s/${id}`, payload)
    ElMessage.success('保存成功')
    editDialogVisible.value = false
    // 刷新对应数据
    const fn = loadFunctions[type + 's'] || loadFunctions[type + 'es']
    if (fn) fn()
    loadStats()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally { editSubmitting.value = false }
}

// ========== 删除 ==========
const deleteSingle = async (type, id) => {
  try {
    await ElMessageBox.confirm('确定要删除这条记录吗？', '确认删除', { type: 'warning' })
    await axios.delete(`/api/inspection/${type}s/${id}`)
    ElMessage.success('已删除')
    const fn = loadFunctions[type + 's'] || loadFunctions[type + 'es']
    if (fn) fn()
    loadStats()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const batchDelete = async (type) => {
  const idMap = { plan: selectedPlanIds, point: selectedPointIds, record: selectedRecordIds, issue: selectedIssueIds, order: selectedOrderIds }
  const ids = idMap[type]?.value || []
  if (!ids.length) return
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${ids.length} 条记录吗？`, '批量删除', { type: 'warning', confirmButtonText: '确定删除', confirmButtonClass: 'el-button--danger' })
    const res = await axios.delete(`/api/inspection/${type}s/batch`, { data: { ids } })
    ElMessage.success(`已删除 ${res.data.deleted || ids.length} 条`)
    idMap[type].value = []
    const fn = loadFunctions[type + 's'] || loadFunctions[type + 'es']
    if (fn) fn()
    loadStats()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('批量删除失败')
  }
}

// ========== 生命周期 ==========
watch(currentOrg, () => { loadAll(); startAutoSync() })
watch(activeTab, () => { /* 切换标签页时自动刷新当前tab */ })

onMounted(() => { loadAll(); startAutoSync() })
onUnmounted(() => { stopAutoSync() })
</script>

<style scoped>
.inspection { display: flex; flex-direction: column; gap: 16px; }
.stats-row { margin-bottom: 0; }
.stat-card { height: 100%; }
.stat-content { display: flex; align-items: center; gap: 16px; }
.stat-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: white; font-size: 24px; }
.stat-info { flex: 1; }
.stat-value { font-size: 24px; font-weight: 600; color: #303133; }
.stat-label { font-size: 14px; color: #909399; margin-top: 4px; }
.tabs-card { margin-top: 0; }
.tab-toolbar { display: flex; justify-content: flex-start; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.photo-cell { display: flex; align-items: flex-start; justify-content: flex-start; gap: 4px; flex-wrap: wrap; }
.record-photo { width: 40px; height: 40px; border-radius: 4px; cursor: pointer; border: 1px solid #ebeef5; transition: transform 0.2s; }
.record-photo:hover { transform: scale(1.1); border-color: #409eff; }
.photo-more { font-size: 11px; }
.no-photo { color: #c0c4cc; font-size: 13px; }
</style>
