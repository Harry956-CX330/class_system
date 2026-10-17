<template>
  <div class="activity-container">
    <div class="page-header">
      <div class="header-left">
        <h3 style="margin: 0">活动管理</h3>
      </div>
      <el-button v-if="authStore.canViewAllData" type="primary" class="header-btn" @click="openCreateDialog">
        发布活动
      </el-button>
    </div>

    <el-table v-if="!isMobile" :data="activities" border stripe v-loading="loading" class="desktop-table">
      <el-table-column prop="title" label="活动标题" min-width="160" />
      <el-table-column label="活动时间" width="290">
        <template #default="{ row }">
          {{ formatTime(row.start_time) }} ~ {{ formatTime(row.end_time) }}
        </template>
      </el-table-column>
      <el-table-column prop="location" label="地点" min-width="120" />
      <el-table-column prop="author_name" label="发布人" width="100" />
      <el-table-column label="参与/签到" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ row.signed_count }}/{{ row.participant_count }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="340" fixed="right">
        <template #default="{ row }">
          <el-button v-if="authStore.canViewAllData" size="small" @click="openCheckinDialog(row)">发起签到</el-button>
          <el-button size="small" :disabled="isSigned(row)" @click="openSignDialog(row)">
            {{ isSigned(row) ? '已签到' : '签到' }}
          </el-button>
          <el-button v-if="authStore.canViewAllData" size="small" type="primary" @click="openParticipantDialog(row)">名单</el-button>
          <template v-if="authStore.canViewAllData">
            <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <div v-else class="mobile-list" v-loading="loading">
      <el-card v-for="row in activities" :key="row.id" class="mobile-card" shadow="sm">
        <div class="card-header">
          <span class="card-title">{{ row.title }}</span>
          <el-tag size="small" type="info">{{ row.signed_count }}/{{ row.participant_count }} 签到</el-tag>
        </div>
        <div class="card-body">
          <p><strong>时间：</strong>{{ formatTime(row.start_time) }} ~ {{ formatTime(row.end_time) }}</p>
          <p><strong>地点：</strong>{{ row.location }}</p>
          <p><strong>发布人：</strong>{{ row.author_name }}</p>
        </div>
        <div class="card-footer">
          <div class="primary-actions">
            <el-button v-if="authStore.canViewAllData" size="small" @click="openCheckinDialog(row)">发起签到</el-button>
            <el-button size="small" :disabled="isSigned(row)" @click="openSignDialog(row)">
              {{ isSigned(row) ? '已签到' : '签到' }}
            </el-button>
            <el-button v-if="authStore.canViewAllData" size="small" type="primary" @click="openParticipantDialog(row)">名单</el-button>
          </div>
          <div v-if="authStore.canViewAllData" class="admin-actions">
            <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </div>
        </div>
      </el-card>
      <el-empty v-if="activities.length === 0" description="暂无活动" />
    </div>

    <el-dialog v-model="formVisible" :title="isEdit ? '编辑活动' : '发布活动'" :width="isMobile ? '95%' : '500px'" class="modern-dialog">
      <el-form :model="form" label-width="80px" label-position="left">
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="地点"><el-input v-model="form.location" /></el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker v-model="form.start_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker v-model="form.end_time" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="formVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">{{ isEdit ? '保存' : '发布' }}</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="checkinVisible" title="签到码" :width="isMobile ? '95%' : '450px'" class="modern-dialog" @close="stopCheckinTimer">
      <div style="text-align: center">
        <p style="color:#666;margin-bottom:12px;font-weight:bold">{{ checkinActivity?.title }}</p>
        <div class="checkin-code">{{ checkinCode }}</div>
        <p style="color:#409EFF;margin-top:8px;font-size:14px;font-weight:bold;">当前签到码（四位数字）</p>
        <p style="color:#999;margin-top:4px;font-size:12px">
          <template v-if="checkinMode === 'fixed'">固定数字模式（不会自动刷新）</template>
          <template v-else>{{ checkinInterval }}秒刷新模式（每{{ checkinInterval }}秒自动更新，防止截图代签）</template>
        </p>
        <div style="margin-top: 10px; display: flex; gap: 8px; align-items: center; justify-content: center; flex-wrap: wrap;">
          <span style="color:#606266;font-size:13px;">刷新间隔：</span>
          <el-input-number v-model="checkinInterval" :min="1" :max="3600" size="small" :disabled="checkinMode === 'fixed'" @change="saveCheckinInterval" />
          <span style="color:#606266;font-size:13px;">秒</span>
        </div>
        <div style="margin-top: 10px; display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
          <el-button size="small" type="primary" @click="refreshCheckinCode">手动刷新</el-button>
          <el-button size="small" :type="checkinMode === 'fixed' ? 'warning' : 'default'" @click="toggleCheckinMode">
            {{ checkinMode === 'fixed' ? '切换为自动刷新' : '切换为固定数字' }}
          </el-button>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="signVisible" title="签到" :width="isMobile ? '95%' : '450px'" class="modern-dialog" @close="closeSignDialog">
      <div style="text-align:center">
        <p style="color:#666;margin-bottom:16px;font-weight:bold">{{ viewActivity?.title }}</p>
        <p style="color:#666;margin-bottom:8px;font-size:14px;">请输入老师展示的四位数字签到码</p>
        <div style="display: flex; justify-content: center;">
          <el-input v-model="inputCode" placeholder="四位数字" :maxlength="4" clearable
            style="max-width: 220px; text-align: center;" @keyup.enter="doSignIn">
            <template #append>
              <el-button :loading="signing" :disabled="inputCode.trim().length !== 4" @click="doSignIn">签到</el-button>
            </template>
          </el-input>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="participantVisible" :title="`活动名单: ${viewActivity?.title || ''}`" :fullscreen="isMobile" :width="isMobile ? '100%' : '900px'" class="modern-dialog">
      <div v-if="authStore.canViewAllData" class="action-bar">
        <el-button type="primary" plain @click="importAllStudents">导入全部</el-button>
        <el-button type="success" plain @click="exportParticipants">导出名单</el-button>
        <el-button type="warning" plain :disabled="!hasAbsentStudents" @click="batchSetLeave">全员请假</el-button>
        <el-button type="primary" plain @click="qqNotifyActivity">QQ群通知</el-button>
        <el-button type="danger" plain @click="qqRemindUnsigned">提醒未签到</el-button>
        <div class="manual-add-wrapper">
          <el-select v-model="selectedStudentId" filterable placeholder="手动添加学生" class="responsive-select" clearable>
            <el-option v-for="s in allStudents" :key="s.id" :label="`${s.real_name} (${s.student_id})`" :value="s.id" />
          </el-select>
          <el-button type="primary" :disabled="!selectedStudentId" @click="addOneStudent">添加</el-button>
        </div>
      </div>
      
      <el-table v-if="!isMobile" :data="participants" border stripe v-loading="partLoading" style="width: 100%">
        <el-table-column prop="student_student_id" label="学号" min-width="120" />
        <el-table-column prop="student_name" label="姓名" min-width="100" />
        <el-table-column label="签到状态" min-width="170">
          <template #default="{ row }">
            <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
              <el-select v-if="authStore.canViewAllData" v-model="row.sign_status" size="small" @change="updateSignStatus(row)" style="width:90px">
                <el-option label="已签到" value="present" />
                <el-option label="迟到" value="late" />
                <el-option label="请假" value="leave" />
                <el-option label="缺勤" value="absent" />
              </el-select>
              <el-tag v-else :type="tagType(row.sign_status)" size="small">{{ statusLabel(row.sign_status) }}</el-tag>
              <el-button v-if="authStore.canViewAllData && row.sign_status !== 'leave'" type="warning" size="small" plain @click="setStudentLeave(row)">请假</el-button>
              <el-button v-if="authStore.canViewAllData && row.sign_status === 'absent'" size="small" type="danger" plain :disabled="!row.student_qq" @click="qqRemindOne(row)">提醒</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-part-list" v-loading="partLoading">
        <div v-for="row in participants" :key="row.student_student_id" class="mobile-part-card">
          <div class="part-info">
            <span class="part-name">{{ row.student_name }}</span>
            <span class="part-id">{{ row.student_student_id }}</span>
          </div>
          <div class="part-actions">
            <template v-if="authStore.canViewAllData">
              <el-select v-model="row.sign_status" size="small" @change="updateSignStatus(row)" class="part-select">
                <el-option label="已签到" value="present" />
                <el-option label="迟到" value="late" />
                <el-option label="请假" value="leave" />
                <el-option label="缺勤" value="absent" />
              </el-select>
              <el-button v-if="row.sign_status !== 'leave'" type="warning" size="small" plain @click="setStudentLeave(row)">请假</el-button>
              <el-button v-if="row.sign_status === 'absent'" size="small" type="danger" plain :disabled="!row.student_qq" @click="qqRemindOne(row)">提醒</el-button>
            </template>
            <template v-else>
              <el-tag :type="tagType(row.sign_status)">{{ statusLabel(row.sign_status) }}</el-tag>
            </template>
          </div>
        </div>
        <el-empty v-if="participants.length === 0" description="暂无人员名单" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const authStore = useAuthStore()

// 响应式状态管理核心
const isMobile = ref(false)
const checkDevice = () => {
  isMobile.value = window.innerWidth <= 768
}

// ---------------- 变量声明 ----------------
const activities = ref([])
const loading = ref(false)
const formVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)

const form = reactive({ title: '', description: '', location: '', start_time: '', end_time: '' })

const checkinVisible = ref(false)
const checkinActivity = ref(null)
const checkinMode = ref('auto')
const checkinCode = ref('0000')
const checkinInterval = ref(2)
let checkinTimer = null

const signVisible = ref(false)
const inputCode = ref('')
const signing = ref(false)

const participantVisible = ref(false)
const viewActivity = ref(null)
const participants = ref([])
const partLoading = ref(false)
const allStudents = ref([])
const selectedStudentId = ref(null)

// ---------------- 工具函数 ----------------
function formatTime(t) { return t ? new Date(t).toLocaleString('zh-CN', { hour12: false }) : '' }
function statusLabel(s) { return { present:'已签到', late:'迟到', leave:'请假', absent:'缺勤' }[s] || '缺勤' }
function tagType(s) { return { present:'success', late:'warning', leave:'info', absent:'danger' }[s] || 'danger' }
function isSigned(row) { return row.my_sign_status === 'present' || row.my_sign_status === 'late' }

// ---------------- 业务逻辑 ----------------
async function loadActivities() {
  loading.value = true
  try { activities.value = (await api.get('/api/activities')).data } catch {} finally { loading.value = false }
}

function openCreateDialog() {
  isEdit.value = false; editId.value = null
  form.title = ''; form.description = ''; form.location = ''; form.start_time = ''; form.end_time = ''
  formVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true; editId.value = row.id
  form.title = row.title; form.description = row.description; form.location = row.location
  form.start_time = row.start_time ? new Date(row.start_time).toISOString().slice(0,19) : ''
  form.end_time = row.end_time ? new Date(row.end_time).toISOString().slice(0,19) : ''
  formVisible.value = true
}

async function handleSubmit() {
  try {
    if (isEdit.value) {
      await api.put(`/api/activities/${editId.value}`, form)
      ElMessage.success('修改成功')
    } else {
      await api.post('/api/activities', form)
      ElMessage.success('发布成功')
    }
    formVisible.value = false
    loadActivities()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定删除该活动吗？', '提示', { type: 'warning' })
    await api.delete(`/api/activities/${row.id}`)
    ElMessage.success('删除成功')
    loadActivities()
  } catch {}
}

async function openParticipantDialog(row) {
  viewActivity.value = row
  participantVisible.value = true
  partLoading.value = true
  try {
    participants.value = (await api.get(`/api/activities/${row.id}/participants`)).data
  } catch {} finally { partLoading.value = false }
  
  if (authStore.canViewAllData) {
    try { allStudents.value = (await api.get('/api/users', { params: { role: 'student' } })).data } catch {}
  }
}

async function importAllStudents() {
  try {
    await ElMessageBox.confirm('确定导入全部学生吗？', '提示', { type: 'warning' })
    const res = await api.post(`/api/activities/${viewActivity.value.id}/import-all-students`)
    ElMessage.success(`导入完成: ${res.data.created} 人`)
    openParticipantDialog(viewActivity.value)
  } catch {}
}

async function addOneStudent() {
  try {
    await api.post(`/api/activities/${viewActivity.value.id}/import-participants`, [selectedStudentId.value])
    ElMessage.success('添加成功')
    selectedStudentId.value = null
    openParticipantDialog(viewActivity.value)
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '添加失败')
  }
}

async function exportParticipants() {
  try {
    const res = await api.get(`/api/activities/${viewActivity.value.id}/export`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = decodeURIComponent(res.headers['content-disposition']?.match(/filename\*=UTF-8''(.+)/)?.[1] || '活动参与情况.xlsx')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch {}
}

async function updateSignStatus(row) {
  try {
    await api.put(`/api/activities/${viewActivity.value.id}/sign-in`, {
      student_id: row.student_id,
      sign_status: row.sign_status,
    })
    ElMessage.success('状态已更新')
  } catch {}
}

async function setStudentLeave(row) {
  row.sign_status = 'leave'
  await updateSignStatus(row)
}

const hasAbsentStudents = computed(() => participants.value.some(p => p.sign_status === 'absent'))

async function batchSetLeave() {
  try {
    await ElMessageBox.confirm('确定将所有缺席学生标记为请假吗？', '批量请假', { type: 'warning' })
    const absentList = participants.value.filter(p => p.sign_status === 'absent')
    for (const row of absentList) {
      try {
        await api.put(`/api/activities/${viewActivity.value.id}/sign-in`, {
          student_id: row.student_id,
          sign_status: 'leave',
        })
        row.sign_status = 'leave'
      } catch {}
    }
    ElMessage.success(`已将 ${absentList.length} 名学生设为请假`)
  } catch {}
}

// ---------------- 签到码逻辑 ----------------
async function refreshCheckinCode() {
  if (!checkinActivity.value) return
  try {
    const res = await api.post(`/api/activities/${checkinActivity.value.id}/refresh-checkin-code`)
    checkinCode.value = res.data.checkin_code
    checkinActivity.value.checkin_code = res.data.checkin_code
  } catch {}
}

function openCheckinDialog(row) {
  checkinActivity.value = row
  checkinVisible.value = true
  checkinMode.value = row.checkin_mode === 'fixed' ? 'fixed' : 'auto'
  checkinCode.value = row.checkin_code || '0000'
  checkinInterval.value = row.checkin_interval || 2
  nextTick(() => startCheckinTimer())
}

async function saveCheckinInterval() {
  if (!checkinActivity.value) return
  try {
    const res = await api.put(`/api/activities/${checkinActivity.value.id}/checkin-mode`, {
      mode: checkinMode.value,
      interval: checkinInterval.value,
    })
    checkinInterval.value = res.data.checkin_interval
    checkinActivity.value.checkin_interval = res.data.checkin_interval
    if (checkinMode.value === 'auto') startCheckinTimer()
  } catch {}
}

async function toggleCheckinMode() {
  if (!checkinActivity.value) return
  const nextMode = checkinMode.value === 'fixed' ? 'auto' : 'fixed'
  try {
    const res = await api.put(`/api/activities/${checkinActivity.value.id}/checkin-mode`, {
      mode: nextMode,
      interval: checkinInterval.value,
    })
    checkinMode.value = res.data.checkin_mode
    checkinCode.value = res.data.checkin_code
    checkinInterval.value = res.data.checkin_interval
    checkinActivity.value.checkin_mode = res.data.checkin_mode
    checkinActivity.value.checkin_code = res.data.checkin_code
    checkinActivity.value.checkin_interval = res.data.checkin_interval
  } catch { return }
  if (checkinMode.value === 'auto') startCheckinTimer()
  else stopCheckinTimer()
}

function startCheckinTimer() {
  stopCheckinTimer()
  if (checkinMode.value === 'fixed') return
  const intervalMs = Math.max(1, checkinInterval.value || 2) * 1000
  checkinTimer = setInterval(async () => {
    if (!checkinVisible.value || !checkinActivity.value) { stopCheckinTimer(); return }
    try {
      const res = await api.post(`/api/activities/${checkinActivity.value.id}/refresh-checkin-code`)
      checkinCode.value = res.data.checkin_code
      checkinActivity.value.checkin_code = res.data.checkin_code
    } catch {}
  }, intervalMs)
}

function stopCheckinTimer() { if (checkinTimer) { clearInterval(checkinTimer); checkinTimer = null } }

// ---------------- 学生签到逻辑 ----------------
function openSignDialog(row) {
  viewActivity.value = row
  signVisible.value = true
  inputCode.value = ''
  signing.value = false
}

function closeSignDialog() {
  inputCode.value = ''
}

async function doSignIn() {
  const code = inputCode.value.trim()
  if (code.length !== 4 || !/^\d{4}$/.test(code)) {
    ElMessage.warning('请输入四位数字签到码')
    return
  }
  signing.value = true
  try {
    const res = await api.post('/api/activities/verify-checkin', {
      code,
      activity_id: viewActivity.value.id
    })
    viewActivity.value.my_sign_status = 'present'
    signVisible.value = false
    inputCode.value = ''
    if (res.data.status === 'already') {
      ElMessage.warning('你已签到过，请勿重复签到')
    } else {
      ElMessageBox.alert('签到成功！', '已成功签到', { type: 'success', confirmButtonText: '知道了' }).catch(() => {})
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '签到失败')
  } finally {
    signing.value = false
  }
}

// ---------------- QQ 提醒逻辑 ----------------
async function qqNotifyActivity() {
  try {
    await ElMessageBox.confirm('确定向QQ群发送签到通知吗？', '提示', { type: 'warning' })
  } catch { return }
  try {
    const res = await api.post(`/api/qq/activity/${viewActivity.value.id}/notify`)
    ElMessage.success(res.data.message || 'QQ群通知已发送')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  }
}

async function qqRemindUnsigned() {
  try {
    await ElMessageBox.confirm('确定向所有未签到同学发送QQ私信提醒吗？', '提示', { type: 'warning' })
  } catch { return }
  try {
    const res = await api.post(`/api/qq/activity/${viewActivity.value.id}/remind`)
    ElMessage.success(res.data.message || '提醒完成')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  }
}

async function qqRemindOne(row) {
  try {
    await ElMessageBox.confirm(`确定提醒 ${row.student_name} 签到吗？`, '提示', { type: 'warning' })
  } catch { return }
  try {
    const res = await api.post(`/api/qq/activity/${viewActivity.value.id}/remind-one`, { student_id: row.student_id })
    ElMessage.success(res.data.message || '提醒已发送')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  }
}

// ---------------- 生命周期 ----------------
onMounted(() => {
  checkDevice()
  window.addEventListener('resize', checkDevice)
  loadActivities()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkDevice)
  stopCheckinTimer()
})
</script>

<style scoped>
.activity-container {
  padding: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

/* --- 签到码大数字展示 --- */
.checkin-code {
  font-size: 64px;
  font-weight: bold;
  letter-spacing: 12px;
  color: #409EFF;
  background: #f5f7fa;
  border: 2px solid #409EFF;
  border-radius: 8px;
  padding: 20px 0;
  font-family: 'Courier New', monospace;
}

/* --- 移动端卡片样式 --- */
.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mobile-card {
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-weight: bold;
  font-size: 16px;
}

.card-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 8px;
}

.card-body p {
  margin: 6px 0;
  color: #606266;
  font-size: 14px;
}

/* 移动端按钮布局精细化 */
.card-footer {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.primary-actions, .admin-actions {
  display: flex;
  flex-wrap: wrap;
  width: 100%;
  gap: 8px;
}

/* 覆盖 Element Plus 的兄弟按钮间距，配合 gap 使用 */
.card-footer .el-button {
  margin-left: 0 !important;
  flex: 1;
}

/* --- 弹窗内的操作栏布局 --- */
.action-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.action-bar .el-button {
  margin-left: 0 !important;
}

.manual-add-wrapper {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.responsive-select {
  width: 200px;
}

/* --- 移动端参与名单特殊样式 --- */
.mobile-part-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mobile-part-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background: #F7F8FA;
  border-radius: 6px;
  border: 1px solid #EBEEF5;
}

.part-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.part-name {
  font-weight: bold;
  color: #303133;
}

.part-id {
  font-size: 13px;
  color: #909399;
}

.part-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.part-select {
  flex: 1;
}

/* --- 响应式媒体查询 (针对手机端 < 768px) --- */
@media screen and (max-width: 768px) {
  .activity-container {
    padding: 10px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .header-btn {
    width: 100%;
  }

  .action-bar .el-button {
    flex: 1;
    min-width: 30%; 
  }
  
  .manual-add-wrapper {
    width: 100%;
  }
  
  .responsive-select {
    flex: 1;
    width: auto;
  }
  
  /* 去除全屏弹窗的默认 margin，并调整内边距 */
  :deep(.modern-dialog) {
    margin: 0 !important;
  }

  :deep(.modern-dialog .el-dialog__body) {
    padding: 15px !important;
  }

  /* 底部按钮对齐调整 */
  .dialog-footer {
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }
  .dialog-footer .el-button {
    flex: 1;
    margin-left: 0 !important;
  }
}
</style>