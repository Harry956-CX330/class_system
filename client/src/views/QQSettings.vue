<template>
  <div class="qq-settings-container">
    <el-card class="page-card" shadow="never">
      <div class="page-header">
        <div class="header-left">
          <div class="title-indicator"></div>
          <h3 class="page-title">QQ 提醒设置</h3>
        </div>
      </div>

      <el-alert 
        title="使用说明" 
        type="info" 
        :closable="false" 
        show-icon
        class="instruction-alert"
      >
        <template #default>
          <div class="alert-content">
            本功能通过 <strong>OneBot 协议</strong> 对接 QQ 机器人实现消息推送。<br />
            你需要部署一个 OneBot 实现（如 
            <el-link href="https://github.com/NapNeko/NapCatQQ" target="_blank" type="primary">NapCatQQ</el-link>、
            <el-link href="https://github.com/LLOneBot/LLOneBot" target="_blank" type="primary">LLOneBot</el-link>），
            将 QQ 号作为机器人登录后，填入下方的 API 地址和群号即可使用。
          </div>
        </template>
      </el-alert>

      <el-form 
        :model="form" 
        :label-width="isMobile ? 'auto' : '140px'" 
        :label-position="isMobile ? 'top' : 'right'" 
        size="large" 
        v-loading="loading"
        class="responsive-form"
      >
        <el-form-item label="启用 QQ 提醒">
          <el-switch v-model="form.enabled" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="API 地址">
          <el-input v-model="form.api_url" placeholder="例如：http://127.0.0.1:5700">
            <template #append>
              <el-button @click="testConnection" :loading="testing">测试连接</el-button>
            </template>
          </el-input>
          <div class="form-tip">OneBot HTTP API 地址，通常为 http://127.0.0.1:5700</div>
        </el-form-item>
        <el-form-item label="群号">
          <el-input v-model="form.group_id" placeholder="请输入用于发群通知的 QQ 群号" />
          <div class="form-tip">群通知消息将发送到此群</div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave" class="save-btn">保存设置</el-button>
        </el-form-item>
      </el-form>

      <el-divider border-style="dashed" />
      
      <div class="api-doc-section">
        <h4>API 接口说明</h4>
        <p class="doc-desc">管理员在文件任务和问卷页面中可使用以下 QQ 提醒功能：</p>
        <el-table :data="apiList" size="small" class="api-table" :header-cell-style="{ background: '#F7F8FA', color: '#4E5969' }">
          <el-table-column prop="name" label="功能" min-width="150" />
          <el-table-column prop="desc" label="说明" min-width="250" />
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import api from '../api'

// 响应式状态管理核心
const isMobile = ref(false)
const checkDevice = () => {
  isMobile.value = window.innerWidth <= 768
}

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)

const form = reactive({
  api_url: '',
  group_id: '',
  enabled: 0,
})

const apiList = [
  { name: '群通知-文件任务', desc: '发布文件任务后，一键向群聊发送新任务通知' },
  { name: '私聊提醒-文件任务', desc: '一键向未提交文件任务的学生私聊发送提醒' },
  { name: '群通知-调查问卷', desc: '发布问卷后，一键向群聊发送新问卷通知' },
  { name: '私聊提醒-调查问卷', desc: '一键向未填写问卷的学生私聊发送提醒' },
]

async function loadConfig() {
  loading.value = true
  try {
    const res = await api.get('/api/qq-config')
    form.api_url = res.data.api_url
    form.group_id = res.data.group_id
    form.enabled = res.data.enabled
  } catch {
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    await api.put('/api/qq-config', {
      api_url: form.api_url,
      group_id: form.group_id,
      enabled: form.enabled,
    })
    ElMessage.success('保存成功')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  if (!form.api_url) return ElMessage.warning('请先填写 API 地址')
  testing.value = true
  try {
    // 分离 base_url 和 access_token
    let baseUrl = form.api_url
    let accessToken = ''
    try {
      const u = new URL(form.api_url)
      accessToken = u.searchParams.get('access_token') || ''
      u.search = ''
      baseUrl = u.toString()
    } catch { /* 非标准 URL 直接用原值 */ }
    const testApi = axios.create({ baseURL: baseUrl, timeout: 5000 })
    const config = {}
    if (accessToken) config.params = { access_token: accessToken }
    const res = await testApi.post('/get_login_info', {}, config)
    ElMessage.success('连接成功！QQ 号：' + (res.data?.data?.user_id || '未知'))
  } catch {
    ElMessage.error('连接失败，请检查 API 地址和机器人是否正常运行')
  } finally {
    testing.value = false
  }
}

// 生命周期挂载与卸载
onMounted(() => {
  checkDevice()
  window.addEventListener('resize', checkDevice)
  loadConfig()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', checkDevice)
})
</script>

<style scoped>
.qq-settings-container {
  padding: 0;
}

.page-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  min-height: calc(100vh - 120px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
}

.title-indicator {
  width: 4px;
  height: 18px;
  background-color: #165DFF;
  border-radius: 2px;
  margin-right: 12px;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1D2129;
}

.instruction-alert {
  margin-bottom: 28px;
  border-radius: 6px;
}

.alert-content {
  margin: 4px 0;
  line-height: 1.8;
  color: #4E5969;
  font-size: 14px;
}

/* PC 端表单限宽，避免横向拉伸过度 */
.responsive-form {
  max-width: 600px;
}

.form-tip {
  font-size: 12px;
  color: #86909C;
  margin-top: 6px;
  line-height: 1.4;
}

.save-btn {
  width: 120px;
}

.api-doc-section h4 {
  font-size: 15px;
  font-weight: 600;
  color: #1D2129;
  margin: 0 0 8px 0;
}

.doc-desc {
  color: #86909C;
  font-size: 13px;
  margin-bottom: 12px;
}

.api-table {
  margin-top: 8px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #E5E6EB;
}

:deep(.api-table::before) {
  display: none;
}

/* 统一输入框焦点高亮 */
:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #165DFF inset !important;
}

/* ================= 移动端适配 ================= */
@media (max-width: 768px) {
  .page-card {
    min-height: auto;
  }

  .alert-content {
    font-size: 13px;
  }

  .responsive-form {
    max-width: 100%;
  }

  /* 移动端保存按钮撑满 */
  .save-btn {
    width: 100%;
    margin-top: 12px;
  }

  /* 去除附加按钮的左右内边距防止拥挤 */
  :deep(.el-input-group__append) {
    padding: 0 12px;
  }
}
</style>