<template>
  <div class="knowledge">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409eff">
              <el-icon><ChatDotRound /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_messages || 0 }}</div>
              <div class="stat-label">消息数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67c23a">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_files || 0 }}</div>
              <div class="stat-label">文件数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #e6a23c">
              <el-icon><Folder /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_size_display || '0 B' }}</div>
              <div class="stat-label">存储大小</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #f56c6c">
              <el-icon><Calendar /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ Object.keys(stats.dates || {}).length }}</div>
              <div class="stat-label">活跃天数</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选区域 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="来源类型">
          <el-select v-model="filterForm.source_type" placeholder="全部" clearable @change="loadData">
            <el-option label="消息" value="message" />
            <el-option label="文件" value="file" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="filterForm.date"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            clearable
            @change="loadData"
          />
        </el-form-item>
        <el-form-item label="搜索">
          <el-input
            v-model="filterForm.keyword"
            placeholder="搜索内容"
            clearable
            @keyup.enter="loadData"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 内容列表 -->
    <el-card class="list-card">
      <template #header>
        <div class="card-header">
          <span>知识库内容 ({{ total }} 条)</span>
          <div class="header-actions">
            <!-- 上传按钮 -->
            <el-button type="success" size="small" @click="showUploadDialog">
              <el-icon><Upload /></el-icon> 上传文件
            </el-button>
            <!-- 批量操作 -->
            <template v-if="selectedItems.length > 0">
              <el-tag type="info" style="margin-right: 8px;">已选择 {{ selectedItems.length }} 项</el-tag>
              <el-dropdown @command="handleBatchCommand">
                <el-button type="warning" size="small">
                  批量操作 <el-icon><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="permission_public">
                      <el-icon><Unlock /></el-icon> 设为公开
                    </el-dropdown-item>
                    <el-dropdown-item command="permission_internal">
                      <el-icon><Lock /></el-icon> 设为内部
                    </el-dropdown-item>
                    <el-dropdown-item command="permission_confidential">
                      <el-icon><Key /></el-icon> 设为机密
                    </el-dropdown-item>
                    <el-dropdown-item divided command="delete">
                      <el-icon><Delete /></el-icon> 批量删除
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
            <el-button type="primary" size="small" @click="loadData">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="filteredItems"
        v-loading="loading"
        stripe
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.type === 'message' ? 'primary' : 'success'" size="small">
              {{ row.type === 'message' ? '消息' : '文件' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="名称/内容" min-width="350">
          <template #default="{ row }">
            <div v-if="row.type === 'message'" class="message-preview">
              <div class="sender" v-if="row.sender_nick">
                <el-icon><User /></el-icon> {{ row.sender_nick }}
              </div>
              <div class="content">{{ row.preview }}</div>
            </div>
            <div v-else class="file-info">
              <div class="file-name">
                <el-icon><Document /></el-icon> {{ row.name }}
              </div>
              <div class="file-meta">
                {{ row.size_display }} · {{ getFileTypeName(row.file_type) }}
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="date" label="日期" width="100" />
        <el-table-column label="权限" width="100">
          <template #default="{ row }">
            <el-tag :type="getPermissionType(row.permission)" size="small">
              {{ getPermissionName(row.permission) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handlePreview(row)">
              <el-icon><View /></el-icon> 预览
            </el-button>
            <el-button type="warning" link size="small" @click="showPermissionDialog(row)">
              <el-icon><Lock /></el-icon> 权限
            </el-button>
            <el-button type="success" link size="small" @click="handleDownload(row)">
              <el-icon><Download /></el-icon> 下载
            </el-button>
            <el-popconfirm
              title="确定要删除这个内容吗？"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button type="danger" link size="small">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-popconfirm>
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

    <!-- 预览对话框 -->
    <el-dialog
      v-model="previewVisible"
      :title="previewTitle"
      width="800px"
      destroy-on-close
    >
      <div v-loading="previewLoading" class="preview-content">
        <!-- 文本预览 -->
        <pre v-if="previewData?.type === 'text'" class="text-preview">{{ previewData.content }}</pre>

        <!-- 图片预览 -->
        <div v-else-if="previewData?.type === 'image'" class="image-preview">
          <img :src="`/api/knowledge/preview?file_path=${encodeURIComponent(previewData.path)}`" />
        </div>

        <!-- Excel 预览 -->
        <div v-else-if="previewData?.type === 'excel'" class="excel-preview">
          <div v-for="(rows, sheetName) in previewData.sheets" :key="sheetName" class="sheet-block">
            <h4>{{ sheetName }}</h4>
            <el-table :data="rows.map((row, idx) => ({ idx, ...row.reduce((acc, cell, i) => ({ ...acc, [`col${i}`]: cell }), {}) }))" border size="small">
              <el-table-column
                v-for="(cell, i) in (rows[0] || [])"
                :key="i"
                :prop="`col${i}`"
                :label="`列${i+1}`"
                min-width="100"
              />
            </el-table>
          </div>
        </div>

        <!-- PDF 预览 -->
        <div v-else-if="previewData?.type === 'pdf'" class="pdf-preview">
          <div class="pdf-info">
            <el-icon :size="48" color="#f56c6c"><Document /></el-icon>
            <p>PDF 文档共 {{ previewData.total_pages }} 页</p>
          </div>
          <el-collapse v-model="activePdfPages">
            <el-collapse-item v-for="page in previewData.pages" :key="page.page" :title="`第 ${page.page} 页`" :name="page.page">
              <pre class="page-text">{{ page.text }}</pre>
            </el-collapse-item>
          </el-collapse>
          <p v-if="previewData.total_pages > 20" class="truncated-hint">（仅显示前 20 页）</p>
        </div>

        <!-- Word 预览 -->
        <div v-else-if="previewData?.type === 'word'" class="word-preview">
          <div class="word-content">
            <pre class="text-preview">{{ previewData.content }}</pre>
          </div>
          <div v-if="previewData.tables?.length" class="word-tables">
            <h4>表格内容</h4>
            <div v-for="(table, tIdx) in previewData.tables" :key="tIdx" class="table-block">
              <el-table :data="table.map((row, idx) => ({ idx, ...row.reduce((acc, cell, i) => ({ ...acc, [`col${i}`]: cell }), {}) }))" border size="small">
                <el-table-column
                  v-for="(cell, i) in (table[0] || [])"
                  :key="i"
                  :prop="`col${i}`"
                  :label="`列${i+1}`"
                  min-width="100"
                />
              </el-table>
            </div>
          </div>
          <p v-if="previewData.truncated" class="truncated-hint">（内容过长，仅显示前 10000 字符）</p>
        </div>

        <!-- PPT 预览 -->
        <div v-else-if="previewData?.type === 'ppt'" class="ppt-preview">
          <div class="ppt-info">
            <el-icon :size="48" color="#e6a23c"><Monitor /></el-icon>
            <p>PPT 演示文稿共 {{ previewData.total_slides }} 页</p>
          </div>
          <el-collapse v-model="activePptSlides">
            <el-collapse-item v-for="slide in previewData.slides" :key="slide.slide" :title="`第 ${slide.slide} 页`" :name="slide.slide">
              <pre class="slide-text">{{ slide.text }}</pre>
            </el-collapse-item>
          </el-collapse>
          <p v-if="previewData.total_slides > 50" class="truncated-hint">（仅显示前 50 页）</p>
        </div>

        <!-- 二进制文件 -->
        <div v-else-if="previewData?.type === 'binary'" class="binary-preview">
          <el-icon :size="64" color="#909399"><Document /></el-icon>
          <p>{{ previewData.name }}</p>
          <p class="file-size">{{ previewData.size }}</p>
          <p class="file-ext">文件类型: {{ previewData.extension }}</p>
        </div>

        <!-- 错误 -->
        <div v-else-if="previewData?.type === 'error'" class="error-preview">
          <el-alert :title="previewData.message" type="error" show-icon />
        </div>
      </div>
    </el-dialog>

    <!-- 权限设置对话框 -->
    <el-dialog
      v-model="permissionDialogVisible"
      title="设置权限等级"
      width="400px"
    >
      <div v-if="currentEditItem" class="permission-dialog">
        <div class="item-info">
          <p><strong>名称：</strong>{{ currentEditItem.name || currentEditItem.preview }}</p>
          <p><strong>类型：</strong>{{ currentEditItem.type === 'message' ? '消息' : '文件' }}</p>
        </div>
        <el-divider />
        <el-form label-width="80px">
          <el-form-item label="权限等级">
            <el-radio-group v-model="selectedPermission">
              <el-radio label="public">
                <el-icon><Unlock /></el-icon> 公开
                <span class="perm-desc">所有用户可访问</span>
              </el-radio>
              <el-radio label="internal">
                <el-icon><Lock /></el-icon> 内部
                <span class="perm-desc">仅内部人员可访问</span>
              </el-radio>
              <el-radio label="confidential">
                <el-icon><Key /></el-icon> 机密
                <span class="perm-desc">需要授权访问</span>
              </el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="permissionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="savePermission" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 上传文件对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传文件到知识库"
      width="500px"
    >
      <el-upload
        ref="uploadRef"
        class="upload-area"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :file-list="uploadFileList"
        :limit="1"
        accept=".txt,.md,.csv,.json,.xml,.html,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.pdf,.jpg,.jpeg,.png,.gif,.bmp,.py,.js,.java,.c,.cpp"
      >
        <el-icon :size="48"><Upload /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处，或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持文档、Office、PDF、图片、代码等格式，文件将自动提取文本并加入 RAG 知识库
          </div>
        </template>
      </el-upload>
      <el-form label-width="80px" style="margin-top: 16px;">
        <el-form-item label="访问权限">
          <el-select v-model="uploadPermission" placeholder="选择权限">
            <el-option label="公开" value="public" />
            <el-option label="内部" value="internal" />
            <el-option label="机密" value="confidential" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="uploadTags" placeholder="多个标签用逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpload" :loading="uploading">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { knowledgeApi } from '../api'

const loading = ref(false)
const saving = ref(false)
const items = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const stats = ref({})
const selectedItems = ref([])

// 注入当前组织
const currentOrg = inject('currentOrg', ref(''))

const filterForm = ref({
  source_type: '',
  date: '',
  keyword: '',
})

const previewVisible = ref(false)
const previewLoading = ref(false)
const previewData = ref(null)
const previewTitle = ref('预览')
const activePdfPages = ref([])
const activePptSlides = ref([])

// 权限设置
const permissionDialogVisible = ref(false)
const currentEditItem = ref(null)
const selectedPermission = ref('public')

// 上传文件
const uploadDialogVisible = ref(false)
const uploading = ref(false)
const uploadFileList = ref([])
const uploadPermission = ref('public')
const uploadTags = ref('')
const uploadRef = ref(null)

const filteredItems = computed(() => {
  if (!filterForm.value.keyword) return items.value
  const kw = filterForm.value.keyword.toLowerCase()
  return items.value.filter(item => {
    const text = (item.preview || item.name || '').toLowerCase()
    const content = (item.content || '').toLowerCase()
    return text.includes(kw) || content.includes(kw)
  })
})

const getFileTypeName = (type) => {
  const names = {
    pdf: 'PDF文档',
    word: 'Word文档',
    excel: 'Excel表格',
    ppt: 'PPT演示',
    image: '图片',
    text: '文本',
    archive: '压缩包',
    video: '视频',
    audio: '音频',
    other: '其他',
  }
  return names[type] || type
}

const getPermissionType = (permission) => {
  const types = {
    public: 'success',
    internal: 'warning',
    confidential: 'danger',
  }
  return types[permission] || 'info'
}

const getPermissionName = (permission) => {
  const names = {
    public: '公开',
    internal: '内部',
    confidential: '机密',
  }
  return names[permission] || '未设置'
}

const handleSelectionChange = (selection) => {
  selectedItems.value = selection
}

const loadData = async () => {
  loading.value = true
  try {
    // TODO: 从登录状态获取用户角色，目前默认为 admin（可查看所有内容）
    const userRole = 'admin'

    const res = await knowledgeApi.getList({
      corp_id: currentOrg.value || undefined,
      source_type: filterForm.value.source_type || undefined,
      date: filterForm.value.date || undefined,
      user_role: userRole,
      page: currentPage.value,
      page_size: pageSize.value,
    })
    items.value = res.items || []
    total.value = res.total || 0
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    stats.value = await knowledgeApi.getStats({
      corp_id: currentOrg.value || undefined,
    })
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

const resetFilter = () => {
  filterForm.value.source_type = ''
  filterForm.value.date = ''
  filterForm.value.keyword = ''
  loadData()
}

// 上传相关函数
const showUploadDialog = () => {
  uploadFileList.value = []
  uploadPermission.value = 'public'
  uploadTags.value = ''
  uploadDialogVisible.value = true
}

const handleFileChange = (file) => {
  uploadFileList.value = [file]
}

const handleUpload = async () => {
  if (uploadFileList.value.length === 0) {
    ElMessage.warning('请选择要上传的文件')
    return
  }

  uploading.value = true
  try {
    const file = uploadFileList.value[0]
    const formData = new FormData()
    formData.append('file', file.raw)

    const params = {
      corp_id: currentOrg.value || undefined,
      access_level: uploadPermission.value,
      tags: uploadTags.value || undefined,
    }

    await knowledgeApi.upload(formData, params)
    ElMessage.success('上传成功')
    uploadDialogVisible.value = false
    loadData()
    loadStats()
  } catch (error) {
    console.error('上传失败:', error)
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

const handlePreview = async (row) => {
  previewVisible.value = true
  previewLoading.value = true
  previewData.value = null
  previewTitle.value = row.type === 'message' ? `消息预览 - ${row.sender_nick || '未知'}` : `文件预览 - ${row.name}`

  try {
    previewData.value = await knowledgeApi.preview(row.path)
  } catch (error) {
    console.error('预览失败:', error)
    ElMessage.error('预览失败')
    previewVisible.value = false
  } finally {
    previewLoading.value = false
  }
}

const handleDownload = (row) => {
  const url = `/api/knowledge/download?file_path=${encodeURIComponent(row.path)}&file_name=${encodeURIComponent(row.name)}`
  const a = document.createElement('a')
  a.href = url
  a.download = row.name
  a.click()
}

const handleDelete = async (row) => {
  try {
    await knowledgeApi.delete(row.id, {
      item_type: row.type,
      corp_id: row.corp_id,
      date: row.date,
    })
    ElMessage.success('删除成功')
    loadData()
    loadStats()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const showPermissionDialog = (row) => {
  currentEditItem.value = row
  selectedPermission.value = row.permission || 'public'
  permissionDialogVisible.value = true
}

const savePermission = async () => {
  if (!currentEditItem.value) return

  saving.value = true
  try {
    await knowledgeApi.updatePermission(
      currentEditItem.value.id,
      currentEditItem.value.type,
      currentEditItem.value.corp_id,
      currentEditItem.value.date,
      selectedPermission.value
    )
    ElMessage.success('权限设置成功')
    permissionDialogVisible.value = false
    loadData()
  } catch (error) {
    ElMessage.error('设置失败')
    console.error('保存权限失败:', error)
  } finally {
    saving.value = false
  }
}

const handleBatchCommand = async (command) => {
  if (selectedItems.value.length === 0) {
    ElMessage.warning('请先选择要操作的内容')
    return
  }

  if (command === 'delete') {
    try {
      await ElMessageBox.confirm(
        `确定要删除选中的 ${selectedItems.value.length} 项内容吗？`,
        '批量删除',
        { type: 'warning' }
      )

      let successCount = 0
      for (const item of selectedItems.value) {
        try {
          await knowledgeApi.delete(item.id, {
            item_type: item.type,
            corp_id: item.corp_id,
            date: item.date,
          })
          successCount++
        } catch (e) {
          console.error('删除失败:', e)
        }
      }

      ElMessage.success(`成功删除 ${successCount} 项`)
      loadData()
      loadStats()
    } catch (e) {
      // 用户取消
    }
  } else if (command.startsWith('permission_')) {
    const permission = command.replace('permission_', '')

    try {
      let successCount = 0
      for (const item of selectedItems.value) {
        try {
          await knowledgeApi.updatePermission(
            item.id,
            item.type,
            item.corp_id,
            item.date,
            permission
          )
          successCount++
        } catch (e) {
          console.error('更新权限失败:', e)
        }
      }

      ElMessage.success(`成功更新 ${successCount} 项权限为「${getPermissionName(permission)}」`)
      loadData()
    } catch (e) {
      ElMessage.error('批量操作失败')
    }
  }
}

// 监听组织变化，重新加载数据
watch(currentOrg, () => {
  currentPage.value = 1
  loadData()
  loadStats()
})

onMounted(() => {
  loadData()
  loadStats()
})
</script>

<style scoped>
.knowledge {
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.message-preview .sender {
  color: #409eff;
  font-size: 13px;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.message-preview .content {
  color: #303133;
  font-size: 14px;
}

.file-info .file-name {
  color: #303133;
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

.file-info .file-meta {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}

.preview-content {
  min-height: 200px;
}

.text-preview {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  max-height: 500px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

.image-preview {
  text-align: center;
}

.image-preview img {
  max-width: 100%;
  max-height: 500px;
  border-radius: 8px;
}

.excel-preview .sheet-block {
  margin-bottom: 16px;
}

.excel-preview h4 {
  margin-bottom: 8px;
  color: #303133;
}

.binary-preview {
  text-align: center;
  padding: 40px;
}

.binary-preview p {
  margin-top: 12px;
  color: #606266;
}

.binary-preview .file-size {
  font-size: 14px;
  color: #909399;
}

.binary-preview .file-ext {
  font-size: 12px;
  color: #c0c4cc;
}

.error-preview {
  padding: 20px;
}

/* PDF 预览 */
.pdf-preview .pdf-info {
  text-align: center;
  padding: 20px;
  margin-bottom: 16px;
  background: #fef0f0;
  border-radius: 8px;
}

.pdf-preview .pdf-info p {
  margin-top: 12px;
  color: #606266;
  font-size: 16px;
}

.pdf-preview .page-text {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.5;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

/* Word 预览 */
.word-preview .word-content {
  margin-bottom: 16px;
}

.word-preview .word-tables h4 {
  margin: 16px 0 8px;
  color: #303133;
}

.word-preview .table-block {
  margin-bottom: 12px;
}

/* PPT 预览 */
.ppt-preview .ppt-info {
  text-align: center;
  padding: 20px;
  margin-bottom: 16px;
  background: #fdf6ec;
  border-radius: 8px;
}

.ppt-preview .ppt-info p {
  margin-top: 12px;
  color: #606266;
  font-size: 16px;
}

.ppt-preview .slide-text {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.5;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

.truncated-hint {
  text-align: center;
  color: #909399;
  font-size: 12px;
  margin-top: 12px;
}

/* 权限设置对话框 */
.permission-dialog .item-info {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 8px;
}

.permission-dialog .item-info p {
  margin: 4px 0;
}

.permission-dialog .el-radio {
  display: block;
  margin-bottom: 12px;
}

.permission-dialog .perm-desc {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}

/* 上传区域 */
.upload-area {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  padding: 40px 0;
}

.upload-area :deep(.el-upload__text) {
  margin-top: 12px;
}

.upload-area :deep(.el-upload__tip) {
  margin-top: 8px;
  color: #909399;
  font-size: 12px;
}
</style>
