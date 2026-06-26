<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card clickable" @click="goTo('/messages')">
          <div class="stat-icon" style="background: #409eff">
            <el-icon><ChatDotRound /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.messages?.total || 0 }}</div>
            <div class="stat-label">总消息数</div>
          </div>
          <el-icon class="arrow"><ArrowRight /></el-icon>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card clickable" @click="goTo('/knowledge')">
          <div class="stat-icon" style="background: #67c23a">
            <el-icon><Collection /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.knowledge?.total_files || 0 }}</div>
            <div class="stat-label">知识库文件</div>
          </div>
          <el-icon class="arrow"><ArrowRight /></el-icon>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card clickable" @click="goTo('/users')">
          <div class="stat-icon" style="background: #e6a23c">
            <el-icon><User /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.users?.active || 0 }}</div>
            <div class="stat-label">活跃用户</div>
          </div>
          <el-icon class="arrow"><ArrowRight /></el-icon>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card clickable" @click="goTo('/debug')">
          <div class="stat-icon" style="background: #f56c6c">
            <el-icon><Monitor /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.debug?.sessions || 0 }}</div>
            <div class="stat-label">调试会话</div>
          </div>
          <el-icon class="arrow"><ArrowRight /></el-icon>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- 消息趋势图 -->
      <el-col :span="16">
        <el-card class="chart-card">
          <template #header>
            <span>最近7天消息趋势</span>
          </template>
          <div class="chart-container">
            <div class="bar-chart">
              <div
                v-for="(day, index) in activity"
                :key="index"
                class="bar-item"
              >
                <div class="bar-wrapper">
                  <div
                    class="bar"
                    :style="{ height: getBarHeight(day.count) + '%' }"
                  ></div>
                </div>
                <div class="bar-label">{{ day.date }}</div>
                <div class="bar-value">{{ day.count }}</div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 知识库类别分布 -->
      <el-col :span="8">
        <el-card class="chart-card">
          <template #header>
            <span>知识库类别分布</span>
          </template>
          <div class="category-list">
            <div
              v-for="(count, category) in stats.knowledge?.categories || {}"
              :key="category"
              class="category-item"
            >
              <span class="category-name">{{ getCategoryName(category) }}</span>
              <el-progress
                :percentage="getCategoryPercent(count)"
                :format="() => count"
              />
            </div>
            <el-empty v-if="!stats.knowledge?.categories || Object.keys(stats.knowledge.categories).length === 0" description="暂无数据" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 技能使用统计 -->
    <el-card class="chart-card" style="margin-top: 20px">
      <template #header>
        <span>技能使用统计</span>
      </template>
      <div class="skill-stats" v-if="skillStats.length > 0">
        <div v-for="skill in skillStats" :key="skill.name" class="skill-item">
          <span class="skill-name">{{ skill.name }}</span>
          <el-tag type="info">{{ skill.count }} 次</el-tag>
        </div>
      </div>
      <el-empty v-else description="暂无技能使用记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { dashboardApi } from '../api'

const router = useRouter()
const currentOrg = inject('currentOrg', ref(''))

const stats = ref({})
const activity = ref([])
const skillStats = ref([])

const maxActivity = computed(() => {
  if (activity.value.length === 0) return 1
  return Math.max(...activity.value.map(d => d.count), 1)
})

const totalKnowledge = computed(() => {
  const categories = stats.value.knowledge?.categories || {}
  return Object.values(categories).reduce((a, b) => a + b, 0) || 1
})

const getBarHeight = (count) => {
  return (count / maxActivity.value) * 100
}

const getCategoryPercent = (count) => {
  return Math.round((count / totalKnowledge.value) * 100)
}

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
  return names[category] || category
}

const goTo = (path) => {
  router.push(path)
}

const loadData = async () => {
  try {
    const params = currentOrg.value ? { corp_id: currentOrg.value } : {}
    const [statsRes, activityRes, skillRes] = await Promise.all([
      dashboardApi.getStats(params),
      dashboardApi.getRecentActivity(params),
      dashboardApi.getSkillStats(params),
    ])
    stats.value = statsRes
    activity.value = activityRes.days || []
    skillStats.value = skillRes.skills || []
  } catch (error) {
    console.error('加载数据失败:', error)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stat-cards {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  width: 100%;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: #fff;
  margin-right: 16px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 4px;
}

.arrow {
  color: #c0c4cc;
  font-size: 16px;
}

.chart-card {
  margin-bottom: 20px;
}

.chart-container {
  height: 300px;
  padding: 20px 0;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 100%;
}

.bar-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.bar-wrapper {
  height: 200px;
  width: 40px;
  display: flex;
  align-items: flex-end;
}

.bar {
  width: 100%;
  background: linear-gradient(180deg, #409eff 0%, #66b1ff 100%);
  border-radius: 4px 4px 0 0;
  min-height: 4px;
  transition: height 0.3s;
}

.bar:hover {
  background: linear-gradient(180deg, #337ecc 0%, #409eff 100%);
}

.bar-label {
  margin-top: 8px;
  font-size: 12px;
  color: #666;
}

.bar-value {
  font-size: 12px;
  color: #409eff;
  font-weight: bold;
}

.category-list {
  padding: 10px 0;
}

.category-item {
  margin-bottom: 16px;
}

.category-name {
  display: block;
  margin-bottom: 4px;
  font-size: 14px;
  color: #333;
}

.skill-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.skill-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.skill-name {
  font-size: 14px;
  color: #333;
}
</style>
