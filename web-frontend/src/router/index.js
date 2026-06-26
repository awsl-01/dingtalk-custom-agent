import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录', public: true }
  },
  {
    path: '/',
    component: () => import('../components/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '仪表盘', icon: 'DataBoard' }
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('../views/Knowledge.vue'),
        meta: { title: '知识库', icon: 'Collection' }
      },
      {
        path: 'messages',
        name: 'Messages',
        component: () => import('../views/Messages.vue'),
        meta: { title: '消息日志', icon: 'ChatDotRound' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/Users.vue'),
        meta: { title: '用户管理', icon: 'User' }
      },
      {
        path: 'scheduling',
        name: 'Scheduling',
        component: () => import('../views/Scheduling.vue'),
        meta: { title: '排课系统', icon: 'Calendar' }
      },
      {
        path: 'debug',
        name: 'Debug',
        component: () => import('../views/Debug.vue'),
        meta: { title: '对话调试', icon: 'Monitor' }
      },
      {
        path: 'inspection',
        name: 'Inspection',
        component: () => import('../views/Inspection.vue'),
        meta: { title: '巡检管理', icon: 'Warning' }
      },
      {
        path: 'assets',
        name: 'Assets',
        component: () => import('../views/Assets.vue'),
        meta: { title: '资产管理', icon: 'Box' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：检查登录状态
router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '首页'} - 钉钉机器人管理后台`

  // 如果是公开页面（如登录页），直接放行
  if (to.meta.public) {
    next()
    return
  }

  // 检查是否有 token
  const token = localStorage.getItem('dingtalk_token')

  if (!token) {
    // 没有 token，跳转到登录页
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // 有 token，验证是否有效
  import('axios').then(({ default: axios }) => {
    axios.get(`/api/auth/verify?token=${token}`)
      .then(res => {
        if (res.data.valid) {
          next()
        } else {
          // token 无效，清除并跳转到登录页
          localStorage.removeItem('dingtalk_token')
          localStorage.removeItem('dingtalk_user_info')
          next({ path: '/login', query: { redirect: to.fullPath } })
        }
      })
      .catch(() => {
        // 验证失败，跳转到登录页
        localStorage.removeItem('dingtalk_token')
        localStorage.removeItem('dingtalk_user_info')
        next({ path: '/login', query: { redirect: to.fullPath } })
      })
  })
})

export default router
