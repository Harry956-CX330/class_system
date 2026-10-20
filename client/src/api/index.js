import axios from 'axios'
import { needsTargetSelection, openNotificationPicker } from '../utils/notificationPicker'
import { ElMessageBox } from 'element-plus'

const api = axios.create({
  baseURL: '',
  timeout: 120000,
})

api.interceptors.request.use(
  async (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    if (/\/(notify|remind|send-email|send-emails|send-dorm-emails|remind-leaders|remind-one|qq-remind-unordered|qq-remind-unordered-email|test-email|resend|submit)$/.test(config.url || '')) config.timeout = 0
    // 管理端视图 → 后端返回全班数据
    const currentView = localStorage.getItem('currentView')
    if (currentView === 'admin') {
      config.headers['X-View-Mode'] = 'admin'
    }
    if (config.method === 'post' && needsTargetSelection(config.url) && !config.skipTargetSelection) {
      const options = (await api.get('/api/notifications/targets', {params:{endpoint:config.url}})).data
      const original = config.data || {}
      config.data = await openNotificationPicker(config.url, options, original)
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // 登录接口的 401（账号密码错误）不触发全局登出
      const isLoginRequest = error.config?.url?.includes('/api/login')
      if (!isLoginRequest) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        localStorage.removeItem('currentView')
        localStorage.removeItem('login_time')
        if (!window.__sessionExpired) {
          window.__sessionExpired = true
          ElMessageBox.alert('登录已过期，请返回登录页重新登录', '提示', {
            type: 'warning',
            confirmButtonText: '返回登录',
            showClose: false,
          })
            .catch(() => {})
            .finally(() => {
              window.location.href = '/login'
            })
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api
