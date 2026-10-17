<template>
  <div class="social-practice-container">
    <div class="page-header">
      <div class="header-left">
        <div class="title-indicator"></div>
        <h3 class="page-title">社会实践</h3>
      </div>
    </div>

    <el-row :gutter="20" class="stat-row">
      <el-col :xs="24" :sm="12" class="mb-col">
        <el-card class="data-card" shadow="never">
          <div class="card-content">
            <div class="card-info">
              <div class="card-title">实践活动总数</div>
              <div class="card-value">{{ stats.total }}</div>
            </div>
            <div class="card-icon icon-primary">
              <el-icon><Compass /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" class="mb-col">
        <el-card class="data-card" shadow="never">
          <div class="card-content">
            <div class="card-info">
              <div class="card-title">累计参与人数</div>
              <div class="card-value">{{ stats.student_count }}</div>
            </div>
            <div class="card-icon icon-success">
              <el-icon><UserFilled /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="page-card" shadow="never">
      <div class="list-header">
        <span class="list-title">实践记录</span>
        <el-button type="primary" :icon="Plus" @click="openAddDialog" class="add-btn">
          添加记录
        </el-button>
      </div>

      <el-table 
        v-if="!isMobile"
        :data="records" 
        style="width: 100%" 
        v-loading="loading"
        class="custom-table"
        :header-cell-style="{ background: '#F7F8FA', color: '#4E5969', fontWeight: '500' }"
      >
        <el-table-column v-if="authStore.canViewAllData" prop="student_name" label="学生姓名" width="120">
          <template #default="{ row }">
            <span class="student-name">{{ row.student_name }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="activity_name" label="活动名称" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="activity-cell">
              <el-icon class="activity-icon"><Compass /></el-icon>
              <span>{{ row.activity_name }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="role" label="角色/分工" width="140">
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain" round>{{ row.role || '参与者' }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="实践周期" width="220">
          <template #default="{ row }">
            <div class="date-range-cell">
              <el-icon><Calendar /></el-icon>
              <span>{{ formatDate(row.start_date) }} 至 {{ formatDate(row.end_date) }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="证明/证书" width="120" align="center">
          <template #default="{ row }">
            <el-image 
              v-if="row.image_path" 
              class="cert-thumbnail"
              :src="`/static/${row.image_path}`"
              fit="cover"
              :preview-src-list="[`/static/${row.image_path}`]" 
              preview-teleported
              hide-on-click-modal
            >
              <template #error>
                <div class="image-slot"><el-icon><Picture /></el-icon></div>
              </template>
            </el-image>
            <span v-else class="empty-cert">未上传</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="created_at" label="登记时间" width="160">
          <template #default="{ row }">
            <span class="time-text">{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <div class="action-cell">
              <el-button size="small" type="primary" link :icon="EditPen" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" link :icon="Delete" @click="handleDelete(row)">删除</el-button>
              <el-divider direction="vertical" />
              <el-upload
                class="inline-upload"
                :show-file-list="false"
                :auto-upload="false"
                :limit="1"
                accept=".jpg,.jpeg,.png,.gif,.webp,.pdf"
                :on-change="(file) => handleUploadCertificate(row, file)"
              >
                <el-button size="small" type="success" link :icon="Upload">传证书</el-button>
              </el-upload>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-record-list" v-loading="loading">
        <el-card v-for="row in records" :key="row.id" class="mobile-card" shadow="sm">
          <div class="m-card-header">
            <div class="m-activity-name">
              <el-icon class="activity-icon"><Compass /></el-icon>
              <span>{{ row.activity_name }}</span>
            </div>
            <el-tag size="small" type="info" effect="plain" round>{{ row.role || '参与者' }}</el-tag>
          </div>

          <div class="m-card-body">
            <div class="m-info-row" v-if="authStore.canViewAllData">
              <span class="label">学生姓名:</span>
              <span class="student-name">{{ row.student_name }}</span>
            </div>
            <div class="m-info-row">
              <span class="label">实践周期:</span>
              <span class="date-text">{{ formatDate(row.start_date) }} ~ {{ formatDate(row.end_date) }}</span>
            </div>
            <div class="m-info-row align-start">
              <span class="label">证明证书:</span>
              <div>
                <el-image 
                  v-if="row.image_path" 
                  class="cert-thumbnail m-thumb"
                  :src="`/static/${row.image_path}`"
                  fit="cover"
                  :preview-src-list="[`/static/${row.image_path}`]" 
                  preview-teleported
                  hide-on-click-modal
                />
                <span v-else class="empty-cert">未上传</span>
              </div>
            </div>
          </div>

          <div class="m-card-footer">
            <span class="time-text">{{ new Date(row.created_at).toLocaleDateString('zh-CN') }} 登记</span>
            <div class="m-actions">
              <el-upload
                class="inline-upload"
                :show-file-list="false"
                :auto-upload="false"
                :limit="1"
                accept=".jpg,.jpeg,.png,.gif,.webp,.pdf"
                :on-change="(file) => handleUploadCertificate(row, file)"
              >
                <el-button size="small" type="success" link :icon="Upload">传证书</el-button>
              </el-upload>
              <el-button size="small" type="primary" link :icon="EditPen" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" link :icon="Delete" @click="handleDelete(row)">删除</el-button>
            </div>
          </div>
        </el-card>
        <el-empty v-if="records.length === 0" description="暂无实践记录" />
      </div>
    </el-card>

    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑实践记录' : '添加实践记录'" 
      width="95%" 
      style="max-width: 600px" 
      class="modern-dialog" 
      destroy-on-close
    >
      <el-form :model="recordForm" label-position="top" size="large">
        <el-form-item label="实践活动名称">
          <el-input v-model="recordForm.activity_name" placeholder="例如：暑期三下乡志愿服务" />
        </el-form-item>
        
        <el-row :gutter="20">
          <el-col :xs="24" :sm="authStore.canViewAllData ? 12 : 24">
            <el-form-item label="角色/分工">
              <el-input v-model="recordForm.role" placeholder="例如：队长、志愿者" />
            </el-form-item>
          </el-col>
          <el-col v-if="authStore.canViewAllData" :xs="24" :sm="12">
            <el-form-item label="归属学生学号">
              <el-input v-model="recordForm.student_id" placeholder="请输入归属学生学号" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12">
            <el-form-item label="开始日期">
              <el-date-picker 
                v-model="recordForm.start_date" 
                type="date" 
                style="width: 100%"
                value-format="YYYY-MM-DD" 
                placeholder="请选择开始日期" 
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="结束日期">
              <el-date-picker 
                v-model="recordForm.end_date" 
                type="date" 
                style="width: 100%"
                value-format="YYYY-MM-DD" 
                placeholder="请选择结束日期" 
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="实践内容描述 (选填)">
          <RichEditor v-model="recordForm.description" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSubmit">
            {{ isEdit ? '保存更改' : '确认添加' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, EditPen, Delete, Upload, Picture, Compass, UserFilled, Calendar } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const authStore = useAuthStore()

// 响应式状态管理
const isMobile = ref(false)
const checkDevice = () => {
  isMobile.value = window.innerWidth <= 768
}

const records = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const stats = ref({ total: 0, student_count: 0 })

const recordForm = reactive({
  activity_name: '',
  role: '',
  description: '',
  start_date: '',
  end_date: '',
  student_id: '',
})

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', year: 'numeric' }).replace(/\//g, '-')
}

async function loadStats() {
  try {
    const res = await api.get('/api/social-practices/stats')
    stats.value = res.data
  } catch {}
}

async function loadRecords() {
  loading.value = true
  try {
    const res = await api.get('/api/social-practices')
    records.value = res.data
  } catch {
    ElMessage.error('加载记录失败')
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  isEdit.value = false
  editId.value = null
  recordForm.activity_name = ''
  recordForm.role = ''
  recordForm.description = ''
  recordForm.start_date = ''
  recordForm.end_date = ''
  recordForm.student_id = ''
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  editId.value = row.id
  recordForm.activity_name = row.activity_name
  recordForm.role = row.role
  recordForm.description = row.description || ''
  recordForm.start_date = row.start_date
  recordForm.end_date = row.end_date
  recordForm.student_id = row.student_id ? String(row.student_id) : ''
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!recordForm.activity_name) {
    return ElMessage.warning('请输入实践活动名称')
  }

  saving.value = true
  try {
    const payload = {
      activity_name: recordForm.activity_name,
      role: recordForm.role,
      description: recordForm.description,
      start_date: recordForm.start_date,
      end_date: recordForm.end_date,
    }
    
    if (authStore.canViewAllData && recordForm.student_id) {
      payload.student_id = parseInt(recordForm.student_id)
    } else {
      payload.student_id = authStore.user.id
    }
    
    if (isEdit.value) {
      await api.put(`/api/social-practices/${editId.value}`, payload)
      ElMessage.success('记录修改成功')
    } else {
      await api.post('/api/social-practices', payload)
      ElMessage.success('记录添加成功')
    }
    dialogVisible.value = false
    loadRecords()
    loadStats()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleUploadCertificate(row, file) {
  const formData = new FormData()
  formData.append('file', file.raw)
  formData.append('sp_id', row.id)
  try {
    await api.post(`/api/social-practices/upload-certificate`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    ElMessage.success('证明文件上传成功')
    loadRecords()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '上传失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除记录 "${row.activity_name}" 吗？此操作不可恢复。`, '删除确认', { 
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning' 
    })
    await api.delete(`/api/social-practices/${row.id}`)
    ElMessage.success('记录已删除')
    loadRecords()
    loadStats()
  } catch {}
}

onMounted(() => {
  checkDevice()
  window.addEventListener('resize', checkDevice)
  loadStats()
  loadRecords()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkDevice)
})
</script>

<style scoped>
/* 容器基底 */
.social-practice-container {
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
  color: #1D2129;
}

/* 数据统计卡片 */
.stat-row {
  margin-bottom: 24px;
}

.data-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 8px 0 rgba(0, 0, 0, 0.04);
  transition: all 0.3s;
}

.data-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.08);
}

.card-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 4px;
}

.card-title {
  font-size: 14px;
  color: #86909C;
  margin-bottom: 8px;
}

.card-value {
  font-size: 28px;
  font-weight: 700;
  color: #1D2129;
  font-family: 'DIN Alternate', -apple-system, BlinkMacSystemFont, sans-serif;
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.icon-primary { background: #E8F3FF; color: #165DFF; }
.icon-success { background: #E8FFEA; color: #00B42A; }

/* 主列表卡片 */
.page-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  min-height: calc(100vh - 280px);
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.list-title {
  font-size: 16px;
  font-weight: 600;
  color: #1D2129;
}

/* 表格内元素美化 */
.student-name {
  font-weight: 500;
  color: #1D2129;
}

.activity-cell {
  display: flex;
  align-items: center;
  color: #1D2129;
  font-weight: 500;
}

.activity-icon {
  margin-right: 8px;
  color: #165DFF;
  font-size: 16px;
}

.date-range-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #4E5969;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 13px;
}

.time-text {
  color: #86909C;
  font-size: 13px;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}

/* 证书缩略图美化 */
.cert-thumbnail {
  border-radius: 6px;
  border: 1px solid #E5E6EB;
  cursor: pointer;
  transition: all 0.3s;
  width: 40px;
  height: 30px;
}

.cert-thumbnail:hover {
  border-color: #165DFF;
  box-shadow: 0 4px 12px rgba(22, 93, 255, 0.2);
}

.empty-cert {
  color: #C9CDD4;
  font-size: 13px;
}

.image-slot {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  background: #F7F8FA;
  color: #C9CDD4;
  font-size: 20px;
}

/* 操作列对其与上传按钮 */
.action-cell {
  display: flex;
  align-items: center;
}

.inline-upload {
  display: inline-flex;
  align-items: center;
}

/* 弹窗内输入框聚焦发光 */
:deep(.el-input__wrapper.is-focus),
:deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px #165DFF inset !important;
}

/* 去除表格底边框 */
:deep(.custom-table::before) {
  display: none;
}

/* =======================================
   移动端卡片视图样式
   ======================================= */
.mobile-record-list {
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

.m-activity-name {
  display: flex;
  align-items: center;
  font-weight: 600;
  color: #1D2129;
  font-size: 15px;
  line-height: 1.4;
  padding-right: 8px;
}

.m-card-body {
  margin-bottom: 12px;
  background-color: #F7F8FA;
  padding: 12px;
  border-radius: 6px;
}

.m-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
}

.m-info-row:last-child {
  margin-bottom: 0;
}

.m-info-row.align-start {
  align-items: flex-start;
}

.m-info-row .label {
  color: #86909C;
  white-space: nowrap;
}

.m-info-row .date-text {
  color: #1D2129;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.m-thumb {
  width: 50px;
  height: 36px;
}

.m-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #F2F3F5;
  padding-top: 12px;
}

.m-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* =======================================
   移动端响应式适配 (Media Queries)
   ======================================= */
@media screen and (max-width: 768px) {
  .mb-col {
    margin-bottom: 16px;
  }
  
  .list-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .add-btn {
    width: 100%;
  }

  /* 调整弹窗表单间距 */
  :deep(.modern-dialog .el-form-item) {
    margin-bottom: 16px;
  }
  :deep(.modern-dialog .el-row) {
    margin-left: 0 !important;
    margin-right: 0 !important;
  }
  :deep(.modern-dialog .el-col) {
    padding-left: 0 !important;
    padding-right: 0 !important;
  }
}
</style>