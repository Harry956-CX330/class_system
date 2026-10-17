<template>
  <div class="resource-manage-container">
    <div class="page-header">
      <div class="header-left">
        <div class="title-indicator"></div>
        <h3 class="page-title">资料管理</h3>
      </div>
    </div>

    <el-row :gutter="20" class="top-section">
      <el-col :xs="24" :sm="24" :md="10" class="mb-col">
        <el-card class="modern-card category-card" shadow="never">
          <div class="card-header">
            <span class="card-title">分类管理</span>
            <el-button type="primary" link :icon="Plus" @click="openCategoryDialog">添加分类</el-button>
          </div>
          <div class="category-list">
            <template v-if="categories.length">
              <el-tag
                v-for="cat in categories"
                :key="cat.id"
                closable
                class="custom-tag"
                effect="light"
                @close="confirmDeleteCategory(cat)"
              >
                <el-icon class="tag-icon"><Folder /></el-icon>
                {{ cat.name }} <span class="count">({{ cat.file_count || 0 }})</span>
              </el-tag>
            </template>
            <div v-else class="empty-text">暂无分类，请先添加</div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="24" :md="14" class="mb-col">
        <el-card class="modern-card upload-card" shadow="never">
          <div class="card-header">
            <span class="card-title">文件上传</span>
          </div>
          <div class="upload-bar">
            <el-select v-model="uploadCategoryId" placeholder="归属分类" class="modern-select upload-item">
              <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="cat.id" />
            </el-select>
            
            <el-select v-model="uploadVisibility" placeholder="可见范围" class="modern-select upload-item">
              <el-option label="班级同学可见" value="student" />
              <el-option label="仅管理员可见" value="admin" />
            </el-select>

            <el-upload
              ref="uploadRef"
              class="inline-upload upload-item"
              :auto-upload="false"
              :limit="1"
              accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.zip,.rar,.jpg,.jpeg,.png,.gif"
              :show-file-list="false"
              :on-change="handleUploadFileChange"
              :on-remove="handleUploadFileRemove"
            >
              <el-button plain type="info" :icon="Document" class="file-choose-btn">
                {{ uploadFile ? uploadFile.name : '选择文件' }}
              </el-button>
            </el-upload>

            <el-button 
              type="primary" 
              :icon="Upload" 
              :disabled="!uploadFile || !uploadCategoryId" 
              @click="handleUpload"
              class="upload-btn upload-item"
            >
              开始上传
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="modern-card list-card" shadow="never">
      <div class="list-header">
        <span class="card-title">资源列表</span>
        <div class="list-actions">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            class="modern-datepicker filter-item"
          />
          <el-button 
            type="danger" 
            plain
            :icon="Delete" 
            :disabled="!selectedIds.length" 
            @click="handleBatchDelete"
            class="filter-item batch-btn"
          >
            批量删除 ({{ selectedIds.length }})
          </el-button>
        </div>
      </div>

      <el-table
        v-if="!isMobile"
        :data="filteredFiles"
        style="width: 100%"
        v-loading="fileLoading"
        @selection-change="handleSelectionChange"
        ref="tableRef"
        class="custom-table"
        :header-cell-style="{ background: '#F7F8FA', color: '#4E5969', fontWeight: '500' }"
      >
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column prop="original_name" label="文件名称" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="file-name-cell">
              <el-icon class="file-icon"><Document /></el-icon>
              <span>{{ row.original_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="category_name" label="所属分类" width="140">
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain" round>{{ row.category_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="文件大小" width="100">
          <template #default="{ row }">
            <span class="sub-text">{{ fileSize(row.file_size) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="uploader_name" label="上传者" width="120" />
        <el-table-column label="上传时间" width="180">
          <template #default="{ row }">
            <span class="sub-text">{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link :icon="View" @click="handlePreview(row)">预览</el-button>
            <el-button size="small" type="success" link :icon="Download" @click="handleDownload(row)">下载</el-button>
            <el-button size="small" type="danger" link :icon="Delete" @click="handleDeleteFile(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-file-list" v-loading="fileLoading">
        <el-checkbox-group v-model="selectedIds">
          <el-card v-for="row in filteredFiles" :key="row.id" class="mobile-card" shadow="sm">
            <div class="m-card-header">
              <el-checkbox :value="row.id" :label="row.id" class="m-checkbox">
                <div class="m-file-title">
                  <el-icon class="file-icon"><Document /></el-icon>
                  <span class="text-truncate">{{ row.original_name }}</span>
                </div>
              </el-checkbox>
            </div>
            
            <div class="m-card-body">
              <div class="m-info-row">
                <el-tag size="small" type="info" effect="plain" round>{{ row.category_name }}</el-tag>
                <span class="m-size">{{ fileSize(row.file_size) }}</span>
              </div>
              <div class="m-info-row mt-1">
                <span class="m-uploader">上传人: {{ row.uploader_name }}</span>
                <span class="m-time">{{ new Date(row.created_at).toLocaleDateString('zh-CN') }}</span>
              </div>
            </div>
            
            <div class="m-card-footer">
              <el-button size="small" type="primary" link :icon="View" @click="handlePreview(row)">预览</el-button>
              <el-button size="small" type="success" link :icon="Download" @click="handleDownload(row)">下载</el-button>
              <el-button size="small" type="danger" link :icon="Delete" @click="handleDeleteFile(row)">删除</el-button>
            </div>
          </el-card>
        </el-checkbox-group>
        <el-empty v-if="filteredFiles.length === 0" description="没有找到匹配的文件"></el-empty>
      </div>
    </el-card>

    <el-dialog v-model="categoryDialogVisible" title="添加新分类" width="95%" style="max-width: 450px" class="modern-dialog" destroy-on-close>
      <el-form :model="categoryForm" label-position="top">
        <el-form-item label="分类名称">
          <el-input v-model="categoryForm.name" placeholder="例如：期末复习资料" size="large" />
        </el-form-item>
        <el-form-item label="分类描述 (选填)">
          <el-input v-model="categoryForm.description" type="textarea" :rows="3" placeholder="简单描述该分类的用途..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="categoryDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleAddCategory">确认添加</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Folder, Document, Upload, Delete, View, Download } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const STATIC = '/static/'
const authStore = useAuthStore()

// 响应式状态管理
const isMobile = ref(false)
const checkDevice = () => {
  isMobile.value = window.innerWidth <= 768
}

const categories = ref([])
const files = ref([])
const fileLoading = ref(false)
const selectedIds = ref([])
const tableRef = ref(null)
const dateRange = ref([])

const uploadCategoryId = ref('')
const uploadVisibility = ref('student')
const uploadRef = ref(null)
const uploadFile = ref(null)

const categoryDialogVisible = ref(false)
const categoryForm = reactive({
  name: '',
  description: '',
})

const filteredFiles = computed(() => {
  if (!dateRange.value || dateRange.value.length !== 2) return files.value
  const [start, end] = dateRange.value
  return files.value.filter((f) => {
    const d = f.created_at ? f.created_at.slice(0, 10) : ''
    return d >= start && d <= end
  })
})

function fileSize(size) {
  return size < 1024
    ? size + ' B'
    : size < 1048576
      ? (size / 1024).toFixed(1) + ' KB'
      : (size / 1048576).toFixed(1) + ' MB'
}

function handleSelectionChange(selection) {
  selectedIds.value = selection.map((s) => s.id)
}

function getExt(filename) {
  return filename ? filename.split('.').pop().toLowerCase() : ''
}

function isImage(ext) {
  return ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)
}

function isOffice(ext) {
  return ['docx', 'xlsx', 'pptx'].includes(ext)
}

function handlePreview(row) {
  const ext = getExt(row.filename)
  if (isImage(ext) || ext === 'pdf') {
    window.open(STATIC + row.filename, '_blank')
  } else if (isOffice(ext)) {
    window.open('https://view.officeapps.live.com/op/view.aspx?src=' + encodeURIComponent(STATIC + row.filename), '_blank')
  } else {
    ElMessage.info('该格式暂不支持在线预览，请下载后查看')
  }
}

function handleDownload(row) {
  window.open(STATIC + row.filename + '?download=1', '_blank')
}

async function loadCategories() {
  try {
    const res = await api.get('/api/resource-categories')
    categories.value = res.data
  } catch {
    ElMessage.error('加载分类失败')
  }
}

async function loadFiles() {
  fileLoading.value = true
  try {
    const res = await api.get('/api/resources')
    files.value = res.data
  } catch {
    ElMessage.error('加载文件列表失败')
  } finally {
    fileLoading.value = false
  }
}

function openCategoryDialog() {
  categoryForm.name = ''
  categoryForm.description = ''
  categoryDialogVisible.value = true
}

async function handleAddCategory() {
  if (!categoryForm.name.trim()) {
    return ElMessage.warning('请输入分类名称')
  }
  try {
    await api.post('/api/resource-categories', {
      name: categoryForm.name,
      description: categoryForm.description,
    })
    ElMessage.success('添加分类成功')
    categoryDialogVisible.value = false
    loadCategories()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '添加分类失败')
  }
}

function confirmDeleteCategory(cat) {
  ElMessageBox.confirm(`确定要删除分类 "${cat.name}" 吗？该操作不可逆转。`, '删除确认', {
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    handleDeleteCategory(cat.id)
  }).catch(() => {})
}

async function handleDeleteCategory(id) {
  try {
    await api.delete(`/api/resource-categories/${id}`)
    ElMessage.success('删除分类成功')
    loadCategories()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '删除分类失败')
  }
}

function handleUploadFileChange(file) {
  uploadFile.value = file
}

function handleUploadFileRemove() {
  uploadFile.value = null
}

async function handleUpload() {
  if (!uploadCategoryId.value) return ElMessage.warning('请选择归属分类')
  if (!uploadFile.value) return ElMessage.warning('请选择要上传的文件')
  
  try {
    const formData = new FormData()
    formData.append('category_id', uploadCategoryId.value)
    formData.append('visibility', uploadVisibility.value)
    formData.append('file', uploadFile.value.raw)
    
    await api.post('/api/resources/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    
    ElMessage.success('文件上传成功')
    uploadFile.value = null
    if (uploadRef.value) {
      uploadRef.value.clearFiles()
    }
    loadFiles()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '上传失败')
  }
}

async function handleDeleteFile(row) {
  try {
    await ElMessageBox.confirm(`确定要删除文件 "${row.original_name}" 吗？`, '删除提示', { 
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning' 
    })
    await api.delete(`/api/resources/${row.id}`)
    ElMessage.success('文件已删除')
    loadFiles()
  } catch {}
}

async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(`确定要批量删除选中的 ${selectedIds.value.length} 个文件吗？`, '批量删除', { 
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning' 
    })
    await api.post('/api/resources/batch-delete', { ids: selectedIds.value })
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    if (tableRef.value) {
      tableRef.value.clearSelection()
    }
    loadFiles()
  } catch {}
}

onMounted(() => {
  checkDevice()
  window.addEventListener('resize', checkDevice)
  loadCategories()
  loadFiles()
})

onUnmounted(() => {
  window.removeEventListener('resize', checkDevice)
})
</script>

<style scoped>
/* 全局容器 */
.resource-manage-container {
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

/* 卡片通用样式 */
.modern-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.04);
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #1D2129;
}

/* 分类标签区域 */
.category-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.custom-tag {
  padding: 0 12px;
  height: 32px;
  line-height: 30px;
  border-radius: 16px;
  border: 1px solid #E5E6EB;
  background: #F7F8FA;
  color: #4E5969;
  font-size: 13px;
  transition: all 0.3s;
}

.custom-tag:hover {
  background: #E8F3FF;
  border-color: #165DFF;
  color: #165DFF;
}

.tag-icon {
  margin-right: 4px;
  vertical-align: text-bottom;
}

.count {
  color: #86909C;
  margin-left: 2px;
}

.empty-text {
  color: #86909C;
  font-size: 14px;
}

/* 上传操作栏 */
.upload-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.upload-item {
  flex-shrink: 0;
}

.modern-select {
  width: 160px;
}

.inline-upload {
  display: inline-block;
  flex: 1;
  min-width: 180px;
}

:deep(.inline-upload .el-upload) {
  display: block;
  width: 100%;
}

.file-choose-btn {
  width: 100%;
  justify-content: flex-start;
  color: #4E5969;
  border-color: #E5E6EB;
  overflow: hidden;
  text-overflow: ellipsis;
}

.upload-btn {
  padding: 0 20px;
}

/* 文件列表区域 */
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.list-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.modern-datepicker {
  width: 280px;
}

.file-name-cell {
  display: flex;
  align-items: center;
  color: #1D2129;
  font-weight: 500;
}

.file-icon {
  margin-right: 8px;
  color: #165DFF;
  font-size: 16px;
  flex-shrink: 0;
}

.sub-text {
  color: #86909C;
  font-size: 13px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* 覆盖表格底边框 */
:deep(.custom-table::before) {
  display: none;
}

/* 移动端卡片视图样式 */
.mobile-file-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mobile-card {
  border-radius: 8px;
  border: 1px solid #E5E6EB;
}

.m-card-header {
  padding-bottom: 8px;
  border-bottom: 1px dashed #E5E6EB;
  margin-bottom: 12px;
}

.m-checkbox {
  width: 100%;
  display: flex;
  align-items: center;
}

:deep(.m-checkbox .el-checkbox__label) {
  flex: 1;
  overflow: hidden;
  padding-left: 10px;
}

.m-file-title {
  display: flex;
  align-items: center;
  font-weight: 600;
  color: #1D2129;
  font-size: 15px;
}

.text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.m-card-body {
  margin-bottom: 12px;
}

.m-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #4E5969;
}

.mt-1 {
  margin-top: 8px;
}

.m-size, .m-uploader, .m-time {
  color: #86909C;
}

.m-card-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  border-top: 1px solid #F2F3F5;
  padding-top: 12px;
}

/* =======================================
   移动端响应式适配
   ======================================= */
@media screen and (max-width: 768px) {
  .mb-col {
    margin-bottom: 16px;
  }
  
  /* 电脑端固定高度在移动端需取消 */
  .category-card, .upload-card {
    height: auto !important;
  }

  /* 上传栏改为垂直排列 */
  .upload-bar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .modern-select {
    width: 100% !important;
  }
  
  .inline-upload {
    width: 100%;
  }

  .upload-btn {
    width: 100%;
  }

  /* 列表操作栏改为垂直排布 */
  .list-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .list-actions {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  .modern-datepicker {
    width: 100% !important;
  }
  
  .batch-btn {
    width: 100%;
    margin-left: 0 !important;
  }
}

/* 针对大于移动端但需要高度统一的情况 */
@media screen and (min-width: 769px) {
  .category-card, .upload-card {
    height: 140px;
    overflow-y: auto;
  }
}
</style>