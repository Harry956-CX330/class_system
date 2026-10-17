<template>
  <router-view />
</template>

<script setup>
import { onMounted, onBeforeUnmount } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from './stores/auth'

// 登录会话最多保留 1 小时，超时自动退出
const SESSION_TIMEOUT_MS = 60 * 60 * 1000

const authStore = useAuthStore()
let timer = null

function expireSession() {
  if (window.__sessionExpired) return
  window.__sessionExpired = true
  ElMessageBox.alert('登录已过期，请返回登录页重新登录', '提示', {
    type: 'warning',
    confirmButtonText: '返回登录',
    showClose: false,
  })
    .then(() => {
      authStore.logout()
      window.location.href = '/login'
    })
    .catch(() => {
      authStore.logout()
      window.location.href = '/login'
    })
}

function checkSession() {
  // 登录页不校验
  if (window.location.pathname === '/login') return
  if (!authStore.isLoggedIn) return
  let loginTime = Number(localStorage.getItem('login_time') || 0)
  // 兼容旧会话：无 login_time 时按刚登录处理
  if (!loginTime) {
    localStorage.setItem('login_time', String(Date.now()))
    return
  }
  if (Date.now() - loginTime >= SESSION_TIMEOUT_MS) {
    expireSession()
  }
}

onMounted(() => {
  checkSession()
  timer = setInterval(checkSession, 30 * 1000)
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>
