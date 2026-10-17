<template>
  <div class="certificate-manage-container">
    <div class="page-header">
      <div class="header-left">
        <div class="title-indicator"></div>
        <h3 class="page-title">奖状管理</h3>
      </div>
      <div class="header-right">
        <el-date-picker
          v-model="exportDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始"
          end-placeholder="结束"
          value-format="YYYY-MM-DD"
          size="small"
          style="width: 240px;"
        />
        <el-button size="small" type="primary" plain :icon="Download" :loading="exportExcelLoading" @click="handleExportExcel">导出Excel</el-button>
        <el-button size="small" type="success" plain :icon="Download" :loading="exportZipLoading" @click="handleExportZip">下载全部</el-button>
      </div>
    </div>

    <el-card class="modern-card upload-card" shadow="never">
      <div class="card-header">
        <span class="card-title">{{ isEditing ? '编辑奖状' : '上传新奖状' }}</span>
        <span class="card-subtitle">{{ isEditing ? '修改荣誉信息' : '记录你的每一个荣誉时刻' }}</span>
      </div>
      
      <el-form :model="certForm" label-position="top" size="large" class="modern-form">
        <el-row :gutter="24">
          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="奖项名称">
              <el-input v-model="certForm.award_name" placeholder="例如：全国数学建模竞赛一等奖" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="获奖级别">
              <el-select v-model="certForm.award_level" placeholder="请选择级别" style="width: 100%">
                <el-option label="国家级" value="国家级" />
                <el-option label="省级" value="省级" />
                <el-option label="校级" value="校级" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="获奖日期 (可选)">
              <el-date-picker 
                v-model="certForm.award_date" 
                type="date" 
                style="width: 100%"
                value-format="YYYY-MM-DD" 
                placeholder="请选择颁奖日期" 
              />
            </el-form-item>
          </el-col>
          
          <el-col v-if="authStore.canViewAllData && !isEditing" :xs="24" :sm="12" :md="8">
            <el-form-item label="归属学生学号">
              <el-input v-model="certForm.student_id" placeholder="请输入归属人的学号" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="证明文件 (图片)">
              <el-upload 
                ref="uploadRef" 
                class="inline-upload"
                :auto-upload="false" 
                :limit="1"
                accept=".jpg,.jpeg,.png,.gif,.webp"
                :on-change="handleFileChange"
                :on-remove="handleFileRemove"
                :show-file-list="true"
              >
                <el-button plain :icon="Picture">选择本地图片</el-button>
                <template #tip>
                  <div class="el-upload__tip">编辑时留空则不更新图片</div>
                </template>
              </el-upload>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8" class="action-col">
            <el-button 
              type="primary" 
              size="large" 
              :icon="Upload" 
              :loading="uploading" 
              @click="handleSubmit"
              class="submit-btn"
            >
              {{ isEditing ? '保存更改' : '提交保存' }}
            </el-button>
            <el-button 
              v-if="isEditing"
              size="large"
              @click="cancelEdit"
              class="cancel-btn"
            >
              取消
            </el-button>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <el-card class="modern-card list-card" shadow="never">
      <div class="list-header">
        <span class="card-title">荣誉展厅</span>
        <div class="filter-actions">
          <el-select v-model="filterLevel" placeholder="全部级别" clearable class="filter-item" @change="loadCertificates">
            <el-option label="国家级" value="国家级" />
            <el-option label="省级" value="省级" />
            <el-option label="校级" value="校级" />
          </el-select>
          <el-input 
            v-if="authStore.canViewAllData" 
            v-model="filterStudentId" 
            placeholder="按学号检索" 
            clearable
            :prefix-icon="Search"
            class="filter-item" 
            @change="loadCertificates" 
            @keyup.enter="loadCertificates"
          />
          <el-input 
            v-model="filterYear" 
            placeholder="按年份 (如2024)" 
            clearable 
            :prefix-icon="Calendar"
            class="filter-item" 
            @change="loadCertificates" 
            @keyup.enter="loadCertificates"
          />
        </div>
      </div>

      <el-table 
        v-if="!isMobile"
        :data="certificates" 
        style="width: 100%" 
        v-loading="loading"
        class="custom-table"
        :header-cell-style="{ background: '#F7F8FA', color: '#4E5969', fontWeight: '500' }"
      >
        <el-table-column v-if="authStore.canViewAllData" prop="student_name" label="获奖人" width="120">
          <template #default="{ row }">
            <span class="student-name">{{ row.student_name }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="authStore.canViewAllData" prop="student_student_id" label="学号" width="140" />
        
        <el-table-column prop="award_name" label="奖项名称" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="award-name-cell">
              <el-icon class="award-icon"><Trophy /></el-icon>
              <span>{{ row.award_name }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="award_level" label="获奖级别" width="120" align="center">
          <template #default="{ row }">
            <el-tag 
              round
              effect="light"
              :type="row.award_level === '国家级' ? 'warning' : row.award_level === '省级' ? 'primary' : 'success'"
            >
              {{ row.award_level }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="award_date" label="获奖日期" width="140">
          <template #default="{ row }">
            <span class="time-text">{{ row.award_date ? new Date(row.award_date).toLocaleDateString('zh-CN') : '-' }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="证书扫描件" width="100" align="center">
          <template #default="{ row }">
            <el-image 
              v-if="row.image_path" 
              class="cert-thumbnail"
              :src="`/static/${row.image_path}`"
              fit="cover" 
              :preview-src-list="[`/static/${row.image_path}`]" 
              :preview-teleported="true"
              :hide-on-click-modal="true"
              :z-index="3000"
            >
              <template #error>
                <div class="image-slot"><el-icon><Picture /></el-icon></div>
              </template>
            </el-image>
            <span v-else style="color: #C9CDD4; font-size: 13px;">无图片</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="created_at" label="收录时间" width="170">
          <template #default="{ row }">
            <span class="time-text">{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" link :icon="Delete" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-cert-list" v-loading="loading">
        <el-card v-for="row in certificates" :key="row.id" class="mobile-card" shadow="sm">
          <div class="m-card-header">
            <div class="m-award-name">
              <el-icon class="award-icon"><Trophy /></el-icon>
              <span>{{ row.award_name }}</span>
            </div>
            <el-tag 
              round size="small" effect="light"
              :type="row.award_level === '国家级' ? 'warning' : row.award_level === '省级' ? 'primary' : 'success'"
            >
              {{ row.award_level }}
            </el-tag>
          </div>
          
          <div class="m-card-body">
            <div class="m-info-group">
              <p v-if="authStore.canViewAllData">
                <span class="label">获奖人:</span> 
                {{ row.student_name }} ({{ row.student_student_id }})
              </p>
              <p>
                <span class="label">日期:</span> 
                {{ row.award_date ? new Date(row.award_date).toLocaleDateString('zh-CN') : '-' }}
              </p>
            </div>
            
            <div class="m-img-wrapper">
              <el-image 
                v-if="row.image_path" 
                class="cert-thumbnail"
                :src="`/static/${row.image_path}`"
                fit="cover" 
                :preview-src-list="[`/static/${row.image_path}`]" 
                :preview-teleported="true"
                :hide-on-click-modal="true"
                :z-index="3000"
              />
              <span v-else class="no-img">无图片</span>
            </div>
          </div>
          
          <div class="m-card-footer">
            <span class="time-text">{{ new Date(row.created_at).toLocaleDateString('zh-CN') }} 收录</span>
            <div class="m-actions">
              <el-button size="small" type="primary" link :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" link :icon="Delete" @click="handleDelete(row)">删除</el-button>
            </div>
          </div>
        </el-card>
      </div>

    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Picture, Search, Calendar, Trophy, Edit, Delete, Download } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const authStore = useAuthStore()

// 响应式状态管理
const isMobile = ref(false)
const checkDevice = () => {
  isMobile.value = window.innerWidth <= 768
}

const uploadRef = ref(null)
const uploading = ref(false)
const loading = ref(false)
const certificates = ref([])
const selectedFile = ref(null)
const filterLevel = ref('')
const filterStudentId = ref('')
const filterYear = ref('')
const isEditing = ref(false)
const editingId = ref(null)

// 导出相关
const exportDateRange = ref(null)
const exportExcelLoading = ref(false)
const exportZipLoading = ref(false)

const certForm = reactive({
  award_name: '',
  award_level: '校级',
  award_date: '',
  student_id: '',
})

function handleFileChange(file) {
  selectedFile.value = file
}

function handleFileRemove() {
  selectedFile.value = null
}

function resetForm() {
  certForm.award_name = ''
  certForm.award_level = '校级'
  certForm.award_date = ''
  certForm.student_id = ''
  selectedFile.value = null
  isEditing.value = false
  editingId.value = null
  if (uploadRef.value) uploadRef.value.clearFiles()
}

async function handleSubmit() {
  if (!certForm.award_name) return ElMessage.warning('请输入奖项名称')

  if (isEditing.value) {
    if (!editingId.value) return
    uploading.value = true
    const formData = new FormData()
    formData.append('award_name', certForm.award_name)
    formData.append('award_level', certForm.award_level)
    if (certForm.award_date) formData.append('award_date', certForm.award_date)
    if (selectedFile.value) {
      formData.append('file', selectedFile.value.raw)
    }
    try {
      await api.put(`/api/certificates/${editingId.value}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      ElMessage.success('奖状信息已更新')
      resetForm()
      loadCertificates()
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || '更新失败')
    } finally {
      uploading.value = false
    }
  } else {
    if (!selectedFile.value) return ElMessage.warning('请选择要上传的奖状图片文件')
    if (authStore.canViewAllData && !certForm.student_id) return ElMessage.warning('请输入学生学号')
    uploading.value = true
    const formData = new FormData()
    formData.append('award_name', certForm.award_name)
    formData.append('award_level', certForm.award_level)
    if (certForm.award_date) formData.append('award_date', certForm.award_date)
    if (authStore.canViewAllData) {
      formData.append('student_id', parseInt(certForm.student_id))
    } else {
      formData.append('student_id', authStore.user.id)
    }
    formData.append('file', selectedFile.value.raw)

    try {
      await api.post('/api/certificate/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      ElMessage.success('奖状上传成功')
      resetForm()
      loadCertificates()
    } catch (err) {
      ElMessage.error(err.response?.data?.detail || '上传失败')
    } finally {
      uploading.value = false
    }
  }
}

function openEditDialog(row) {
  isEditing.value = true
  editingId.value = row.id
  certForm.award_name = row.award_name
  certForm.award_level = row.award_level
  certForm.award_date = row.award_date ? new Date(row.award_date).toISOString().slice(0, 10) : ''
  selectedFile.value = null
  if (uploadRef.value) uploadRef.value.clearFiles()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function cancelEdit() {
  resetForm()
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除奖状「${row.award_name}」吗？该操作不可撤销。`,
      '删除确认',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
    )
    await api.delete(`/api/certificates/${row.id}`)
    ElMessage.success('奖状已删除')
    loadCertificates()
  } catch (err) {
    if (err !== 'cancel' && err !== 'close') {
      ElMessage.error(err.response?.data?.detail || '删除失败')
    }
  }
}

async function loadCertificates() {
  loading.value = true
  try {
    const params = {}
    if (filterLevel.value) params.award_level = filterLevel.value
    if (filterStudentId.value && authStore.canViewAllData) params.student_id = filterStudentId.value
    if (filterYear.value) params.academic_year = filterYear.value
    
    const res = await api.get('/api/certificates', { params })
    certificates.value = res.data
  } catch {
    ElMessage.error('加载奖状列表失败')
  } finally {
    loading.value = false
  }
}

async function handleExportExcel() {
  exportExcelLoading.value = true
  try {
    const params = {}
    if (exportDateRange.value) {
      params.start_date = exportDateRange.value[0]
      params.end_date = exportDateRange.value[1]
    }
    const res = await api.get('/api/certificates/export-excel', { params, responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '奖状列表.xlsx'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (err) {
    ElMessage.error('导出失败')
  } finally {
    exportExcelLoading.value = false
  }
}

async function handleExportZip() {
  exportZipLoading.value = true
  try {
    const params = {}
    if (exportDateRange.value) {
      params.start_date = exportDateRange.value[0]
      params.end_date = exportDateRange.value[1]
    }
    const res = await api.get('/api/certificates/download-zip', { params, responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'application/zip' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '奖状图片.zip'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (err) {
    if (err.response?.status === 404) {
      ElMessage.warning('没有符合条件的奖状图片')
    } else {
      ElMessage.error('下载失败')
    }
  } finally {
    exportZipLoading.value = false
  }
}

onMounted(() => {
  checkDevice()
  window.addEventListener('resize', checkDevice)
  loadCertificates()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkDevice)
})
</script>

<style scoped>
/* 容器基底 */
.certificate-manage-container {
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

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
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

/* 统一卡片样式 */
.modern-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.04);
  margin-bottom: 20px;
}

.card-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px dashed #E5E6EB;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #1D2129;
}

.card-subtitle {
  margin-left: 12px;
  font-size: 13px;
  color: #86909C;
}

/* 表单区域美化 */
.action-col {
  display: flex;
  align-items: flex-end;
  padding-bottom: 18px; /* 电脑端对其 Input */
  gap: 12px;
}

.submit-btn {
  width: 140px;
}

/* 输入框焦点高亮 */
:deep(.el-input__wrapper.is-focus),
:deep(.el-select .el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px #165DFF inset !important;
}

/* 列表区域 */
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.filter-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap; /* 允许折行 */
}

.filter-item {
  width: 150px;
}

/* 表格内元素美化 */
.student-name {
  font-weight: 500;
  color: #1D2129;
}

.award-name-cell {
  display: flex;
  align-items: center;
  color: #1D2129;
  font-weight: 500;
}

.award-icon {
  margin-right: 8px;
  color: #FF7D00;
  font-size: 16px;
}

.time-text {
  color: #86909C;
  font-size: 13px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* 图片缩略图美化 */
.cert-thumbnail {
  border-radius: 6px;
  border: 1px solid #E5E6EB;
  cursor: pointer;
  transition: all 0.3s;
  width: 60px;
  height: 45px;
}

.cert-thumbnail:hover {
  border-color: #165DFF;
  box-shadow: 0 4px 12px rgba(22, 93, 255, 0.2);
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

/* 移动端卡片样式 */
.mobile-cert-list {
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
}

.m-award-name {
  display: flex;
  align-items: center;
  font-weight: 600;
  color: #1D2129;
  font-size: 15px;
  line-height: 1.4;
  padding-right: 8px;
}

.m-card-body {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #F7F8FA;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 12px;
}

.m-info-group p {
  margin: 0 0 4px 0;
  font-size: 13px;
  color: #1D2129;
}
.m-info-group p:last-child {
  margin-bottom: 0;
}
.m-info-group .label {
  color: #86909C;
  margin-right: 4px;
}

.m-img-wrapper {
  flex-shrink: 0;
  margin-left: 12px;
}
.no-img {
  font-size: 12px;
  color: #C9CDD4;
}

.m-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #F2F3F5;
  padding-top: 12px;
}

/* 去除表格自带底边框 */
:deep(.custom-table::before) {
  display: none;
}

/* =======================================
   移动端响应式适配
   ======================================= */
@media screen and (max-width: 768px) {
  .card-header {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  .card-subtitle {
    margin-left: 0;
  }

  /* 消除移动端底部操作栏的多余 padding，并让按钮占满宽度 */
  .action-col {
    padding-bottom: 0;
    flex-direction: column;
    align-items: stretch;
    margin-top: 8px;
  }
  .submit-btn,
  .cancel-btn {
    width: 100%;
    margin-left: 0 !important;
  }

  /* 检索栏在手机端垂直堆叠 */
  .list-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  .filter-actions {
    width: 100%;
    flex-direction: column;
  }
  .filter-item {
    width: 100%;
  }
}
</style>