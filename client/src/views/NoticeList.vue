<template>
  <div class="notice-manage-container">
    <el-card class="page-card" shadow="never">
      <div class="page-header">
        <div class="header-left">
          <div class="title-indicator"></div>
          <h3 class="page-title">通知公告</h3>
        </div>
        <el-button v-if="authStore.isAdmin" type="primary" :icon="Plus" @click="openCreateDialog" class="create-btn">
          发布新通知
        </el-button>
      </div>

      <div class="collection-toolbar notice-category-filter"><label for="notice-category">公告分类</label><select id="notice-category" v-model="selectedCategory" class="category-filter"><option value="">全部分类</option><option v-for="category in categories" :key="category" :value="category">{{ category }}</option></select><span>{{ filteredNotices.length }} 条公告</span></div>

      <el-table 
        v-if="!isMobile"
        :data="filteredNotices"
        style="width: 100%" 
        v-loading="loading"
        class="custom-table"
        :header-cell-style="{ background: '#F7F8FA', color: '#4E5969', fontWeight: '500' }"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-preview">
              <div class="preview-label"><el-icon><ChatLineSquare /></el-icon> 内容速览</div>
              <RichContent class="preview-content" :content="row.content" />
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="title" label="公告标题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="notice-title">{{ row.title }}</span>
            <el-tag size="small" effect="plain" class="notice-category-tag">{{ row.category || '未分类' }}</el-tag>
            <el-tag v-if="row.is_urgent" type="danger" size="small" effect="dark" class="urgent-tag">紧急</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="author_name" label="发布人" min-width="160">
          <template #default="{ row }">
            <div class="author-cell">
              <el-avatar :size="24" class="author-avatar">{{ (row.author_name || 'U').charAt(0) }}</el-avatar>
              <span>{{ row.author_name || '管理员' }}</span>
              <span v-if="row.author_qq" class="author-qq">QQ:{{ row.author_qq }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="发布时间" min-width="160">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" type="primary" link :icon="View" @click="openViewDialog(row)">详细阅读</el-button>
              <template v-if="authStore.isAdmin">
                <el-button size="small" type="primary" link :icon="EditPen" @click="openEditDialog(row)">编辑</el-button>
                <el-button size="small" type="success" link :icon="Message" :loading="sendingId === row.id" @click="handleSendEmail(row)">邮件</el-button>
                <el-button size="small" type="warning" link :icon="ChatDotSquare" :loading="qqNotifySendingId === row.id" @click="handleQQNotify(row)">QQ群</el-button>
                <el-button size="small" type="danger" link :icon="Delete" @click="handleDelete(row)">删除</el-button>
              </template>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-list" v-loading="loading">
        <el-card v-for="row in filteredNotices" :key="row.id" class="mobile-notice-card" shadow="sm">
          <div class="card-header">
            <span class="mobile-notice-title">{{ row.title }}</span>
            <el-tag size="small" effect="plain">{{ row.category || '未分类' }}</el-tag>
            <el-tag v-if="row.is_urgent" type="danger" size="small" effect="dark" class="urgent-tag mobile-urgent-tag">紧急</el-tag>
          </div>
          <div class="card-body">
            <div class="meta-info">
              <div class="author-cell">
                <el-avatar :size="20" class="author-avatar">{{ (row.author_name || 'U').charAt(0) }}</el-avatar>
                <span>{{ row.author_name || '管理员' }}</span>
                <span v-if="row.author_qq" class="author-qq">QQ:{{ row.author_qq }}</span>
              </div>
              <span class="time-text">{{ formatTime(row.created_at) }}</span>
            </div>
            <RichContent class="preview-content-mobile" :content="row.content" />
          </div>
          <div class="card-footer" :class="{'admin-footer': authStore.isAdmin}">
            <el-button size="small" type="primary" plain :icon="View" @click="openViewDialog(row)">详细阅读</el-button>
            <template v-if="authStore.isAdmin">
              <el-button size="small" type="info" plain :icon="EditPen" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" type="success" plain :icon="Message" :loading="sendingId === row.id" @click="handleSendEmail(row)">邮件</el-button>
              <el-button size="small" type="warning" plain :icon="ChatDotSquare" :loading="qqNotifySendingId === row.id" @click="handleQQNotify(row)">QQ群</el-button>
              <el-button size="small" type="danger" plain :icon="Delete" @click="handleDelete(row)">删除</el-button>
            </template>
          </div>
        </el-card>
        <el-empty v-if="filteredNotices.length === 0" description="该分类暂无通知公告" />
      </div>
    </el-card>

    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑通知公告' : '发布新通知'" 
      :width="isMobile ? '100%' : '650px'" 
      :fullscreen="isMobile"
      class="modern-dialog flex-dialog" 
      destroy-on-close
    >
      <div class="dialog-scroll-body">
        <el-form :model="noticeForm" label-position="top" size="large">
          <el-form-item label="公告标题">
            <el-input v-model="noticeForm.title" placeholder="请输入通知标题，建议言简意赅" />
          </el-form-item>
          <el-form-item label="公告正文">
            <RichEditor v-model="noticeForm.content" @uploading="attachmentsUploading = $event" />
          </el-form-item>
          <el-form-item label="公告分类"><el-select v-model="noticeForm.category" filterable allow-create default-first-option placeholder="选择已有分类或输入新分类" style="width:100%"><el-option v-for="category in categories" :key="category" :label="category" :value="category" /></el-select><span class="category-hint">可输入新分类，最长 30 个字；历史公告默认未分类。</span></el-form-item>
          <el-form-item v-if="authStore.isAdmin">
            <el-checkbox v-model="noticeForm.is_urgent" class="urgent-checkbox">
              <span class="urgent-label">设为紧急通知</span>
              <span class="urgent-hint">（仅能存在一条紧急，设置后其他将自动取消）</span>
            </el-checkbox>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :icon="Position" :disabled="attachmentsUploading" @click="handleSubmit">{{ attachmentsUploading ? '附件上传中…' : (isEdit ? '保存修改' : '立即发布') }}</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog 
      v-model="viewDialogVisible" 
      title="公告详情" 
      :width="isMobile ? '100%' : '700px'" 
      :fullscreen="isMobile"
      class="modern-dialog flex-dialog article-dialog"
    >
      <div class="dialog-scroll-body">
        <div class="article-header">
          <h2 class="article-title">{{ viewNotice.title }}</h2>
          <div class="article-meta">
            <el-tag effect="plain">{{ viewNotice.category || '未分类' }}</el-tag>
            <span class="meta-item"><el-icon><User /></el-icon> {{ viewNotice.author_name || '管理员' }}<template v-if="viewNotice.author_qq"> (QQ:{{ viewNotice.author_qq }})</template></span>
            <span class="meta-item"><el-icon><Calendar /></el-icon> {{ formatTime(viewNotice.created_at) }}</span>
          </div>
        </div>
        
        <el-divider border-style="dashed" class="article-divider" />
        
        <RichContent class="article-content" :content="viewNotice.content" />
      </div>
      
      <template #footer>
        <div class="dialog-footer center-footer">
          <el-button type="primary" plain @click="viewDialogVisible = false" class="read-btn">已阅 / 关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, View, EditPen, Delete, ChatLineSquare, Position, User, Calendar, Message, ChatDotSquare } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const authStore = useAuthStore()
const notices = ref([])
const selectedCategory=ref('')
const attachmentsUploading=ref(false)
const categories=computed(()=>Array.from(new Set(['未分类','班级通知','学习课程','活动安排','资料文件',...notices.value.map(item=>item.category||'未分类')])).sort((a,b)=>a.localeCompare(b,'zh-CN')))
const filteredNotices=computed(()=>notices.value.filter(item=>!selectedCategory.value||(item.category||'未分类')===selectedCategory.value))
const loading = ref(false)

// 响应式状态
const isMobile = ref(false)

// 弹窗状态
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const viewDialogVisible = ref(false)

// 数据绑定
const viewNotice = reactive({ title: '', content: '', author_name: '', created_at: '', category:'未分类' })
const noticeForm = reactive({ title: '', content: '', is_urgent: false, category:'未分类' })
const sendingId = ref(null)
const qqNotifySendingId = ref(null)

// 监听窗口尺寸
const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  loadNotices()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', checkMobile)
})

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', { 
    year: 'numeric', month: '2-digit', day: '2-digit', 
    hour: '2-digit', minute: '2-digit' 
  })
}

async function loadNotices() {
  loading.value = true
  try {
    const res = await api.get('/api/notices')
    notices.value = res.data
  } catch {
    ElMessage.error('加载通知失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  isEdit.value = false
  editId.value = null
  noticeForm.title = ''
  noticeForm.content = ''
  noticeForm.is_urgent = false
  noticeForm.category = selectedCategory.value || '未分类'
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  editId.value = row.id
  noticeForm.title = row.title
  noticeForm.content = row.content
  noticeForm.is_urgent = row.is_urgent || false
  noticeForm.category = row.category || '未分类'
  dialogVisible.value = true
}

function openViewDialog(row) {
  viewNotice.category=row.category||'未分类'
  viewNotice.title = row.title
  viewNotice.content = row.content
  viewNotice.author_name = row.author_name
  viewNotice.created_at = row.created_at
  viewDialogVisible.value = true
}

async function handleSubmit() {
  if(noticeForm.category.length>30)return ElMessage.warning('分类最长 30 个字')
  if (!noticeForm.title.trim() || !noticeForm.content.trim()) {
    return ElMessage.warning('标题和内容均不能为空')
  }

  try {
    if (isEdit.value) {
      await api.put(`/api/notices/${editId.value}`, noticeForm)
      ElMessage.success('通知修改成功')
    } else {
      await api.post('/api/notices', noticeForm)
      ElMessage.success('公告发布成功')
    }
    dialogVisible.value = false
    loadNotices()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除公告 "${row.title}" 吗？此操作不可撤销。`, '删除确认', { 
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning' 
    })
    await api.delete(`/api/notices/${row.id}`)
    ElMessage.success('删除成功')
    loadNotices()
  } catch {}
}

async function handleSendEmail(row) {
  try {
    await ElMessageBox.confirm(`确定要向全班学生发送邮件通知 "${row.title}" 吗？`, '邮件通知确认', {
      confirmButtonText: '发送',
      cancelButtonText: '取消',
      type: 'info'
    })
    sendingId.value = row.id
    const res = await api.post(`/api/notices/${row.id}/send-email`)
    const d = res.data.detail || {}
    if (d.success) {
      ElMessage.success(`邮件已发送: 成功 ${d.sent} 人，失败 ${d.failed} 人`)
    } else {
      ElMessage.error(d.detail || '发送失败')
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.detail || '邮件发送失败，请检查 SMTP 配置')
    }
  } finally {
    sendingId.value = null
  }
}

async function handleQQNotify(row) {
  try {
    await ElMessageBox.confirm(`确定向 QQ 群发送公告「${row.title}」的通知吗？`, 'QQ群通知确认', {
      confirmButtonText: '发送', cancelButtonText: '取消', type: 'warning'
    })
  } catch { return }
  qqNotifySendingId.value = row.id
  try {
    const res = await api.post(`/api/qq/notice/${row.id}/notify`)
    ElMessage.success(res.data.message || 'QQ群通知已发送')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  } finally {
    qqNotifySendingId.value = null
  }
}
</script>

<style scoped>
/* 容器与卡片基底 */
.notice-manage-container {
  padding: 0;
}

.page-card {
  border: none;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  min-height: calc(100vh - 120px);
}

/* 顶部操作区 */
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

/* ================= 移动端卡片视图 ================= */
.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mobile-notice-card {
  border-radius: 8px;
  border: 1px solid #E5E6EB;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}

.mobile-notice-title {
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 15px;
  line-height: 1.4;
  word-break: break-all;
  flex: 1;
}

.mobile-urgent-tag {
  flex-shrink: 0;
  margin-top: 2px;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.meta-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-content-mobile {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: pre-wrap;
  background-color: var(--surface-soft);
  padding: 10px 12px;
  border-radius: 6px;
}

.card-footer {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #F2F3F5;
  display: flex;
}

.admin-footer {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
  gap: 8px;
}

.card-footer .el-button {
  margin-left: 0 !important;
  width: 100%;
}

/* ================= PC端视图样式 ================= */
.notice-title {
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 15px;
}

.urgent-tag {
  margin-left: 8px;
  vertical-align: middle;
}

.urgent-checkbox {
  margin-top: 8px;
  align-items: flex-start;
}

.urgent-label {
  font-weight: 600;
  color: #F53F3F;
}

.urgent-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-left: 4px;
}

.author-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.author-avatar {
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: bold;
}

.author-qq {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-left: 4px;
}

.time-text {
  color: var(--el-text-color-secondary);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 13px;
}

/* 操作列按钮容器 */
.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.action-buttons .el-button {
  margin-left: 0 !important;
}

/* 展开行（速览块）美化 */
.expand-preview {
  margin: 8px 32px 8px 50px;
  padding: 16px 24px;
  background-color: var(--surface-soft);
  border-left: 4px solid #165DFF;
  border-radius: 0 6px 6px 0;
}

.preview-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-color-primary);
  margin-bottom: 8px;
}

.preview-content {
  white-space: pre-wrap;
  line-height: 1.8;
  color: var(--el-text-color-regular);
  font-size: 14px;
}

/* 表单输入框焦点高亮 */
:deep(.el-input__wrapper.is-focus),
:deep(.custom-textarea .el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px #165DFF inset !important;
}
:deep(.custom-textarea .el-textarea__inner) {
  padding: 12px 16px;
  background-color: var(--surface-soft);
}

/* 阅读详情与通用弹窗优化 */
:deep(.flex-dialog) {
  display: flex;
  flex-direction: column;
}

:deep(.flex-dialog .el-dialog__body) {
  flex: 1;
  overflow: hidden;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.dialog-scroll-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.article-header {
  text-align: center;
}

.article-title {
  margin: 0 0 16px 0;
  font-size: 22px;
  color: var(--el-text-color-primary);
  line-height: 1.4;
  word-break: break-all;
}

.article-meta {
  display: flex;
  justify-content: center;
  gap: 24px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.article-divider {
  margin: 20px 0;
  border-color: #E5E6EB;
}

.article-content {
  white-space: pre-wrap;
  line-height: 1.8;
  color: var(--el-text-color-primary);
  font-size: 15px;
  padding: 0 8px;
  min-height: 150px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 0 4px;
}

.center-footer {
  justify-content: center;
}

/* 去除表格底边框 */
:deep(.custom-table::before) {
  display: none;
}

/* ================= 移动端适配响应式微调 ================= */
@media (max-width: 768px) {
  /* 顶部操作区堆叠 */
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .create-btn {
    width: 100%;
  }

  /* 弹窗底部按钮在手机上均分宽度 */
  .dialog-footer {
    justify-content: space-between;
  }
  .dialog-footer .el-button {
    flex: 1;
    margin-left: 0 !important;
  }
  .read-btn {
    width: 100% !important;
  }

  /* 移除弹窗在手机上的 margin，彻底融入全屏 */
  :deep(.modern-dialog) {
    margin: 0 !important;
    height: 100vh !important;
  }
  
  .dialog-scroll-body {
    padding: 16px 15px;
  }

  /* 紧急提示文字换行规避 */
  .urgent-checkbox {
    white-space: normal;
    height: auto;
  }
  .urgent-hint {
    display: block;
    margin-left: 0;
    margin-top: 4px;
  }

  /* 文章元数据堆叠 */
  .article-meta {
    flex-direction: column;
    gap: 8px;
    align-items: center;
  }
}
</style>
