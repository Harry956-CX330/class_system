import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/role-select',
    name: 'RoleSelect',
    component: () => import('../views/RoleSelect.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: 'appearance', component: () => import('../views/AppearanceSettings.vue'), meta: {title:'登录页外观',requiresAdmin:true} },
      { path: '', redirect: '/dashboard' },
      {
        path: 'dashboard',
        name: 'Dashboard',
        meta: { title: '首页统计' },
      },
      {
        path: 'notices',
        name: 'Notices',
        component: () => import('../views/NoticeList.vue'),
        meta: { title: '通知公告' },
      },
      {
        path: 'grades',
        name: 'Grades',
        component: () => import('../views/GradeList.vue'),
        meta: { title: '成绩管理' },
      },
      {
        path: 'certificates',
        name: 'Certificates',
        component: () => import('../views/CertificateUpload.vue'),
        meta: { title: '奖状管理' },
      },
      {
        path: 'class-meetings',
        name: 'ClassMeeting',
        component: () => import('../views/ClassMeeting.vue'),
        meta: { title: '班会管理', requiresAuth: true },
      },
      {
        path: 'resources/manage',
        name: 'ResourceManage',
        component: () => import('../views/ResourceManage.vue'),
        meta: { title: '资料管理', requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'resources',
        name: 'ResourceBrowse',
        component: () => import('../views/ResourceBrowse.vue'),
        meta: { title: '资料下载', requiresAuth: true },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/UserManagement.vue'),
        meta: { title: '用户管理', requiresAdmin: true },
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('../views/UserProfile.vue'),
        meta: { title: '个人信息', requiresAuth: true },
      },
      {
        path: 'social-practice',
        name: 'SocialPractice',
        component: () => import('../views/SocialPractice.vue'),
        meta: { title: '社会实践', requiresAuth: true },
      },
      {
        path: 'file-tasks',
        name: 'FileTask',
        component: () => import('../views/FileTask.vue'),
        meta: { title: '文件任务', requiresAuth: true },
      },
      {
        path: 'textbook-order',
        name: 'TextbookOrder',
        component: () => import('../views/TextbookOrder.vue'),
        meta: { title: '教材订购', requiresAuth: true },
      },
      {
        path: 'surveys',
        name: 'Survey',
        component: () => import('../views/Survey.vue'),
        meta: { title: '问卷调查', requiresAuth: true },
      },
      {
        path: 'survey-editor',
        name: 'SurveyEditor',
        component: () => import('../views/SurveyEditor.vue'),
        meta: { title: '问卷编辑', requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'groups',
        name: 'Groups',
        component: () => import('../views/GroupManagement.vue'),
        meta: { title: '分组管理' }
      },
      {
        path: 'activities',
        name: 'Activity',
        component: () => import('../views/ActivityManage.vue'),
        meta: { title: '活动管理', requiresAuth: true },
      },
      {
        path: 'qr-checkin',
        name: 'QrCheckin',
        component: () => import('../views/QrCheckin.vue'),
        meta: { title: '扫码签到', requiresAuth: true },
      },
      {
        path: 'qr-checkin/manage',
        name: 'QrCheckinManage',
        component: () => import('../views/QrCheckinManage.vue'),
        meta: { title: '扫码签到管理', requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'email-settings',
        name: 'EmailSettings',
        component: () => import('../views/SmtpSettings.vue'),
        meta: { title: '邮件设置', requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'qq-settings',
        name: 'QQSettings',
        component: () => import('../views/QQSettings.vue'),
        meta: { title: 'QQ提醒', requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'class-committee',
        name: 'ClassCommittee',
        component: () => import('../views/ClassCommitteeManage.vue'),
        meta: { title: '班委通讯录', requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'sheet',
        name: 'OnlineSheet',
        component: () => import('../views/OnlineSheet.vue'),
        meta: { title: '协作表格', requiresAuth: true },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.systemAdmin && authStore.user?.role !== 'admin') { next('/dashboard'); return }

  // 未登录用户只能访问不需要认证的页面
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    next('/login')
    return
  }

  // 普通用户访问管理员页面，重定向到首页
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    next('/dashboard')
    return
  }

  // 普通用户和超管不能访问角色选择页
  if (to.path === '/role-select' && !authStore.isClassLeader) {
    next('/dashboard')
    return
  }

  // 班干登录后未选择视图，且不在角色选择页 → 跳转到角色选择页
  if (
    authStore.isClassLeader &&
    !authStore.currentView &&
    to.path !== '/role-select' &&
    to.path !== '/login'
  ) {
    next('/role-select')
    return
  }

  // 班干已选择视图，访问角色选择页 → 跳转到首页
  if (to.path === '/role-select' && authStore.currentView) {
    next('/dashboard')
    return
  }

  next()
})

export default router
