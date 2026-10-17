import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  // 管理员选择的视图模式: 'user' 用户端 | 'admin' 管理端 | null 未选择
  const currentView = ref(localStorage.getItem('currentView') || null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin' || user.value?.is_class_leader === true)
  const isClassLeader = computed(() => user.value?.is_class_leader === true)
  // 管理端全量数据视图：超管始终可见，班干需切换到管理端才可见
  const canViewAllData = computed(() => {
    if (user.value?.role === 'admin') return true
    if (user.value?.is_class_leader && currentView.value === 'admin') return true
    return false
  })

  function login(tokenVal, userVal) {
    token.value = tokenVal
    user.value = userVal
    // 登录时清除之前的视图选择
    currentView.value = null
    localStorage.removeItem('currentView')
    localStorage.setItem('token', tokenVal)
    localStorage.setItem('user', JSON.stringify(userVal))
    localStorage.setItem('login_time', String(Date.now()))
  }

  function setView(view) {
    currentView.value = view
    localStorage.setItem('currentView', view)
  }

  function logout() {
    token.value = ''
    user.value = null
    currentView.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('currentView')
    localStorage.removeItem('login_time')
  }

  return { token, user, isLoggedIn, isAdmin, isClassLeader, canViewAllData, currentView, login, setView, logout }
})
