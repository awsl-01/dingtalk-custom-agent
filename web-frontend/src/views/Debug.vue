<template>
  <div class="debug">
    <el-row :gutter="20">
      <!-- 左侧：输入区 -->
      <el-col :span="10">
        <el-card class="input-card">
          <template #header>
            <span>模拟对话</span>
          </template>

          <el-form :model="chatForm" label-position="top">
            <el-form-item label="消息内容">
              <el-input
                v-model="chatForm.message"
                type="textarea"
                :rows="4"
                placeholder="输入要模拟的消息..."
              />
            </el-form-item>
            <el-form-item label="企业ID">
              <el-input v-model="chatForm.corp_id" placeholder="corp_id" />
            </el-form-item>
            <el-form-item label="用户ID">
              <el-input v-model="chatForm.user_id" placeholder="用户ID" />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                @click="handleSend"
                :loading="sending"
                style="width: 100%"
              >
                <el-icon><Promotion /></el-icon> 发送测试消息
              </el-button>
            </el-form-item>
          </el-form>

          <!-- 快捷消息 -->
          <div class="quick-messages">
            <div class="section-title">快捷测试</div>
            <div class="quick-list">
              <el-tag
                v-for="msg in quickMessages"
                :key="msg"
                class="quick-tag"
                @click="chatForm.message = msg"
              >
                {{ msg }}
              </el-tag>
            </div>
          </div>
        </el-card>

        <!-- 已注册技能 -->
        <el-card class="skills-card">
          <template #header>
            <span>已注册技能 ({{ skills.length }})</span>
          </template>
          <div class="skills-list">
            <div v-for="skill in skills" :key="skill.name" class="skill-item">
              <div class="skill-name">{{ skill.name }}</div>
              <div class="skill-desc">{{ skill.description }}</div>
              <div class="skill-keywords">
                <el-tag v-for="kw in skill.keywords?.slice(0, 3)" :key="kw" size="small" type="info">
                  {{ kw }}
                </el-tag>
              </div>
            </div>
            <el-empty v-if="skills.length === 0" description="暂无技能" :image-size="60" />
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：处理流程 -->
      <el-col :span="14">
        <el-card class="result-card">
          <template #header>
            <div class="card-header">
              <span>处理流程</span>
              <el-tag v-if="result" type="success" size="small">
                耗时: {{ result.processing_time_ms }}ms
              </el-tag>
            </div>
          </template>

          <div v-if="result" class="process-result">
            <!-- 机器人回复 -->
            <div class="bot-response">
              <div class="response-label">🤖 机器人回复:</div>
              <div class="response-text">{{ result.bot_response }}</div>
            </div>

            <!-- 处理步骤 -->
            <el-divider content-position="left">处理步骤</el-divider>
            <el-steps direction="vertical" :active="result.steps?.length" finish-status="success">
              <el-step
                v-for="(step, index) in result.steps"
                :key="index"
                :title="step.step"
                :description="step.detail"
                :status="getStepStatus(step.status)"
              />
            </el-steps>

            <!-- 详细信息 -->
            <el-collapse v-if="result.skill_matched || result.kb_results?.length" style="margin-top: 20px">
              <el-collapse-item v-if="result.skill_matched" title="技能匹配详情">
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item label="技能名称">{{ result.skill_matched }}</el-descriptions-item>
                  <el-descriptions-item label="置信度">{{ (result.skill_confidence * 100).toFixed(1) }}%</el-descriptions-item>
                </el-descriptions>
              </el-collapse-item>

              <el-collapse-item v-if="result.kb_results?.length" title="知识库检索结果">
                <div class="kb-results">
                  <div v-for="(kb, index) in result.kb_results" :key="index" class="kb-item">
                    <div class="kb-header">
                      <el-tag :type="getCategoryType(kb.category)" size="small">
                        {{ getCategoryName(kb.category) }}
                      </el-tag>
                      <span class="kb-score">相关度: {{ (kb.score * 100).toFixed(1) }}%</span>
                    </div>
                    <div class="kb-text">{{ kb.text }}</div>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>

          <el-empty v-else description="发送消息后查看处理流程" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { debugApi } from '../api'

const sending = ref(false)
const chatForm = ref({
  message: '',
  corp_id: 'default',
  user_id: 'debug_user',
})

const result = ref(null)
const skills = ref([])

const quickMessages = [
  '计算机2301班周一有什么课？',
  '查询课表',
  '帮我搜索一下高等数学的教学资源',
  '最近有什么通知？',
  '制作一个PPT，主题是环境保护',
  '张老师的联系方式是什么？',
]

const getCategoryName = (category) => {
  const names = {
    schedule: '课表',
    exam: '考试',
    contact: '通讯录',
    homework: '作业',
    notice: '通知',
    teaching: '教学',
    student: '学生',
    other: '其他',
  }
  return names[category] || category || '未知'
}

const getCategoryType = (category) => {
  const types = {
    schedule: '',
    exam: 'warning',
    contact: 'success',
    homework: 'danger',
    notice: 'info',
    teaching: '',
    student: 'success',
    other: 'info',
  }
  return types[category] || 'info'
}

const getStepStatus = (status) => {
  const statuses = {
    success: 'success',
    error: 'error',
    skip: 'wait',
    info: '',
  }
  return statuses[status] || ''
}

const handleSend = async () => {
  if (!chatForm.value.message.trim()) {
    ElMessage.warning('请输入消息内容')
    return
  }

  sending.value = true
  result.value = null

  try {
    const res = await debugApi.chat(chatForm.value)
    result.value = res
    ElMessage.success('处理完成')
  } catch (error) {
    console.error('调试失败:', error)
    ElMessage.error('调试失败: ' + (error.message || '未知错误'))
  } finally {
    sending.value = false
  }
}

const loadSkills = async () => {
  try {
    const res = await debugApi.getSkills()
    skills.value = res.skills || []
  } catch (error) {
    console.error('加载技能失败:', error)
  }
}

onMounted(() => {
  loadSkills()
})
</script>

<style scoped>
.debug {
  height: calc(100vh - 120px);
}

.input-card, .skills-card, .result-card {
  height: 100%;
}

.input-card :deep(.el-card__body) {
  height: calc(100% - 56px);
  overflow-y: auto;
}

.skills-card {
  margin-top: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quick-messages {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.section-title {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.quick-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-tag {
  cursor: pointer;
}

.quick-tag:hover {
  color: #409eff;
  border-color: #409eff;
}

.skills-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skill-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.skill-name {
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
}

.skill-desc {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.skill-keywords {
  display: flex;
  gap: 4px;
}

.process-result {
  padding: 0;
}

.bot-response {
  padding: 16px;
  background: #f0f9ff;
  border-radius: 8px;
  margin-bottom: 16px;
}

.response-label {
  font-weight: 500;
  color: #409eff;
  margin-bottom: 8px;
}

.response-text {
  font-size: 14px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.kb-results {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kb-item {
  padding: 8px;
  background: #f5f7fa;
  border-radius: 4px;
}

.kb-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.kb-score {
  font-size: 12px;
  color: #999;
}

.kb-text {
  font-size: 13px;
  color: #666;
}
</style>
