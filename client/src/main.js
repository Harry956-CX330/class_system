import { createApp, defineAsyncComponent } from 'vue'
import { createPinia } from 'pinia'
import { ElConfigProvider } from 'element-plus'
import 'element-plus/theme-chalk/base.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './theme'
import 'element-plus/theme-chalk/el-message.css'
import 'element-plus/theme-chalk/el-message-box.css'
import 'element-plus/theme-chalk/el-notification.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import App from './App.vue'
import RichContent from './components/RichContent.vue'
import './styles/theme.css'
import router from './router'

const app = createApp(App)
app.component('RichEditor', defineAsyncComponent(() => import('./components/RichEditor.vue')))
app.component('RichContent', RichContent)
app.use(createPinia())
app.use(router)

app.mount('#app')

window.addEventListener('beforeinstallprompt', event => { event.preventDefault(); window.__installPrompt = event })
if (import.meta.env.PROD && 'serviceWorker' in navigator && window.isSecureContext) {
  const register = () => navigator.serviceWorker.register('/sw.js').catch(() => {})
  if (document.readyState === 'complete') register()
  else window.addEventListener('load', register, { once: true })
}
