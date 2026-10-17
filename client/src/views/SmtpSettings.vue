<template>
  <div class="smtp-settings-container">
    <el-card class="page-card" shadow="never">
      <div class="page-header">
        <div class="header-left">
          <div class="title-indicator"></div>
          <h3 class="page-title">邮件服务配置</h3>
        </div>
      </div>

      <el-tabs v-model="activeTab" class="email-tabs" @tab-change="onTabChange">
        <el-tab-pane label="邮件配置" name="config">
          <el-alert 
            title="配置说明" 
            type="info" 
            :closable="false" 
            show-icon
            class="config-alert"
          >
            <template #default>
              <div class="alert-content">
                请配置 QQ 邮箱 SMTP 服务以启用邮件通知功能。<br/>
                1. 登录 QQ 邮箱 → 设置 → 账户 → 开启 POP3/SMTP 服务<br/>
                2. 获取授权码（非邮箱密码）作为下方"密码"<br/>
                3. 填入下方表单并保存即可
              </div>
            </template>
          </el-alert>

          <el-form 
            :model="config" 
            label-width="100px" 
            size="large" 
            label-position="top"
            class="responsive-form"
          >
            <el-form-item label="SMTP 服务器">
              <el-input v-model="config.host" placeholder="smtp.qq.com" />
            </el-form-item>
            <el-form-item label="端口">
              <el-input-number v-model="config.port" :min="1" :max="65535" style="width: 100%;" />
            </el-form-item>
            <el-form-item label="发件邮箱">
              <el-input v-model="config.username" placeholder="your-email@qq.com" />
            </el-form-item>
            <el-form-item label="授权码 / 密码">
              <el-input v-model="config.password" type="password" show-password placeholder="QQ邮箱授权码" />
            </el-form-item>
            <el-form-item class="form-actions-item">
              <div class="form-actions">
                <el-button type="primary" :loading="saving" @click="handleSave" class="action-btn">
                  保存配置
                </el-button>
                <el-button :loading="testing" @click="handleTest" class="action-btn test-btn">
                  测试发送
                </el-button>
              </div>
            </el-form-item>
          </el-form>

          <div class="status-indicator">
            <template v-if="status.configured">
              <el-tag type="success" size="large">已配置</el-tag>
              <span class="status-text">
                当前发件邮箱：{{ status.username }}
              </span>
            </template>
            <template v-else>
              <el-tag type="warning" size="large">未配置</el-tag>
              <span class="status-text">
                请填写上方信息并保存
              </span>
            </template>
          </div>
        </el-tab-pane>

        <el-tab-pane label="发送历史" name="history">
          <div class="history-toolbar">
            <div class="filter-group">
              <el-select v-model="historyFilter.status" placeholder="发送状态" clearable style="width: 130px;" @change="loadHistory">
                <el-option label="全部" value="" />
                <el-option label="发送成功" value="sent" />
                <el-option label="发送失败" value="failed" />
              </el-select>
              <el-select v-model="historyFilter.send_type" placeholder="邮件类型" clearable style="width: 130px;" @change="loadHistory">
                <el-option label="全部" value="" />
                <el-option label="测试邮件" value="test" />
                <el-option label="通知公告" value="notice" />
                <el-option label="文件任务" value="file_task" />
                <el-option label="调查问卷" value="survey" />
              </el-select>
            </div>
            <el-button 
              type="danger" 
              plain 
              :loading="resending" 
              @click="handleResendAll"
              :disabled="failedCount === 0"
              class="resend-btn"
            >
              一键重发失败邮件 ({{ failedCount }})
            </el-button>
          </div>

          <el-table v-if="!isMobile" :data="historyList" stripe v-loading="historyLoading" class="history-table">
            <el-table-column prop="created_at" label="发送时间" width="160">
              <template #default="{ row }">
                <span class="time-text">{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="recipient_email" label="收件人" min-width="180" show-overflow-tooltip />
            <el-table-column prop="subject" label="邮件主题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="send_type" label="类型" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="typeTagType(row.send_type)">
                  {{ typeLabel(row.send_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'sent' ? 'success' : 'danger'">
                  {{ row.status === 'sent' ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="error_message" label="错误信息" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.error_message" class="error-msg">{{ row.error_message }}</span>
                <span v-else class="no-error">-</span>
              </template>
            </el-table-column>
          </el-table>

          <div v-else class="mobile-history-list" v-loading="historyLoading">
            <el-card v-for="row in historyList" :key="row.id" class="history-card" shadow="sm">
              <div class="card-header">
                <span class="subject-text">{{ row.subject }}</span>
                <el-tag size="small" :type="row.status === 'sent' ? 'success' : 'danger'">
                  {{ row.status === 'sent' ? '成功' : '失败' }}
                </el-tag>
              </div>
              <div class="card-body">
                <div class="info-row">
                  <span class="label">收件人：</span>
                  <span class="value">{{ row.recipient_email }}</span>
                </div>
                <div class="info-row">
                  <span class="label">类型：</span>
                  <span class="value">
                    <el-tag size="small" :type="typeTagType(row.send_type)">{{ typeLabel(row.send_type) }}</el-tag>
                  </span>
                </div>
                <div class="info-row">
                  <span class="label">时间：</span>
                  <span class="value time-text">{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</span>
                </div>
                <div v-if="row.error_message" class="info-row error-row">
                  <span class="label">错误：</span>
                  <span class="value error-msg">{{ row.error_message }}</span>
                </div>
              </div>
            </el-card>
            <el-empty v-if="historyList.length === 0" description="暂无发送记录" />
          </div>

          <div class="history-pagination">
            <el-pagination
              v-model:current-page="historyPage"
              v-model:page-size="historyPageSize"
              :total="historyTotal"
              :page-sizes="[10, 20, 50]"
              :layout="isMobile ? 'prev, pager, next' : 'total, sizes, prev, pager, next'"
              :small="isMobile"
              @current-change="loadHistory"
              @size-change="loadHistory"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const activeTab = ref('config')

// ─── 响应式状态管理 ───
const isMobile = ref(false)
const checkDevice = () => {
  isMobile.value = window.innerWidth <= 768
}

// ─── SMTP 配置 ───
const config = reactive({
  host: 'smtp.qq.com',
  port: 587,
  username: '',
  password: '',
})

const status = reactive({
  configured: false,
  username: '',
})

const saving = ref(false)
const testing = ref(false)

async function loadConfig() {
  try {
    const res = await api.get('/api/smtp-config')
    config.host = res.data.host
    config.port = res.data.port
    config.username = res.data.username
    config.password = ''
    status.configured = res.data.configured
    status.username = res.data.username
  } catch {
    ElMessage.error('加载配置失败')
  }
}

async function handleSave() {
  saving.value = true
  try {
    await api.put('/api/smtp-config', { ...config })
    status.configured = true
    status.username = config.username
    config.password = ''
    ElMessage.success('SMTP 配置已保存')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  const email = await ElMessageBox.prompt('请输入测试接收邮箱', '测试发送', {
    confirmButtonText: '发送测试',
    cancelButtonText: '取消',
    inputPattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    inputErrorMessage: '请输入有效的邮箱地址',
  }).catch(() => null)
  if (!email?.value) return

  testing.value = true
  try {
    await api.post('/api/smtp-config/test-email', { email: email.value })
    ElMessage.success('测试邮件发送成功，请检查收件箱')
    if (activeTab.value === 'history') loadHistory()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '测试失败，请检查配置')
  } finally {
    testing.value = false
  }
}

// ─── 发送历史 ───
const historyList = ref([])
const historyLoading = ref(false)
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = ref(20)
const failedCount = ref(0)
const resending = ref(false)

const historyFilter = reactive({
  status: '',
  send_type: '',
})

async function loadHistory() {
  historyLoading.value = true
  try {
    const params = {
      page: historyPage.value,
      page_size: historyPageSize.value,
    }
    if (historyFilter.status) params.status = historyFilter.status
    if (historyFilter.send_type) params.send_type = historyFilter.send_type
    const res = await api.get('/api/email-history', { params })
    historyList.value = res.data.items
    historyTotal.value = res.data.total
    // 统计失败数
    if (!historyFilter.status && !historyFilter.send_type) {
      // 仅在全量查询时更新失败计数
      try {
        const failRes = await api.get('/api/email-history', { params: { page: 1, page_size: 1, status: 'failed' } })
        failedCount.value = failRes.data.total
      } catch { /* ignore */ }
    }
  } catch {
    ElMessage.error('加载发送历史失败')
  } finally {
    historyLoading.value = false
  }
}

// 切换 tab 时加载历史
function onTabChange(name) {
  if (name === 'history') {
    loadHistory()
  }
}

async function handleResendAll() {
  try {
    await ElMessageBox.confirm(
      `确定要重新发送所有失败的邮件吗？共 ${failedCount.value} 封。`,
      '确认重发',
      { confirmButtonText: '确定重发', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }

  resending.value = true
  try {
    const res = await api.post('/api/email-history/resend')
    const data = res.data
    if (data.failed > 0) {
      ElMessage.warning(`重发完成：成功 ${data.resent} 封，失败 ${data.failed} 封`)
    } else {
      ElMessage.success(`全部重发成功，共 ${data.resent} 封`)
    }
    loadHistory()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '重发失败')
  } finally {
    resending.value = false
  }
}

function typeLabel(type) {
  const map = { test: '测试', notice: '通知', file_task: '文件任务', survey: '问卷' }
  return map[type] || type
}

function typeTagType(type) {
  const map = { test: 'info', notice: 'primary', file_task: 'warning', survey: 'success' }
  return map[type] || 'info'
}

onMounted(() => {
  checkDevice()
  window.addEventListener('resize', checkDevice)
  loadConfig()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkDevice)
})
</script>

<style scoped>
.smtp-settings-container {
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
  color: var(--el-text-color-primary);
}

.config-alert {
  margin-bottom: 24px;
  border-radius: 6px;
}

.alert-content {
  margin: 0;
  line-height: 1.8;
  color: var(--el-text-color-regular);
}

.responsive-form {
  width: 100%;
  max-width: 520px;
}

/* 按钮区域 */
.form-actions {
  display: flex;
  gap: 12px;
  width: 100%;
}

.action-btn {
  width: 120px;
}

.status-indicator {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #E5E6EB;
  max-width: 520px;
  display: flex;
  align-items: center;
}

.status-text {
  color: var(--el-text-color-secondary);
  margin-left: 12px;
  font-size: 14px;
}

/* ─── 邮件历史 ─── */
.email-tabs {
  margin-top: -8px;
}

.history-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-group {
  display: flex;
  gap: 10px;
}

.history-table {
  width: 100%;
}

.time-text {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: var(--el-text-color-regular);
}

.error-msg {
  color: #F53F3F;
  font-size: 13px;
}

.no-error {
  color: #C9CDD4;
}

.history-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* ─── 移动端历史卡片 ─── */
.mobile-history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-card {
  border-radius: 8px;
  border: 1px solid #E5E6EB;
}

.history-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #F2F3F5;
  gap: 8px;
}

.history-card .subject-text {
  font-weight: 600;
  font-size: 15px;
  color: var(--el-text-color-primary);
  line-height: 1.4;
  word-break: break-all;
}

.history-card .info-row {
  display: flex;
  margin-bottom: 6px;
  font-size: 13px;
  line-height: 1.5;
}

.history-card .info-row:last-child {
  margin-bottom: 0;
}

.history-card .label {
  color: var(--el-text-color-secondary);
  width: 60px;
  flex-shrink: 0;
}

.history-card .value {
  color: var(--el-text-color-regular);
  flex: 1;
  word-break: break-all;
}

.history-card .error-row {
  margin-top: 8px;
  background-color: #FFECE8;
  padding: 8px;
  border-radius: 4px;
}

/* =======================================
   移动端响应式适配
   ======================================= */
@media screen and (max-width: 768px) {
  .page-card {
    min-height: auto;
  }

  .alert-content {
    font-size: 13px;
  }

  :deep(.form-actions-item .el-form-item__content) {
    margin-bottom: 0;
  }

  .form-actions {
    flex-direction: column;
    gap: 12px;
  }

  .action-btn {
    width: 100%;
    margin-left: 0 !important;
  }

  .status-indicator {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .status-text {
    margin-left: 0;
  }

  .history-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-group {
    flex-wrap: wrap;
  }

  .filter-group .el-select {
    flex: 1; /* 让下拉框在手机端平分宽度 */
    width: auto !important;
  }
  
  .resend-btn {
    width: 100%;
    margin-left: 0 !important;
  }

  .history-pagination {
    justify-content: center; /* 手机端分页居中 */
  }
}
</style>