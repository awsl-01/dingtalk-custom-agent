import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截器：自动添加 token
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('dingtalk_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    // 如果是 401 错误，清除 token 并跳转到登录页
    if (error.response?.status === 401) {
      localStorage.removeItem('dingtalk_token')
      localStorage.removeItem('dingtalk_user_info')
      window.location.href = '/login'
    }
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 用户信息管理（本地存储）
export const userInfo = {
  get() {
    const stored = localStorage.getItem('dingtalk_user_info')
    if (stored) {
      try {
        return JSON.parse(stored)
      } catch {
        return null
      }
    }
    return null
  },
  set(userId, userName) {
    localStorage.setItem('dingtalk_user_info', JSON.stringify({
      user_id: userId,
      user_name: userName,
    }))
  },
  clear() {
    localStorage.removeItem('dingtalk_user_info')
  },
  isLoggedIn() {
    return !!this.get()?.user_name
  },
  getUserId() {
    return this.get()?.user_id || 'web_user'
  },
  getUserName() {
    return this.get()?.user_name || 'Web用户'
  },
}

// 仪表盘 API
export const dashboardApi = {
  getStats: (params) => api.get('/dashboard/stats', { params }),
  getRecentActivity: (params) => api.get('/dashboard/recent-activity', { params }),
  getSkillStats: (params) => api.get('/dashboard/skill-stats', { params }),
}

// 组织管理 API
export const organizationApi = {
  getList: () => api.get('/organizations/list'),
  getStats: (params) => api.get('/organizations/stats', { params }),
  updateName: (corpId, name) => api.put(`/organizations/${corpId}/name`, { name }),
}

// 用户管理 API
export const userApi = {
  getList: (corpId, params) => api.get('/users/list', { params: { corp_id: corpId, ...params } }),
  getStats: (corpId) => api.get('/users/stats', { params: { corp_id: corpId } }),
  getRoles: () => api.get('/users/roles'),
  getPermissions: () => api.get('/users/permissions'),
  create: (corpId, data) => api.post('/users/', data, { params: { corp_id: corpId } }),
  update: (userId, corpId, data) => api.put(`/users/${userId}`, data, { params: { corp_id: corpId } }),
  delete: (userId, corpId) => api.delete(`/users/${userId}`, { params: { corp_id: corpId } }),
}

// 排课系统 API
export const schedulingApi = {
  getSchedule: (corpId, classId) => api.get('/scheduling/schedule', { params: { corp_id: corpId, class_id: classId } }),
  getClasses: (corpId) => api.get('/scheduling/classes', { params: { corp_id: corpId } }),
  getTeachers: (corpId) => api.get('/scheduling/teachers', { params: { corp_id: corpId } }),
  getSwapRequests: (corpId, status) => api.get('/scheduling/swap-requests', { params: { corp_id: corpId, status } }),
  createSwapRequest: (corpId, data) => api.post('/scheduling/swap-requests', data, {
    params: { corp_id: corpId, user_id: userInfo.getUserId(), user_name: userInfo.getUserName() }
  }),
  approveSwapRequest: (swapId, corpId, data) => api.put(`/scheduling/swap-requests/${swapId}/approve`, data, {
    params: { corp_id: corpId, approver_id: userInfo.getUserId(), approver_name: userInfo.getUserName() }
  }),
  cancelSwapRequest: (swapId, corpId) => api.delete(`/scheduling/swap-requests/${swapId}`, {
    params: { corp_id: corpId, user_id: userInfo.getUserId() }
  }),
  getSwapLog: (corpId) => api.get('/scheduling/swap-log', { params: { corp_id: corpId } }),
}

// 知识库 API
export const knowledgeApi = {
  getList: (params) => api.get('/knowledge/list', { params }),
  search: (params) => api.get('/knowledge/search', { params }),
  getStats: (params) => api.get('/knowledge/stats', { params }),
  delete: (itemId, params) => api.delete(`/knowledge/${itemId}`, { params }),
  preview: (filePath) => api.get('/knowledge/preview', { params: { file_path: filePath } }),
  download: (filePath, fileName) => `/api/knowledge/download?file_path=${encodeURIComponent(filePath)}&file_name=${encodeURIComponent(fileName)}`,
  getStructured: (params) => api.get('/knowledge/structured', { params }),
  updatePermission: (itemId, itemType, corpId, date, permission) =>
    api.put(`/knowledge/${itemId}/permission`, { permission }, { params: { item_type: itemType, corp_id: corpId, date } }),
  upload: (formData, params) => api.post('/knowledge/upload', formData, { params, headers: { 'Content-Type': 'multipart/form-data' } }),
}

// 消息日志 API
export const messagesApi = {
  getList: (params) => api.get('/messages/list', { params }),
  getDetail: (msgId) => api.get(`/messages/${msgId}`),
  getStats: (params) => api.get('/messages/stats/overview', { params }),
}

// 对话调试 API
export const debugApi = {
  chat: (data) => api.post('/debug/chat', data),
  getSkills: () => api.get('/debug/skills'),
  getConfig: () => api.get('/debug/config'),
}

export default api
