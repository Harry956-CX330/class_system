<template>
  <div class="meeting-manage-container">
    <div class="page-header">
      <div class="header-left">
        <div class="title-indicator"></div>
        <h3 class="page-title">班会管理</h3>
      </div>
    </div>

    <el-row :gutter="20" class="stat-row">
      <el-col :xs="24" :sm="8" class="mb-col">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ meetings.length }}</div>
          <div class="stat-label">班会总数</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8" class="mb-col">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" style="color: #67C23A">{{ upcomingCount }}</div>
          <div class="stat-label">即将举行</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8" class="mb-col">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" style="color: #409EFF">{{ completedCount }}</div>
          <div class="stat-label">已举行</div>
        </el-card>
      </el-col>
    </el-row>

    <div v-if="authStore.canViewAllData" class="action-bar">
      <div class="batch-actions">
        <el-date-picker
          v-model="batchDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          class="responsive-datepicker"
        />
        <el-button type="danger" @click="handleBatchDelete" :disabled="!batchDateRange" class="action-btn">
          批量删除
        </el-button>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreateDialog" class="publish-btn">
        发布班会
      </el-button>
    </div>

    <el-card shadow="never" class="modern-card">
      <el-table 
        v-if="!isMobile"
        :data="meetings" 
        border 
        stripe 
        v-loading="loading"
        :header-cell-style="{ background: '#F7F8FA', color: '#4E5969', fontWeight: '500' }"
      >
        <el-table-column prop="title" label="班会标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-weight: 500; color: var(--el-text-color-primary)">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="meeting_date" label="班会时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.meeting_date) }}
          </template>
        </el-table-column>
        <el-table-column prop="location" label="地点" width="150" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'upcoming'" type="info" effect="plain" round>即将举行</el-tag>
            <el-tag v-else-if="row.status === 'completed'" type="success" effect="plain" round>已举行</el-tag>
            <el-tag v-else round>{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="authStore.canViewAllData" prop="author_name" label="发布人" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            <span style="color: var(--el-text-color-secondary); font-size: 13px">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        
        <el-table-column v-if="authStore.canViewAllData" label="操作" width="340" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link :icon="EditPen" @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" type="warning" link :icon="Document" @click="openRecordDialog(row)">纪要</el-button>
            <el-button size="small" type="info" link @click="qqNotifyMeeting(row)">QQ群通知</el-button>
            <el-button size="small" type="success" link @click="qqRemindLeaders(row)">提醒班干</el-button>
            <el-button size="small" type="danger" link :icon="Delete" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
        <el-table-column v-else label="操作" width="120" fixed="right" align="center">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openDetailDialog(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-meeting-list" v-loading="loading">
        <el-card v-for="row in meetings" :key="row.id" class="mobile-card" shadow="sm">
          <div class="m-card-header">
            <span class="m-title">{{ row.title }}</span>
            <el-tag v-if="row.status === 'upcoming'" type="info" size="small" round>即将举行</el-tag>
            <el-tag v-else-if="row.status === 'completed'" type="success" size="small" round>已举行</el-tag>
            <el-tag v-else size="small" round>{{ row.status }}</el-tag>
          </div>
          
          <div class="m-card-body">
            <div class="m-info-row">
              <el-icon><Calendar /></el-icon>
              <span>{{ formatTime(row.meeting_date) }}</span>
            </div>
            <div class="m-info-row">
              <el-icon><Location /></el-icon>
              <span>{{ row.location || '待定' }}</span>
            </div>
            <div v-if="authStore.canViewAllData" class="m-info-row">
              <el-icon><User /></el-icon>
              <span>发布人: {{ row.author_name }}</span>
            </div>
          </div>
          
          <div class="m-card-footer">
            <template v-if="authStore.canViewAllData">
              <el-button size="small" type="primary" plain @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" type="warning" plain @click="openRecordDialog(row)">纪要</el-button>
              <el-button size="small" type="info" plain @click="qqNotifyMeeting(row)">QQ群通知</el-button>
              <el-button size="small" type="success" plain @click="qqRemindLeaders(row)">提醒班干</el-button>
              <el-button size="small" type="danger" plain @click="handleDelete(row)">删除</el-button>
            </template>
            <template v-else>
              <el-button size="small" type="primary" style="width: 100%" @click="openDetailDialog(row)">查看详情</el-button>
            </template>
          </div>
        </el-card>
        <el-empty v-if="meetings.length === 0" description="暂无班会记录" />
      </div>
    </el-card>

    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑班会' : '发布班会'" 
      width="95%" 
      style="max-width: 600px"
      destroy-on-close
    >
      <el-form :model="meetingForm" label-width="80px" label-position="left">
        <el-form-item label="班会标题">
          <el-input v-model="meetingForm.title" placeholder="请输入班会标题" />
        </el-form-item>
        <el-form-item label="班会时间">
          <el-date-picker
            v-model="meetingForm.meeting_date"
            type="datetime"
            placeholder="选择班会时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="地点">
          <el-input v-model="meetingForm.location" placeholder="请输入班会地点" />
        </el-form-item>
        <el-form-item label="描述">
          <RichEditor v-model="meetingForm.description" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="meetingForm.status" style="width: 100%">
            <el-option label="即将举行" value="upcoming" />
            <el-option label="已举行" value="completed" />
          </el-select>
        </el-form-item>
        <el-form-item label="考勤班干">
          <el-select v-model="meetingForm.attendance_leader_id" clearable filterable placeholder="选择考勤班干" style="width: 100%">
            <el-option v-for="l in classLeaders" :key="l.id" :label="`${l.real_name} (${l.class_position || '班委'})`" :value="l.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="主持/记录">
          <el-select v-model="meetingForm.host_leader_id" clearable filterable placeholder="选择主持+记录班干" style="width: 100%">
            <el-option v-for="l in classLeaders" :key="l.id" :label="`${l.real_name} (${l.class_position || '班委'})`" :value="l.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSubmit">
            {{ isEdit ? '保存' : '发布' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="recordVisible" title="班会纪要" width="95%" style="max-width: 700px" destroy-on-close>
      <div class="upload-section">
        <p class="gallery-title">班会记录文件（支持 pdf / word）：</p>
        <div v-if="recordForm.record_file_name" class="record-file-info">
          <el-icon><Document /></el-icon>
          <a :href="imgUrl(recordForm.record_file)" target="_blank" class="record-file-link">{{ recordForm.record_file_name }}</a>
        </div>
        <el-upload
          :auto-upload="false"
          :limit="1"
          accept=".pdf,.doc,.docx"
          :on-change="handleRecordFileChange"
          :file-list="recordFileList"
        >
          <el-button type="primary" plain>选择文件</el-button>
        </el-upload>
        <el-button type="success" :loading="uploadingFile" @click="handleUploadFile" style="margin-top: 8px">上传记录文件</el-button>
      </div>

      <div class="upload-section">
        <p class="gallery-title">发送班会记录邮件（标题为班会标题，附件为记录文件）：</p>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <el-input v-model="emailTo" placeholder="请输入接收邮箱" clearable style="flex: 1; min-width: 200px;" />
          <el-button type="primary" :loading="sendingEmail" @click="sendRecordEmail">发送邮件</el-button>
        </div>
      </div>

      <template #footer>
        <el-button @click="recordVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="班会详情" width="95%" style="max-width: 700px" destroy-on-close>
      <template v-if="detailMeeting">
        <el-descriptions :column="isMobile ? 1 : 2" border class="detail-descriptions">
          <el-descriptions-item label="班会标题" :span="isMobile ? 1 : 2">{{ detailMeeting.title }}</el-descriptions-item>
          <el-descriptions-item label="班会时间">{{ formatTime(detailMeeting.meeting_date) }}</el-descriptions-item>
          <el-descriptions-item label="地点">{{ detailMeeting.location || '—' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag v-if="detailMeeting.status === 'upcoming'" type="info" size="small">即将举行</el-tag>
            <el-tag v-else-if="detailMeeting.status === 'completed'" type="success" size="small">已举行</el-tag>
            <span v-else>{{ detailMeeting.status }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="发布人">{{ detailMeeting.author_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="isMobile ? 1 : 2">
            <RichContent :content="detailMeeting.description || '—'" />
          </el-descriptions-item>
        </el-descriptions>
        
        <div v-if="detailMeeting.record_file_name" class="detail-record-section">
          <h4 class="section-title">班会记录文件</h4>
          <a :href="imgUrl(detailMeeting.record_file)" target="_blank" class="record-file-link">{{ detailMeeting.record_file_name }}</a>
        </div>
      </template>
      <template #footer>
        <el-button @click="detailVisible = false" style="width: 100%; max-width: 120px">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, EditPen, Delete, Document, Calendar, Location, User } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const authStore = useAuthStore()

// 响应式状态管理
const isMobile = ref(false)
const checkDevice = () => {
  isMobile.value = window.innerWidth <= 768
}

const meetings = ref([])
const loading = ref(false)

const upcomingCount = computed(() => meetings.value.filter(m => m.status === 'upcoming').length)
const completedCount = computed(() => meetings.value.filter(m => m.status === 'completed').length)

const batchDateRange = ref(null)

const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const saving = ref(false)

const meetingForm = reactive({
  title: '',
  meeting_date: '',
  location: '',
  description: '',
  status: 'upcoming',
  attendance_leader_id: null,
  host_leader_id: null,
})

const recordVisible = ref(false)
const recordMeetingId = ref(null)

const recordForm = reactive({
  record_file: '',
  record_file_name: '',
})

const classLeaders = ref([])
const pendingFile = ref(null)
const recordFileList = ref([])
const uploadingFile = ref(false)
const emailTo = ref('')
const sendingEmail = ref(false)

const detailVisible = ref(false)
const detailMeeting = ref(null)

function imgUrl(name) {
  return '/static/' + name
}

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}

async function loadMeetings() {
  loading.value = true
  try {
    const res = await api.get('/api/class-meetings')
    meetings.value = res.data
  } catch {
    ElMessage.error('加载班会列表失败')
  } finally {
    loading.value = false
  }
}

async function handleBatchDelete() {
  if (!batchDateRange.value) return
  try {
    await ElMessageBox.confirm(
      `确定要删除 ${batchDateRange.value[0]} 至 ${batchDateRange.value[1]} 之间的所有班会吗？此操作不可恢复！`,
      '批量删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await api.post('/api/class-meetings/batch-delete', {
      from_date: batchDateRange.value[0],
      to_date: batchDateRange.value[1],
    })
    ElMessage.success('批量删除成功')
    batchDateRange.value = null
    loadMeetings()
  } catch (err) {
    if (err !== 'cancel' && err !== 'close') {
      ElMessage.error(err.response?.data?.detail || '批量删除失败')
    }
  }
}

function openCreateDialog() {
  isEdit.value = false
  editId.value = null
  meetingForm.title = ''
  meetingForm.meeting_date = ''
  meetingForm.location = ''
  meetingForm.description = ''
  meetingForm.status = 'upcoming'
  meetingForm.attendance_leader_id = null
  meetingForm.host_leader_id = null
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  editId.value = row.id
  meetingForm.title = row.title
  meetingForm.meeting_date = row.meeting_date
  meetingForm.location = row.location || ''
  meetingForm.description = row.description || ''
  meetingForm.status = row.status
  meetingForm.attendance_leader_id = row.attendance_leader_id || null
  meetingForm.host_leader_id = row.host_leader_id || null
  dialogVisible.value = true
}

async function handleSubmit() {
  saving.value = true
  try {
    const payload = {
      title: meetingForm.title,
      meeting_date: meetingForm.meeting_date,
      location: meetingForm.location,
      description: meetingForm.description,
      status: meetingForm.status,
      attendance_leader_id: meetingForm.attendance_leader_id,
      host_leader_id: meetingForm.host_leader_id,
    }
    if (isEdit.value) {
      await api.put(`/api/class-meetings/${editId.value}`, payload)
      ElMessage.success('编辑成功')
    } else {
      await api.post('/api/class-meetings', payload)
      ElMessage.success('发布成功')
    }
    dialogVisible.value = false
    loadMeetings()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || (isEdit.value ? '编辑失败' : '发布失败'))
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除该班会吗？', '提示', { type: 'warning' })
    await api.delete(`/api/class-meetings/${row.id}`)
    ElMessage.success('删除成功')
    loadMeetings()
  } catch {}
}

function openRecordDialog(row) {
  recordMeetingId.value = row.id
  recordForm.record_file = row.record_file || ''
  recordForm.record_file_name = row.record_file_name || ''
  pendingFile.value = null
  recordFileList.value = []
  emailTo.value = ''
  recordVisible.value = true
}

function handleRecordFileChange(file) {
  pendingFile.value = file.raw
  recordFileList.value = [file]
}

async function handleUploadFile() {
  if (!pendingFile.value) {
    ElMessage.warning('请先选择要上传的文件')
    return
  }
  uploadingFile.value = true
  try {
    const formData = new FormData()
    formData.append('file', pendingFile.value)
    const res = await api.post(
      `/api/class-meetings/${recordMeetingId.value}/upload-file`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    recordForm.record_file = res.data.record_file
    recordForm.record_file_name = res.data.record_file_name
    pendingFile.value = null
    recordFileList.value = []
    ElMessage.success('记录文件上传成功')
    loadMeetings()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '文件上传失败')
  } finally {
    uploadingFile.value = false
  }
}

async function sendRecordEmail() {
  if (!emailTo.value.trim()) {
    ElMessage.warning('请输入接收邮箱')
    return
  }
  sendingEmail.value = true
  try {
    const res = await api.post(`/api/class-meetings/${recordMeetingId.value}/send-email`, {
      email: emailTo.value.trim(),
    })
    ElMessage.success(res.data.message || '邮件已发送')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '邮件发送失败')
  } finally {
    sendingEmail.value = false
  }
}

async function qqNotifyMeeting(row) {
  try {
    await ElMessageBox.confirm(`确定向QQ群发送班会「${row.title}」的通知吗？`, '提示', { type: 'warning' })
  } catch { return }
  try {
    const res = await api.post(`/api/qq/class-meeting/${row.id}/notify`)
    ElMessage.success(res.data.message || 'QQ群通知已发送')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  }
}

async function qqRemindLeaders(row) {
  try {
    await ElMessageBox.confirm('确定向考勤班干和主持/记录班干发送QQ私信提醒吗？', '提示', { type: 'warning' })
  } catch { return }
  try {
    const res = await api.post(`/api/qq/class-meeting/${row.id}/remind-leaders`)
    ElMessage.success(res.data.message || '提醒完成')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  }
}

async function loadClassLeaders() {
  try {
    classLeaders.value = (await api.get('/api/class-committee/all')).data
  } catch {}
}

function openDetailDialog(row) {
  detailMeeting.value = row
  detailVisible.value = true
}

onMounted(() => {
  checkDevice()
  window.addEventListener('resize', checkDevice)
  loadMeetings()
  if (authStore.canViewAllData) loadClassLeaders()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkDevice)
})
</script>

<style scoped>
/* 容器基底 */
.meeting-manage-container {
  padding: 0;
}

/* 顶部标题栏 */
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

/* 统计卡片 */
.stat-row {
  margin-bottom: 20px;
}

.stat-card {
  border-radius: 8px;
  border: none;
}

.stat-value { 
  font-size: 32px; 
  font-weight: 700; 
  text-align: center;
  font-family: 'DIN Alternate', -apple-system, BlinkMacSystemFont, sans-serif;
  color: var(--el-text-color-primary);
}

.stat-label { 
  text-align: center; 
  color: var(--el-text-color-secondary);
  margin-top: 8px; 
  font-size: 14px;
}

/* 操作栏 */
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
  flex-wrap: wrap;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.modern-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.04);
}

/* 图片区域 */
.image-gallery {
  margin-bottom: 16px;
}
.gallery-title {
  margin: 0 0 8px; 
  color: var(--el-text-color-regular);
  font-size: 14px;
}
.gallery-container {
  display: flex; 
  flex-wrap: wrap; 
  gap: 10px;
}
.gallery-img {
  width: 80px; 
  height: 80px; 
  border-radius: 4px;
  border: 1px solid #E5E6EB;
}
.gallery-img-large {
  width: 120px; 
  height: 120px; 
  border-radius: 6px;
  border: 1px solid #E5E6EB;
}
.upload-section {
  margin-bottom: 16px;
}

/* 班会记录文件展示 */
.record-file-info {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--surface-soft);
  border-radius: 6px;
  margin-bottom: 8px;
  color: var(--el-text-color-regular);
}
.record-file-link {
  color: var(--el-color-primary);
  text-decoration: none;
  word-break: break-all;
}
.record-file-link:hover {
  text-decoration: underline;
}

/* 详情弹窗文字 */
.pre-wrap-text {
  white-space: pre-wrap; 
  line-height: 1.6;
  color: var(--el-text-color-regular);
}
.detail-record-section {
  margin-top: 24px;
}
.section-title {
  margin-top: 0;
  margin-bottom: 12px;
  font-size: 15px;
  color: var(--el-text-color-primary);
}
.record-text-box {
  white-space: pre-wrap; 
  line-height: 1.6; 
  padding: 16px; 
  background: var(--surface-soft);
  border-radius: 6px;
  color: var(--el-text-color-regular);
}
.detail-image-section {
  margin-top: 24px;
}

/* 移动端卡片视图 */
.mobile-meeting-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.mobile-card {
  border-radius: 8px;
  border: 1px solid #E5E6EB;
}
.m-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  border-bottom: 1px dashed #E5E6EB;
  padding-bottom: 12px;
}
.m-title {
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 15px;
  line-height: 1.4;
  padding-right: 8px;
}
.m-card-body {
  margin-bottom: 16px;
  background-color: var(--surface-soft);
  padding: 12px;
  border-radius: 6px;
}
.m-info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.m-info-row:last-child {
  margin-bottom: 0;
}
.m-card-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  border-top: 1px solid #F2F3F5;
  padding-top: 12px;
}

/* 弹窗底部操作区 */
.responsive-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

/* =======================================
   移动端响应式适配 (Media Queries)
   ======================================= */
@media screen and (max-width: 768px) {
  .mb-col {
    margin-bottom: 16px;
  }
  
  /* 操作栏垂直堆叠 */
  .action-bar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .batch-actions {
    flex-direction: column;
    align-items: stretch;
  }
  
  .responsive-datepicker {
    width: 100% !important;
  }

  .action-btn, .publish-btn {
    width: 100%;
    margin-left: 0 !important;
  }

  /* 调整弹窗表单间距 */
  :deep(.modern-dialog .el-form-item) {
    flex-direction: column;
    margin-bottom: 16px;
  }
  :deep(.modern-dialog .el-form-item__label) {
    justify-content: flex-start;
    padding-bottom: 4px;
    line-height: 1.2;
  }
  
  /* 图片画廊弹性适配 */
  .gallery-img-large {
    width: 80px;
    height: 80px;
  }
  
  /* 弹窗底部按钮全宽铺满 */
  .responsive-footer .el-button {
    flex: 1;
    min-width: 30%;
    margin-left: 0 !important;
  }
}
</style>