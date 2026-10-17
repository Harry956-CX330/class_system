<template>
  <div class="resource-download-container">
    <el-card class="page-card" shadow="never">
      <!-- 顶部标题栏 -->
      <div class="page-header">
        <div class="header-left">
          <div class="title-indicator"></div>
          <h3 class="page-title">资料下载中心</h3>
        </div>
      </div>

      <!-- 空状态展示 -->
      <el-empty 
        v-if="categories.length === 0 && allFiles.length === 0 && !loading" 
        description="班级暂无可用资料" 
        :image-size="200"
      />

      <!-- 资料分类标签页 -->
      <div v-else class="tabs-wrapper">
        <el-tabs v-model="activeTab" class="modern-tabs" @tab-change="handleTabChange">
          
          <!-- 全部资料 Tab -->
          <el-tab-pane label="全部资料" name="all">
            <el-table 
              :data="allFiles" 
              style="width: 100%" 
              v-loading="loading"
              class="custom-table"
              :header-cell-style="{ background: '#F7F8FA', color: '#4E5969', fontWeight: '500' }"
            >
              <el-table-column prop="original_name" label="文件名称" min-width="250" show-overflow-tooltip>
                <template #default="{ row }">
                  <div class="file-name-cell">
                    <el-icon class="file-icon"><Document /></el-icon>
                    <span>{{ row.original_name }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="格式" width="100" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="getFileTagType(getExt(row.filename))" effect="light" class="ext-tag">
                    {{ getExt(row.filename).toUpperCase() || '未知' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="文件大小" width="120">
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
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" type="primary" link :icon="View" @click="handlePreview(row)">预览</el-button>
                  <el-button size="small" type="success" link :icon="Download" @click="handleDownload(row)">下载</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <!-- 动态分类 Tabs -->
          <el-tab-pane
            v-for="cat in categories"
            :key="cat.id"
            :label="cat.name"
            :name="String(cat.id)"
          >
            <el-table 
              :data="getFilesByCategory(cat.id)" 
              style="width: 100%" 
              v-loading="loading"
              class="custom-table"
              :header-cell-style="{ background: '#F7F8FA', color: '#4E5969', fontWeight: '500' }"
            >
              <el-table-column prop="original_name" label="文件名称" min-width="250" show-overflow-tooltip>
                <template #default="{ row }">
                  <div class="file-name-cell">
                    <el-icon class="file-icon"><Document /></el-icon>
                    <span>{{ row.original_name }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="格式" width="100" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="getFileTagType(getExt(row.filename))" effect="light" class="ext-tag">
                    {{ getExt(row.filename).toUpperCase() || '未知' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="文件大小" width="120">
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
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" type="primary" link :icon="View" @click="handlePreview(row)">预览</el-button>
                  <el-button size="small" type="success" link :icon="Download" @click="handleDownload(row)">下载</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, View, Download } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const STATIC = '/static/'
const authStore = useAuthStore()

const categories = ref([])
const allFiles = ref([])
const loading = ref(false)
const activeTab = ref('all')

function fileSize(size) {
  return size < 1024
    ? size + ' B'
    : size < 1048576
      ? (size / 1024).toFixed(1) + ' KB'
      : (size / 1048576).toFixed(1) + ' MB'
}

function getExt(filename) {
  return filename ? filename.split('.').pop().toLowerCase() : ''
}

// 动态获取文件类型对应的标签颜色
function getFileTagType(ext) {
  if (['pdf'].includes(ext)) return 'danger'
  if (['xls', 'xlsx'].includes(ext)) return 'success'
  if (['ppt', 'pptx'].includes(ext)) return 'warning'
  if (['doc', 'docx'].includes(ext)) return 'primary'
  if (['zip', 'rar', '7z'].includes(ext)) return 'info'
  return 'info'
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
    ElMessage.info('该格式暂不支持在线预览，请直接下载')
  }
}

function handleDownload(row) {
  window.open(STATIC + row.filename + '?download=1', '_blank')
}

function getFilesByCategory(categoryId) {
  return allFiles.value.filter((f) => f.category_id === categoryId)
}

function handleTabChange() {
  // 可预留用于切换 Tab 时的数据统计或动画逻辑
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
  loading.value = true
  try {
    const res = await api.get('/api/resources')
    allFiles.value = res.data
  } catch {
    ElMessage.error('加载文件列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadCategories()
  loadFiles()
})
</script>

<style scoped>
/* 容器与卡片 */
.resource-download-container {
  padding: 0;
}

.page-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  min-height: calc(100vh - 120px);
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

/* Tabs 美化 */
.tabs-wrapper {
  margin-top: 10px;
}

:deep(.modern-tabs .el-tabs__item) {
  font-size: 15px;
  padding: 0 24px;
  height: 48px;
  line-height: 48px;
}

:deep(.modern-tabs .el-tabs__nav-wrap::after) {
  height: 1px;
  background-color: #E5E6EB;
}

/* 表格内文字与样式优化 */
.file-name-cell {
  display: flex;
  align-items: center;
  color: #1D2129;
  font-weight: 500;
}

.file-icon {
  margin-right: 8px;
  color: #165DFF;
  font-size: 18px;
}

.ext-tag {
  font-weight: 600;
  border-radius: 4px;
  width: 50px;
  text-align: center;
}

.sub-text {
  color: #86909C;
  font-size: 13px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* 去除表格自带底边框 */
:deep(.custom-table::before) {
  display: none;
}
</style>