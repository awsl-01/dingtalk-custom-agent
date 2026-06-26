<template>
  <div class="messages">
    <!-- 筛选区域 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="发送者ID">
          <el-input v-model="filterForm.sender_id" placeholder="筛选发送者" clearable />
        </el-form-item>
        <el-form-item label="消息类型">
          <el-select v-model="filterForm.message_type" placeholder="全部类型" clearable>
            <el-option label="文本" value="text" />
            <el-option label="图片" value="picture" />
            <el-option label="文件" value="file" />
            <el-option label="富文本" value="richText" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理状态">
          <el-select v-model="filterForm.status" placeholder="全部状态" clearable>
            <el-option label="成功" value="success" />
            <el-option label="失败" value="error" />
            <el-option label="跳过" value="skipped" />
            <el-option label="处理中" value="processing" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="handleDateChange"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">
            <el-icon><Search /></el-icon> 查询
          </el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 消息列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>消息记录 ({{ total }} 条)</span>
          <el-button type="primary" size="small" @click="loadData">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </template>

      <el-table :data="messages" v-loading="loading" stripe @row-click="showDetail">
        <el-table-column prop="msg_id" label="消息ID" width="140" show-overflow-tooltip />
        <el-table-column prop="sender_nick" label="发送者" width="100" />
        <el-table-column prop="content" label="内容" min-width="250" show-overflow-tooltip />
        <el-table-column prop="message_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="getTypeColor(row.message_type)" size="small">
              {{ getTypeName(row.message_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusColor(row.status)" size="small">
              {{ getStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="skill_used" label="技能" width="100">
          <template #default="{ row }">
            {{ row.skill_used || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="processing_time_ms" label="耗时" width="80">
          <template #default="{ row }">
            {{ row.processing_time_ms ? row.processing_time_ms + 'ms' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @size-change="loadData"
        @current-change="loadData"
        style="margin-top: 16px; justify-content: flex-end"
      />
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="消息详情" width="700px">
      <div v-if="currentMessage" class="message-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="消息ID">{{ currentMessage.msg_id }}</el-descriptions-item>
          <el-descriptions-item label="发送者">{{ currentMessage.sender_nick }} ({{ currentMessage.sender_id }})</el-descriptions-item>
          <el-descriptions-item label="消息类型">
            <el-tag :type="getTypeColor(currentMessage.message_type)">
              {{ getTypeName(currentMessage.message_type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="处理状态">
            <el-tag :type="getStatusColor(currentMessage.status)">
              {{ getStatusName(currentMessage.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="会话ID" :span="2">{{ currentMessage.conversation_id }}</el-descriptions-item>
          <el-descriptions-item label="企业ID">{{ currentMessage.corp_id }}</el-descriptions-item>
          <el-descriptions-item label="使用技能">{{ currentMessage.skill_used || '-' }}</el-descriptions-item>
          <el-descriptions-item label="处理耗时">{{ currentMessage.processing_time_ms }}ms</el-descriptions-item>
          <el-descriptions-item label="知识库结果数">{{ currentMessage.kb_results_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="接收时间" :span="2">{{ formatTime(currentMessage.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="消息内容" :span="2">
            <div class="message-content">{{ currentMessage.full_content }}</div>
          </el-descriptions-item>
          <el-descriptions-item v-if="currentMessage.error_msg" label="错误信息" :span="2">
            <div class="error-msg">{{ currentMessage.error_msg }}</div>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, inject, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { messagesApi } from '../api'

const loading = ref(false)
const messages = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

// 注入当前组织
const currentOrg = inject('currentOrg', ref(''))

const filterForm = ref({
  sender_id: '',
  message_type: '',
  status: '',
  start_date: '',
  end_date: '',
})
const dateRange = ref(null)

const detailVisible = ref(false)
const currentMessage = ref(null)

const getTypeName = (type) => {
  const names = { text: '文本', picture: '图片', file: '文件', richText: '富文本' }
  return names[type] || type || '未知'
}

const getTypeColor = (type) => {
  const colors = { text: '', picture: 'success', file: 'warning', richText: 'info' }
  return colors[type] || 'info'
}

const getStatusName = (status) => {
  const names = { success: '成功', error: '失败', skipped: '跳过', processing: '处理中' }
  return names[status] || status || '未知'
}

const getStatusColor = (status) => {
  const colors = { success: 'success', error: 'danger', skipped: 'info', processing: 'warning' }
  return colors[status] || 'info'
}

const formatTime = (isoString) => {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN')
}

const handleDateChange = (val) => {
  if (val) {
    filterForm.value.start_date = val[0]
    filterForm.value.end_date = val[1]
  } else {
    filterForm.value.start_date = ''
    filterForm.value.end_date = ''
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await messagesApi.getList({
      corp_id: currentOrg.value || undefined,
      ...filterForm.value,
      page: currentPage.value,
      page_size: pageSize.value,
    })
    messages.value = res.messages || []
    total.value = res.total || 0
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const resetFilter = () => {
  filterForm.value = {
    sender_id: '',
    message_type: '',
    status: '',
    start_date: '',
    end_date: '',
  }
  dateRange.value = null
  loadData()
}

const showDetail = (row) => {
  currentMessage.value = row
  detailVisible.value = true
}

// 监听组织变化，重新加载数据
watch(currentOrg, () => {
  currentPage.value = 1
  loadData()
})

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.messages {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card :deep(.el-card__body) {
  padding-bottom: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.message-detail .message-content {
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.6;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
}

.message-detail .error-msg {
  color: #f56c6c;
  background: #fef0f0;
  padding: 12px;
  border-radius: 4px;
  font-size: 14px;
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}
</style>
