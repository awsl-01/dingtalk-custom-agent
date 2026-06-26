<template>
  <div class="scheduling">
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
                <div class="stat-value">{{ classes.length }}</div>
                <div class="stat-label">班级数量</div>
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
                <div class="stat-value">{{ teachers.length }}</div>
                <div class="stat-label">教师数量</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-content">
              <div class="stat-icon" style="background: #e6a23c">
                <el-icon><Clock /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ pendingCount }}</div>
                <div class="stat-label">待审批调课</div>
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
                <div class="stat-value">{{ totalLessons }}</div>
                <div class="stat-label">总课时数</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 标签页 -->
      <el-card class="tabs-card">
        <el-tabs v-model="activeTab">
          <!-- 课表视图 -->
          <el-tab-pane label="课表视图" name="schedule">
            <div class="schedule-toolbar">
              <el-select v-model="selectedClass" placeholder="选择班级" @change="loadSchedule">
                <el-option
                  v-for="cls in classes"
                  :key="cls.id"
                  :label="cls.name"
                  :value="cls.id"
                />
              </el-select>
              <el-button type="primary" @click="showSwapDialog">
                <el-icon><Switch /></el-icon> 申请调课
              </el-button>
            </div>

            <!-- 课表表格 -->
            <div class="schedule-table-wrapper" v-loading="loading">
              <table class="schedule-table" v-if="scheduleData.length > 0">
                <thead>
                  <tr>
                    <th class="period-header">节次</th>
                    <th v-for="day in weekdays" :key="day">{{ day }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="period in periods" :key="period">
                    <td class="period-cell">第{{ period }}节</td>
                    <td v-for="day in weekdays" :key="`${day}_${period}`" class="lesson-cell">
                      <div v-if="getLesson(day, period)" class="lesson-content" @click="showLessonDetail(day, period)">
                        <div class="course-name">{{ getLesson(day, period).course_name }}</div>
                        <div class="teacher-name">{{ getLesson(day, period).teacher_name }}</div>
                        <div class="classroom-name">{{ getLesson(day, period).classroom_name }}</div>
                      </div>
                      <div v-else class="empty-lesson">-</div>
                    </td>
                  </tr>
                </tbody>
              </table>
              <el-empty v-else description="暂无排课数据" />
            </div>
          </el-tab-pane>

          <!-- 调课申请 -->
          <el-tab-pane label="调课申请" name="swap">
            <div class="swap-toolbar">
              <el-select v-model="swapStatusFilter" placeholder="状态筛选" clearable @change="loadSwapRequests">
                <el-option label="待审批" value="pending" />
                <el-option label="已批准" value="approved" />
                <el-option label="已拒绝" value="rejected" />
                <el-option label="已取消" value="cancelled" />
              </el-select>
              <el-button type="primary" @click="showSwapDialog">
                <el-icon><Plus /></el-icon> 新建申请
              </el-button>
            </div>

            <el-table :data="swapRequests" v-loading="loading" stripe>
              <el-table-column prop="class_name" label="班级" width="100" />
              <el-table-column label="调课内容" min-width="250">
                <template #default="{ row }">
                  <div class="swap-detail">
                    <span class="swap-course">{{ row.course1_name }}</span>
                    <span class="swap-time">{{ row.day1 }}第{{ row.period1 }}节</span>
                    <el-icon><Right /></el-icon>
                    <span class="swap-course">{{ row.course2_name }}</span>
                    <span class="swap-time">{{ row.day2 }}第{{ row.period2 }}节</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="requester_nick" label="申请人" width="80" />
              <el-table-column label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="getSwapStatusType(row.status)" size="small">
                    {{ getSwapStatusName(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作/结果" width="200" fixed="right">
                <template #default="{ row }">
                  <template v-if="row.status === 'pending'">
                    <el-button type="success" link size="small" @click="handleApprove(row)">
                      <el-icon><Check /></el-icon> 批准
                    </el-button>
                    <el-button type="danger" link size="small" @click="handleReject(row)">
                      <el-icon><Close /></el-icon> 拒绝
                    </el-button>
                    <el-button type="info" link size="small" @click="handleCancel(row)">
                      取消
                    </el-button>
                  </template>
                  <template v-else-if="row.status === 'approved'">
                    <span class="result-approved">
                      <el-icon><CircleCheck /></el-icon>
                      已批准
                    </span>
                    <span class="operator" v-if="row.approver_nick">by {{ row.approver_nick }}</span>
                  </template>
                  <template v-else-if="row.status === 'rejected'">
                    <span class="result-rejected">
                      <el-icon><CircleClose /></el-icon>
                      已拒绝
                    </span>
                    <span class="operator" v-if="row.approver_nick">by {{ row.approver_nick }}</span>
                  </template>
                  <template v-else-if="row.status === 'cancelled'">
                    <span class="result-cancelled">已取消</span>
                  </template>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 调课记录 -->
          <el-tab-pane label="调课记录" name="log">
            <el-timeline v-loading="loading">
              <el-timeline-item
                v-for="log in swapLogs"
                :key="log.log_id"
                :timestamp="formatTime(log.timestamp)"
                placement="top"
              >
                <el-card class="log-card">
                  <div class="log-content">
                    <span class="log-class">{{ log.class_name }}</span>
                    <span class="log-swap">
                      {{ log.course1 }} {{ log.from1 }} ↔ {{ log.course2 }} {{ log.from2 }}
                    </span>
                  </div>
                  <div class="log-meta">
                    <span>申请人: {{ log.requester }}</span>
                    <span>审批人: {{ log.approver }}</span>
                  </div>
                </el-card>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-if="swapLogs.length === 0" description="暂无调课记录" />
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <!-- 调课申请对话框 -->
      <el-dialog v-model="swapDialogVisible" title="申请调课" width="500px">
        <el-form :model="swapForm" label-width="100px">
          <el-form-item label="班级">
            <el-select v-model="swapForm.class_id" placeholder="选择班级" @change="onClassChange">
              <el-option
                v-for="cls in classes"
                :key="cls.id"
                :label="cls.name"
                :value="cls.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="原课程">
            <div class="swap-source">
              <el-select v-model="swapForm.day1" placeholder="星期" style="width: 100px; margin-right: 8px;">
                <el-option v-for="day in weekdays" :key="day" :label="day" :value="day" />
              </el-select>
              <el-select v-model="swapForm.period1" placeholder="节次" style="width: 100px;">
                <el-option v-for="p in periods" :key="p" :label="`第${p}节`" :value="p" />
              </el-select>
            </div>
          </el-form-item>
          <el-form-item label="目标课程">
            <div class="swap-source">
              <el-select v-model="swapForm.day2" placeholder="星期" style="width: 100px; margin-right: 8px;">
                <el-option v-for="day in weekdays" :key="day" :label="day" :value="day" />
              </el-select>
              <el-select v-model="swapForm.period2" placeholder="节次" style="width: 100px;">
                <el-option v-for="p in periods" :key="p" :label="`第${p}节`" :value="p" />
              </el-select>
            </div>
          </el-form-item>
          <el-form-item label="调课原因">
            <el-input v-model="swapForm.reason" type="textarea" placeholder="请输入调课原因" />
          </el-form-item>
          <el-form-item label="永久调课">
            <el-switch v-model="swapForm.permanent" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="swapDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitSwapRequest" :loading="submitting">提交申请</el-button>
        </template>
      </el-dialog>

      <!-- 审批对话框 -->
      <el-dialog v-model="approvalDialogVisible" :title="approvalAction === 'approve' ? '批准调课' : '拒绝调课'" width="400px">
        <div v-if="currentSwapRequest" class="approval-content">
          <p><strong>班级：</strong>{{ currentSwapRequest.class_name }}</p>
          <p><strong>调课内容：</strong></p>
          <p>{{ currentSwapRequest.course1_name }} {{ currentSwapRequest.day1 }}第{{ currentSwapRequest.period1 }}节 ↔ {{ currentSwapRequest.course2_name }} {{ currentSwapRequest.day2 }}第{{ currentSwapRequest.period2 }}节</p>
          <el-input v-if="approvalAction === 'reject'" v-model="approvalReason" type="textarea" placeholder="请输入拒绝原因" style="margin-top: 12px;" />
        </div>
        <template #footer>
          <el-button @click="approvalDialogVisible = false">取消</el-button>
          <el-button :type="approvalAction === 'approve' ? 'success' : 'danger'" @click="submitApproval" :loading="submitting">
            {{ approvalAction === 'approve' ? '批准' : '拒绝' }}
          </el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { schedulingApi } from '../api'

const router = useRouter()
const currentOrg = inject('currentOrg', ref(''))

const loading = ref(false)
const submitting = ref(false)
const activeTab = ref('schedule')

// 课表数据
const classes = ref([])
const teachers = ref([])
const scheduleData = ref([])
const selectedClass = ref('')
const weekdays = ref(['周一', '周二', '周三', '周四', '周五'])
const periods = ref([1, 2, 3, 4, 5, 6])

// 调课数据
const swapRequests = ref([])
const swapStatusFilter = ref('')
const pendingCount = ref(0)
const swapLogs = ref([])

// 调课表单
const swapDialogVisible = ref(false)
const swapForm = ref({
  class_id: '',
  class_name: '',
  day1: '',
  period1: null,
  day2: '',
  period2: null,
  reason: '',
  permanent: false,
})

// 审批对话框
const approvalDialogVisible = ref(false)
const currentSwapRequest = ref(null)
const approvalAction = ref('approve')
const approvalReason = ref('')

const totalLessons = computed(() => {
  return scheduleData.value.length * weekdays.value.length * periods.value.length
})

const goToDashboard = () => {
  router.push('/dashboard')
}

const getLesson = (day, period) => {
  const currentClass = scheduleData.value.find(c => c.class_id === selectedClass.value)
  if (!currentClass) return null
  return currentClass.lessons[`${day}_${period}`] || null
}

const getSwapStatusType = (status) => {
  const types = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
    cancelled: 'info',
  }
  return types[status] || 'info'
}

const getSwapStatusName = (status) => {
  const names = {
    pending: '待审批',
    approved: '已批准',
    rejected: '已拒绝',
    cancelled: '已取消',
  }
  return names[status] || status
}

const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}

const loadSchedule = async () => {
  if (!currentOrg.value) return

  loading.value = true
  try {
    const res = await schedulingApi.getSchedule(currentOrg.value, selectedClass.value || undefined)
    scheduleData.value = res.schedule || []
    classes.value = res.classes ? Object.entries(res.classes).map(([id, name]) => ({ id, name })) : []
    weekdays.value = res.weekdays || weekdays.value
    periods.value = res.periods ? Object.keys(res.periods).map(Number) : periods.value
  } catch (error) {
    console.error('加载排课数据失败:', error)
  } finally {
    loading.value = false
  }
}

const loadSwapRequests = async () => {
  if (!currentOrg.value) return

  loading.value = true
  try {
    const [requestsRes, pendingRes, logsRes] = await Promise.all([
      schedulingApi.getSwapRequests(currentOrg.value, swapStatusFilter.value || undefined),
      schedulingApi.getSwapRequests(currentOrg.value, 'pending'),
      schedulingApi.getSwapLog(currentOrg.value),
    ])
    swapRequests.value = requestsRes.requests || []
    pendingCount.value = pendingRes.total || 0
    swapLogs.value = logsRes.logs || []
  } catch (error) {
    console.error('加载调课数据失败:', error)
  } finally {
    loading.value = false
  }
}

const showSwapDialog = () => {
  swapForm.value = {
    class_id: selectedClass.value || '',
    class_name: '',
    day1: '',
    period1: null,
    day2: '',
    period2: null,
    reason: '',
    permanent: false,
  }
  swapDialogVisible.value = true
}

const onClassChange = (classId) => {
  const cls = classes.value.find(c => c.id === classId)
  swapForm.value.class_name = cls ? cls.name : ''
}

const submitSwapRequest = async () => {
  if (!swapForm.value.class_id || !swapForm.value.day1 || !swapForm.value.period1 || !swapForm.value.day2 || !swapForm.value.period2) {
    ElMessage.warning('请填写完整的调课信息')
    return
  }

  if (swapForm.value.day1 === swapForm.value.day2 && swapForm.value.period1 === swapForm.value.period2) {
    ElMessage.warning('原课程和目标课程不能相同')
    return
  }

  submitting.value = true
  try {
    await schedulingApi.createSwapRequest(currentOrg.value, swapForm.value)
    ElMessage.success('调课申请已提交')
    swapDialogVisible.value = false
    loadSwapRequests()
  } catch (error) {
    ElMessage.error('提交失败')
    console.error('提交调课申请失败:', error)
  } finally {
    submitting.value = false
  }
}

const showLessonDetail = (day, period) => {
  // 可以扩展为显示详情
}

const handleApprove = (request) => {
  currentSwapRequest.value = request
  approvalAction.value = 'approve'
  approvalReason.value = ''
  approvalDialogVisible.value = true
}

const handleReject = (request) => {
  currentSwapRequest.value = request
  approvalAction.value = 'reject'
  approvalReason.value = ''
  approvalDialogVisible.value = true
}

const handleCancel = async (request) => {
  try {
    await ElMessageBox.confirm('确定要取消这个调课申请吗？', '取消申请', { type: 'warning' })
    await schedulingApi.cancelSwapRequest(request.swap_id, currentOrg.value)
    ElMessage.success('已取消')
    loadSwapRequests()
  } catch (e) {
    // 用户取消
  }
}

const submitApproval = async () => {
  if (approvalAction.value === 'reject' && !approvalReason.value) {
    ElMessage.warning('请输入拒绝原因')
    return
  }

  submitting.value = true
  try {
    await schedulingApi.approveSwapRequest(
      currentSwapRequest.value.swap_id,
      currentOrg.value,
      { action: approvalAction.value, reason: approvalReason.value }
    )
    ElMessage.success(approvalAction.value === 'approve' ? '已批准' : '已拒绝')
    approvalDialogVisible.value = false
    loadSwapRequests()
  } catch (error) {
    ElMessage.error('操作失败')
    console.error('审批失败:', error)
  } finally {
    submitting.value = false
  }
}

watch(currentOrg, () => {
  loadSchedule()
  loadSwapRequests()
})

onMounted(() => {
  loadSchedule()
  loadSwapRequests()
})
</script>

<style scoped>
.scheduling {
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

.tabs-card {
  margin-top: 0;
}

.schedule-toolbar,
.swap-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.schedule-table-wrapper {
  overflow-x: auto;
}

.schedule-table {
  width: 100%;
  border-collapse: collapse;
  border: 1px solid #ebeef5;
}

.schedule-table th,
.schedule-table td {
  border: 1px solid #ebeef5;
  padding: 12px;
  text-align: center;
}

.schedule-table th {
  background: #f5f7fa;
  font-weight: 600;
  color: #303133;
}

.period-header,
.period-cell {
  background: #f5f7fa;
  font-weight: 500;
  width: 80px;
}

.lesson-cell {
  min-width: 120px;
  cursor: pointer;
}

.lesson-content {
  padding: 8px;
  border-radius: 6px;
  background: #ecf5ff;
  transition: all 0.2s;
}

.lesson-content:hover {
  background: #d9ecff;
  transform: scale(1.02);
}

.course-name {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.teacher-name {
  color: #606266;
  font-size: 12px;
  margin-top: 4px;
}

.classroom-name {
  color: #909399;
  font-size: 11px;
  margin-top: 2px;
}

.empty-lesson {
  color: #c0c4cc;
}

.swap-detail {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.swap-course {
  font-weight: 500;
  color: #303133;
}

.swap-time {
  color: #909399;
  font-size: 12px;
}

.log-card {
  margin-bottom: 0;
}

.log-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.log-class {
  font-weight: 600;
  color: #409eff;
}

.log-swap {
  color: #606266;
}

.log-meta {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 16px;
}

.text-muted {
  color: #c0c4cc;
}

.result-approved {
  color: #67c23a;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.result-rejected {
  color: #f56c6c;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.result-cancelled {
  color: #909399;
  font-weight: 500;
}

.operator {
  color: #909399;
  font-size: 12px;
  margin-left: 6px;
}

.swap-source {
  display: flex;
  gap: 8px;
}

.approval-content p {
  margin: 8px 0;
}
</style>
