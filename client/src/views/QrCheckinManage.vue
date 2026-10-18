<template>
  <div class="qr-manage-page">
    <div class="page-card">
      <div class="page-head">
        <h2>扫码签到管理</h2>
        <p>创建限时签到任务，支持静态与动态二维码，防止截图代签</p>
      </div>

      <div class="create-form">
        <el-form :inline="true" @submit.prevent>
          <el-form-item label="签到名称">
            <el-input v-model="form.name" placeholder="例如：周一班会签到" clearable style="width: 220px" />
          </el-form-item>
          <el-form-item label="有效时长(分钟)">
            <el-input-number v-model="form.duration_minutes" :min="1" :max="1440" style="width: 140px" />
          </el-form-item>
          <el-form-item label="二维码类型">
            <el-radio-group v-model="form.qr_type">
              <el-radio-button value="static">静态</el-radio-button>
              <el-radio-button value="dynamic">动态</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="form.qr_type === 'dynamic'" label="刷新间隔">
            <el-select v-model="form.refresh_seconds" style="width: 110px">
              <el-option label="3 秒" :value="3" />
              <el-option label="5 秒" :value="5" />
              <el-option label="10 秒" :value="10" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="creating" @click="createTask">新建签到</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table :data="tasks" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="签到名称" min-width="160" />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag :type="row.qr_type === 'dynamic' ? 'warning' : 'info'">
              {{ row.qr_type === 'dynamic' ? '动态' : '静态' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status === 'active' ? '进行中' : '已关闭' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="已签/请假/总" width="130">
          <template #default="{ row }">
            {{ row.signed_count }} / {{ row.leave_count }} / {{ row.total_students }}
          </template>
        </el-table-column>
        <el-table-column label="截止时间" width="170">
          <template #default="{ row }">{{ formatTime(row.expires_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" min-width="280">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="openQr(row)">二维码</el-button>
            <el-button size="small" @click="openRecords(row)">名单</el-button>
            <el-button size="small" @click="exportTask(row)">导出</el-button>
            <el-button v-if="row.status === 'active'" size="small" type="warning" @click="closeTask(row)">关闭</el-button>
            <el-button size="small" type="danger" plain @click="deleteTask(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="qrVisible" title="签到二维码" width="420px" @close="stopQrTimer">
      <div class="qr-dialog">
        <div class="qr-task-name">{{ qrTask?.name }}</div>
        <img v-if="qrDataUrl" :src="qrDataUrl" class="qr-image" alt="签到二维码" />
        <div v-if="qrTask?.qr_type === 'dynamic'" class="qr-countdown">
          距离下次刷新还有 <b>{{ countdown }}</b> 秒
        </div>
        <div v-else class="qr-countdown">静态二维码，全程有效</div>
      </div>
    </el-dialog>

    <el-dialog v-model="recordsVisible" :title="`签到名单 · ${recordsTask?.name || ''}`" width="760px">
      <el-table :data="records" v-loading="recordsLoading" max-height="520" :row-class-name="rowClassName">
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="student_no" label="学号" width="130" />
        <el-table-column label="签到时间" min-width="160">
          <template #default="{ row }">{{ formatTime(row.sign_time) }}</template>
        </el-table-column>
        <el-table-column prop="device_id" label="设备标识" min-width="150" show-overflow-tooltip />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170">
          <template #default="{ row }">
            <el-button size="small" type="success" plain @click="markManual(row)">设为已签到</el-button>
            <el-button size="small" type="warning" plain @click="markLeave(row)">请假</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const loading = ref(false)
const creating = ref(false)
const tasks = ref([])
const form = reactive({ name: '', duration_minutes: 10, qr_type: 'static', refresh_seconds: 3 })

const qrVisible = ref(false)
const qrTask = ref(null)
const qrDataUrl = ref('')
const countdown = ref(0)
let countdownTimer = null

const recordsVisible = ref(false)
const recordsTask = ref(null)
const records = ref([])
const recordsLoading = ref(false)

function formatTime(value) {
  if (!value) return ''
  return String(value).replace('T', ' ').slice(0, 19)
}

function statusLabel(status) {
  return { auto: '已签到', manual: '已签到(补签)', leave: '请假', absent: '未签到' }[status] || status
}

function statusTag(status) {
  return { auto: 'success', manual: 'success', leave: 'warning', absent: 'danger' }[status] || 'info'
}

function rowClassName({ row }) {
  return row.status === 'absent' ? 'absent-row' : ''
}

async function loadTasks() {
  loading.value = true
  try {
    const res = await api.get('/api/qr-checkin/tasks')
    tasks.value = res.data
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function createTask() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写签到名称')
    return
  }
  creating.value = true
  try {
    await api.post('/api/qr-checkin/tasks', {
      name: form.name.trim(),
      duration_minutes: form.duration_minutes,
      qr_type: form.qr_type,
      refresh_seconds: form.qr_type === 'dynamic' ? form.refresh_seconds : null,
    })
    ElMessage.success('签到已创建')
    form.name = ''
    loadTasks()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

async function openQr(row) {
  qrTask.value = row
  qrVisible.value = true
  if (row.qr_type === 'dynamic') {
    await refreshQr()
  } else {
    const res = await api.get(`/api/qr-checkin/tasks/${row.id}`)
    qrDataUrl.value = res.data.qr_data_url
    countdown.value = 0
  }
  startQrTimer()
}

async function refreshQr() {
  if (!qrTask.value) return
  const res = await api.post(`/api/qr-checkin/tasks/${qrTask.value.id}/refresh-code`)
  qrDataUrl.value = res.data.qr_data_url
  qrTask.value = { ...qrTask.value, ...res.data }
  countdown.value = res.data.refresh_seconds || 0
}

function startQrTimer() {
  stopQrTimer()
  if (qrTask.value?.qr_type !== 'dynamic') return
  countdownTimer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      countdown.value = qrTask.value?.refresh_seconds || 3
      refreshQr().catch(() => {})
    }
  }, 1000)
}

function stopQrTimer() {
  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = null
}

async function openRecords(row) {
  recordsTask.value = row
  recordsVisible.value = true
  recordsLoading.value = true
  try {
    const res = await api.get(`/api/qr-checkin/tasks/${row.id}/records`)
    records.value = res.data.records
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '名单加载失败')
  } finally {
    recordsLoading.value = false
  }
}

async function updateRecord(row, status) {
  try {
    await api.put(`/api/qr-checkin/tasks/${recordsTask.value.id}/manual`, {
      student_id: row.student_id,
      status,
    })
    ElMessage.success('状态已更新')
    openRecords(recordsTask.value)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '更新失败')
  }
}

function markManual(row) {
  updateRecord(row, 'manual')
}

function markLeave(row) {
  updateRecord(row, 'leave')
}

async function exportTask(row) {
  try {
    const res = await api.get(`/api/qr-checkin/tasks/${row.id}/export`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const link = document.createElement('a')
    link.href = url
    link.download = `${row.name}_签到名单.xlsx`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

async function closeTask(row) {
  try {
    await ElMessageBox.confirm(`确定提前关闭「${row.name}」吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await api.post(`/api/qr-checkin/tasks/${row.id}/close`)
    ElMessage.success('签到已关闭')
    loadTasks()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '关闭失败')
  }
}

async function deleteTask(row) {
  try {
    await ElMessageBox.confirm(`删除后签到记录无法恢复，确定删除「${row.name}」吗？`, '危险操作', { type: 'error' })
  } catch {
    return
  }
  try {
    await api.delete(`/api/qr-checkin/tasks/${row.id}`)
    ElMessage.success('已删除')
    loadTasks()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}

onMounted(loadTasks)
onBeforeUnmount(stopQrTimer)
</script>

<style scoped>
.qr-manage-page {
  padding: 16px;
}

.page-card {
  background: var(--el-bg-color);
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.06);
}

.page-head {
  margin-bottom: 16px;
}

.page-head h2 {
  margin: 0 0 6px;
  font-size: 20px;
}

.page-head p {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.create-form {
  margin-bottom: 16px;
}

.qr-dialog {
  text-align: center;
}

.qr-task-name {
  font-weight: 600;
  margin-bottom: 12px;
}

.qr-image {
  width: 240px;
  height: 240px;
  image-rendering: pixelated;
}

.qr-countdown {
  margin-top: 12px;
  color: #409eff;
  font-size: 14px;
}

:deep(.absent-row) {
  color: #f56c6c;
  font-weight: 600;
}
</style>
