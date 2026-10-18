<template>
  <div class="qr-manage-page">
    <section class="page-card">
      <div class="page-head">
        <div><h2>扫码签到管理</h2><p>创建限时签到，展示二维码并管理签到名单</p></div>
        <el-button :loading="loading" @click="loadTasks">刷新列表</el-button>
      </div>
      <div class="overview"><span>签到任务 <b>{{ tasks.length }}</b></span><span>进行中 <b>{{ tasks.filter(isActive).length }}</b></span><span>支持静态 / 动态二维码</span></div>
      <el-form class="create-form" label-position="top" @submit.prevent="createTask">
        <el-form-item label="签到名称" class="name-field"><el-input v-model="form.name" maxlength="100" placeholder="例如：周一班会签到" clearable /></el-form-item>
        <el-form-item label="有效时长（分钟）"><el-input-number v-model="form.duration_minutes" :min="1" :max="1440" :precision="0" controls-position="right" /></el-form-item>
        <el-form-item label="二维码类型"><el-radio-group v-model="form.qr_type"><el-radio-button value="static">静态</el-radio-button><el-radio-button value="dynamic">动态</el-radio-button></el-radio-group></el-form-item>
        <el-form-item v-if="form.qr_type === 'dynamic'" label="刷新间隔"><el-select v-model="form.refresh_seconds"><el-option v-for="seconds in [3, 5, 10]" :key="seconds" :label="`${seconds} 秒`" :value="seconds" /></el-select></el-form-item>
        <el-form-item class="create-action"><el-button type="primary" native-type="submit" :loading="creating">新建签到</el-button></el-form-item>
      </el-form>
      <div v-if="compact" v-loading="loading" class="task-cards">
        <el-empty v-if="!tasks.length" description="暂无签到任务，先创建一个吧" />
        <article v-for="row in tasks" :key="row.id" class="task-card">
          <div class="card-heading"><h3>{{ row.name }}</h3><el-tag :type="isActive(row) ? 'success' : 'info'">{{ taskStatus(row) }}</el-tag></div>
          <p class="task-meta">#{{ row.id }} · {{ row.qr_type === 'dynamic' ? '动态二维码' : '静态二维码' }}</p>
          <div class="counts"><span><b>{{ row.signed_count }}</b>已签到</span><span><b>{{ row.leave_count }}</b>请假</span><span><b>{{ row.total_students }}</b>总人数</span></div>
          <p class="task-meta">截止：{{ formatTime(row.expires_at) }}</p>
          <div class="row-actions">
            <el-button type="primary" :disabled="!isActive(row)" @click="openQr(row)">二维码</el-button><el-button @click="openRecords(row)">名单</el-button><el-button @click="exportTask(row)">导出</el-button>
            <el-button v-if="isActive(row)" type="warning" plain @click="closeTask(row)">关闭</el-button><el-button type="danger" plain @click="deleteTask(row)">删除</el-button>
          </div>
        </article>
      </div>
      <div v-else class="table-wrap">
        <p class="table-hint">表格内容较多时，可左右滑动查看。</p>
        <el-table :data="tasks" v-loading="loading" row-key="id" empty-text="暂无签到任务">
          <el-table-column prop="name" label="签到名称" min-width="180" show-overflow-tooltip />
          <el-table-column label="类型" width="80"><template #default="{ row }">{{ row.qr_type === 'dynamic' ? '动态' : '静态' }}</template></el-table-column>
          <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="isActive(row) ? 'success' : 'info'">{{ taskStatus(row) }}</el-tag></template></el-table-column>
          <el-table-column label="已签 / 请假 / 总人数" width="165"><template #default="{ row }">{{ row.signed_count }} / {{ row.leave_count }} / {{ row.total_students }}</template></el-table-column>
          <el-table-column label="截止时间" width="175"><template #default="{ row }">{{ formatTime(row.expires_at) }}</template></el-table-column>
          <el-table-column label="操作" width="330"><template #default="{ row }"><div class="row-actions">
            <el-button size="small" type="primary" :disabled="!isActive(row)" @click="openQr(row)">二维码</el-button><el-button size="small" @click="openRecords(row)">名单</el-button><el-button size="small" @click="exportTask(row)">导出</el-button>
            <el-button v-if="isActive(row)" size="small" type="warning" plain @click="closeTask(row)">关闭</el-button><el-button size="small" type="danger" plain @click="deleteTask(row)">删除</el-button>
          </div></template></el-table-column>
        </el-table>
      </div>
    </section>
    <el-dialog v-model="qrVisible" title="签到二维码" width="min(420px, calc(100vw - 24px))" @close="closeQr">
      <div v-loading="qrLoading" class="qr-dialog">
        <h3 class="qr-task-name">{{ qrTask?.name }}</h3>
        <img v-if="qrDataUrl" :src="qrDataUrl" class="qr-image" alt="签到二维码" />
        <el-alert v-if="qrError" :title="qrError" type="warning" :closable="false" show-icon />
        <el-button v-if="qrError" class="retry-button" @click="loadQr">重新加载</el-button>
        <p v-if="qrDataUrl" class="qr-countdown">{{ qrTask?.qr_type === 'dynamic' ? `下次刷新：${countdown} 秒` : '静态二维码，有效期内可使用' }}</p>
        <p class="task-meta">截止：{{ formatTime(qrTask?.expires_at) }}</p>
      </div>
    </el-dialog>
    <el-dialog v-model="recordsVisible" :title="`签到名单 · ${recordsTask?.name || ''}`" width="min(1000px, calc(100vw - 24px))" class="records-dialog">
      <div class="records-toolbar">
        <el-input v-model="recordSearch" placeholder="搜索姓名或学号" clearable aria-label="搜索姓名或学号" />
        <el-select v-model="recordStatus" placeholder="全部状态" aria-label="筛选签到状态"><el-option label="全部状态" value="" /><el-option v-for="status in ['auto', 'manual', 'leave', 'absent']" :key="status" :label="statusLabel(status)" :value="status" /></el-select>
        <el-button :loading="recordsLoading" @click="loadRecords">刷新名单</el-button>
      </div>
      <p class="records-summary">已签到 {{ records.filter(row => ['auto', 'manual'].includes(row.status)).length }} · 请假 {{ records.filter(row => row.status === 'leave').length }} · 未签到 {{ records.filter(row => row.status === 'absent').length }} · 当前显示 {{ filteredRecords.length }} 人</p>
      <div v-if="compact" v-loading="recordsLoading" class="record-cards">
        <el-empty v-if="!filteredRecords.length" description="没有符合条件的同学" />
        <article v-for="row in filteredRecords" :key="row.student_id" class="record-card">
          <div class="card-heading"><h3>{{ row.name }}</h3><el-tag :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag></div>
          <p>学号：{{ row.student_no }}</p><p>签到时间：{{ formatTime(row.sign_time) || '—' }}</p><p v-if="row.device_id" class="device-id">设备：{{ row.device_id }}</p>
          <div v-if="canManageRecords" class="row-actions"><el-button type="success" plain :loading="updatingStudent === row.student_id" :disabled="updatingStudent !== null || ['auto', 'manual'].includes(row.status)" @click="updateRecord(row, 'manual')">设为已签到</el-button><el-button type="warning" plain :disabled="updatingStudent !== null || row.status === 'leave'" @click="updateRecord(row, 'leave')">设为请假</el-button></div>
        </article>
      </div>
      <div v-else class="table-wrap">
        <p class="table-hint">表格可左右滑动查看设备及操作。</p>
        <el-table :data="filteredRecords" v-loading="recordsLoading" max-height="min(520px, 55dvh)" row-key="student_id">
          <el-table-column prop="name" label="姓名" width="100" /><el-table-column prop="student_no" label="学号" width="150" />
          <el-table-column label="状态" width="130"><template #default="{ row }"><el-tag :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag></template></el-table-column>
          <el-table-column label="签到时间" width="175"><template #default="{ row }">{{ formatTime(row.sign_time) || '—' }}</template></el-table-column><el-table-column prop="device_id" label="设备标识" min-width="150" show-overflow-tooltip />
          <el-table-column v-if="canManageRecords" label="操作" width="205"><template #default="{ row }"><div class="row-actions"><el-button size="small" type="success" plain :loading="updatingStudent === row.student_id" :disabled="updatingStudent !== null || ['auto', 'manual'].includes(row.status)" @click="updateRecord(row, 'manual')">设为已签到</el-button><el-button size="small" type="warning" plain :disabled="updatingStudent !== null || row.status === 'leave'" @click="updateRecord(row, 'leave')">请假</el-button></div></template></el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
const media = window.matchMedia('(max-width: 1024px)')
const compact = ref(media.matches)
const loading = ref(false), creating = ref(false), tasks = ref([])
const form = reactive({ name: '', duration_minutes: 10, qr_type: 'static', refresh_seconds: 3 })
const qrVisible = ref(false), qrTask = ref(null), qrDataUrl = ref(''), countdown = ref(0), qrLoading = ref(false), qrError = ref('')
let countdownTimer = null, qrGeneration = 0, refreshPending = false
const recordsVisible = ref(false), recordsTask = ref(null), records = ref([]), recordsLoading = ref(false)
const recordSearch = ref(''), recordStatus = ref(''), updatingStudent = ref(null)
let recordsGeneration = 0
const canManageRecords = computed(() => recordsTask.value?.can_manage_records === true)
const filteredRecords = computed(() => records.value.filter(row => (!recordStatus.value || row.status === recordStatus.value) && `${row.name} ${row.student_no}`.toLowerCase().includes(recordSearch.value.trim().toLowerCase())))
function formatTime(value) { return value ? String(value).replace('T', ' ').slice(0, 19) : '' }
function isActive(row) {
  const value = String(row.expires_at || '')
  const expires = Date.parse(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : value + '+08:00')
  return row.status === 'active' && expires > Date.now()
}
function taskStatus(row) { return row.status !== 'active' ? '已关闭' : isActive(row) ? '进行中' : '已到期' }
function statusLabel(status) { return { auto: '已签到', manual: '已签到（补签）', leave: '请假', absent: '未签到' }[status] || status }
function statusTag(status) { return { auto: 'success', manual: 'success', leave: 'warning', absent: 'danger' }[status] || 'info' }
async function loadTasks() {
  if (loading.value) return
  loading.value = true
  try { tasks.value = (await api.get('/api/qr-checkin/tasks')).data }
  catch (error) { ElMessage.error(error.response?.data?.detail || '加载失败') }
  finally { loading.value = false }
}
async function createTask() {
  if (creating.value) return
  if (!form.name.trim()) return ElMessage.warning('请填写签到名称')
  if (!Number.isInteger(form.duration_minutes)) return ElMessage.warning('请填写有效时长')
  creating.value = true
  try {
    await api.post('/api/qr-checkin/tasks', { ...form, name: form.name.trim(), refresh_seconds: form.qr_type === 'dynamic' ? form.refresh_seconds : null })
    ElMessage.success('签到已创建'); form.name = ''; await loadTasks()
  } catch (error) { ElMessage.error(error.response?.data?.detail || '创建失败') }
  finally { creating.value = false }
}
function stopQrTimer() { clearInterval(countdownTimer); countdownTimer = null }
function closeQr() { stopQrTimer(); qrGeneration++; qrDataUrl.value = ''; refreshPending = false; qrLoading.value = false }
async function openQr(row) { closeQr(); qrTask.value = row; qrError.value = ''; qrVisible.value = true; await loadQr() }
async function loadQr() {
  if (!qrVisible.value || !qrTask.value || refreshPending) return
  stopQrTimer()
  const token = qrGeneration, task = qrTask.value
  if (!isActive(task)) { qrDataUrl.value = ''; qrError.value = '此签到已关闭或到期，请返回列表查看。'; return }
  refreshPending = true; qrLoading.value = true; qrError.value = ''; qrDataUrl.value = ''
  try {
    const res = task.qr_type === 'dynamic' ? await api.post(`/api/qr-checkin/tasks/${task.id}/refresh-code`) : await api.get(`/api/qr-checkin/tasks/${task.id}`)
    if (token !== qrGeneration || !qrVisible.value) return
    qrDataUrl.value = res.data.qr_data_url; qrTask.value = { ...task, ...res.data }; countdown.value = res.data.refresh_seconds || task.refresh_seconds || 3
    countdownTimer = setInterval(() => {
      if (!isActive(qrTask.value)) { stopQrTimer(); qrDataUrl.value = ''; qrError.value = '签到已到期。'; return }
      if (task.qr_type === 'dynamic' && --countdown.value <= 0) loadQr()
    }, 1000)
  } catch (error) { if (token === qrGeneration) qrError.value = error.response?.data?.detail || '二维码加载失败，请检查网络后重试。' }
  finally { if (token === qrGeneration) { refreshPending = false; qrLoading.value = false } }
}
async function openRecords(row) { recordsTask.value = row; records.value = []; recordSearch.value = ''; recordStatus.value = ''; recordsVisible.value = true; await loadRecords() }
async function loadRecords() {
  if (!recordsTask.value) return
  const taskId = recordsTask.value.id, token = ++recordsGeneration
  recordsLoading.value = true
  try { const res = await api.get(`/api/qr-checkin/tasks/${taskId}/records`); if (token === recordsGeneration) records.value = res.data.records }
  catch (error) { if (token === recordsGeneration) ElMessage.error(error.response?.data?.detail || '名单加载失败') }
  finally { if (token === recordsGeneration) recordsLoading.value = false }
}
async function updateRecord(row, status) {
  if (updatingStudent.value !== null) return
  const taskId = recordsTask.value.id
  updatingStudent.value = row.student_id
  try {
    await api.put(`/api/qr-checkin/tasks/${taskId}/manual`, { student_id: row.student_id, status })
    ElMessage.success('状态已更新'); if (recordsTask.value?.id === taskId) await loadRecords(); await loadTasks()
  } catch (error) { ElMessage.error(error.response?.data?.detail || '更新失败') }
  finally { updatingStudent.value = null }
}
async function exportTask(row) {
  try {
    const res = await api.get(`/api/qr-checkin/tasks/${row.id}/export`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data), link = document.createElement('a')
    link.href = url; link.download = `${row.name.replace(/[\\/:*?"<>|]/g, '_')}_签到名单.xlsx`
    document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch { ElMessage.error('导出失败') }
}
async function closeTask(row) {
  try { await ElMessageBox.confirm(`确定提前关闭「${row.name}」吗？`, '关闭签到', { type: 'warning' }) } catch { return }
  try { await api.post(`/api/qr-checkin/tasks/${row.id}/close`); ElMessage.success('签到已关闭'); await loadTasks() }
  catch (error) { ElMessage.error(error.response?.data?.detail || '关闭失败') }
}
async function deleteTask(row) {
  try { await ElMessageBox.confirm(`删除后签到记录无法恢复，确定删除「${row.name}」吗？`, '删除签到', { type: 'error' }) } catch { return }
  try { await api.delete(`/api/qr-checkin/tasks/${row.id}`); ElMessage.success('已删除'); await loadTasks() }
  catch (error) { ElMessage.error(error.response?.data?.detail || '删除失败') }
}
function handleMedia(event) { compact.value = event.matches }
function handleVisibility() { if (qrVisible.value) { if (document.hidden) closeQr(); else loadQr() } }
onMounted(() => { loadTasks(); media.addEventListener('change', handleMedia); document.addEventListener('visibilitychange', handleVisibility) })
onBeforeUnmount(() => { closeQr(); recordsGeneration++; media.removeEventListener('change', handleMedia); document.removeEventListener('visibilitychange', handleVisibility) })
</script>

<style scoped>
.qr-manage-page, .table-wrap { min-width: 0; width: 100%; }
.page-card { min-width: 0; background: var(--el-bg-color); border: 1px solid var(--el-border-color-lighter); border-radius: 16px; padding: 24px; }
.page-head, .card-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.page-head h2 { margin: 0 0 8px; font-size: 22px; }
.page-head p, .task-meta, .records-summary, .table-hint { color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.7; }
.page-head p { margin: 0; }
.page-head > .el-button { flex-shrink: 0; }
.overview { display: flex; flex-wrap: wrap; gap: 12px 24px; padding: 16px; margin: 20px 0; border-radius: 12px; background: var(--el-fill-color-light); color: var(--el-text-color-secondary); font-size: 13px; }
.overview b { color: var(--el-color-primary); font-size: 20px; margin-left: 8px; }
.create-form { display: grid; grid-template-columns: minmax(180px, 2fr) repeat(3, minmax(130px, 1fr)) auto; gap: 16px; align-items: end; margin-bottom: 20px; }
.create-form :deep(.el-form-item) { min-width: 0; margin: 0; }
.create-form :deep(.el-input-number), .create-form :deep(.el-select) { width: 100%; }
.row-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.row-actions :deep(.el-button + .el-button) { margin-left: 0; }
.table-wrap { overflow: hidden; }
.table-hint { margin: 0 0 8px; }
.task-cards, .record-cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.task-card, .record-card { min-width: 0; border: 1px solid var(--el-border-color-lighter); border-radius: 12px; padding: 16px; background: var(--el-bg-color); }
.card-heading h3 { min-width: 0; margin: 0; font-size: 16px; line-height: 1.6; overflow-wrap: anywhere; }
.card-heading .el-tag { flex-shrink: 0; }
.counts { display: grid; grid-template-columns: repeat(3, 1fr); padding: 12px 0; background: var(--el-fill-color-light); border-radius: 10px; }
.counts span { display: flex; flex-direction: column; gap: 4px; text-align: center; font-size: 12px; color: var(--el-text-color-secondary); }
.counts b { color: var(--el-text-color-primary); font-size: 22px; }
.qr-dialog { text-align: center; min-height: 140px; }
.qr-task-name { margin: 0 0 16px; overflow-wrap: anywhere; }
.qr-image { width: 240px; max-width: 100%; height: auto; image-rendering: pixelated; border: 8px solid #fff; border-radius: 8px; }
.qr-countdown { color: var(--el-color-primary); font-size: 14px; }
.retry-button { margin-top: 16px; }
.records-toolbar { display: flex; gap: 12px; flex-wrap: wrap; }
.records-toolbar > .el-input { flex: 1; min-width: 180px; }
.records-toolbar > .el-select { width: 150px; }
.record-cards { max-height: 58dvh; overflow-y: auto; overscroll-behavior: contain; }
.record-card p { color: var(--el-text-color-secondary); font-size: 13px; margin: 8px 0; overflow-wrap: anywhere; }
.device-id { font-size: 12px !important; }
.task-cards > .el-empty, .record-cards > .el-empty { grid-column: 1 / -1; }
@media (max-width: 1199px) { .create-form { grid-template-columns: repeat(2, minmax(0, 1fr)); } .create-action .el-button { width: 100%; } }
@media (max-width: 600px) {
  .page-card { padding: 16px; }
  .page-head h2 { font-size: 20px; }
  .page-head p { font-size: 12px; }
  .task-cards, .record-cards { grid-template-columns: minmax(0, 1fr); }
  .create-form { gap: 12px; }
  .name-field, .create-action { grid-column: 1 / -1; }
  .row-actions .el-button { min-height: 36px; }
  .records-toolbar { gap: 8px; }
  .records-toolbar > .el-input { flex-basis: 100%; }
  .records-toolbar > .el-select { flex: 1; min-width: 0; }
  .records-summary { font-size: 12px; }
}
</style>
