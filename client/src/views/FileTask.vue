<template>
  <div class="file-task-container">
    <el-card class="page-card" shadow="never">
      <div class="page-header">
        <div class="header-left">
          <div class="title-indicator"></div>
          <h3 class="page-title">文件任务管理</h3>
        </div>
        <div class="header-actions">
          <el-button v-if="authStore.canViewAllData" type="primary" :icon="Plus" @click="openCreateDialog" class="action-btn">
            发布新任务
          </el-button>
          <el-button v-if="authStore.canViewAllData" type="success" :icon="Download" @click="openDownloadAllZip" class="action-btn">
            打包全部
          </el-button>
        </div>
      </div>

      <div class="task-overview">
        <div><span class="overview-label">文件收集</span><strong>{{ activeTaskCount }} 项进行中</strong><p>统一命名，有序收阅。上传的原文件会在下载时自动整理。</p></div>
        <div class="overview-metric"><strong>{{ tasks.length }}</strong><span>全部任务</span></div>
      </div>
      <div class="collection-toolbar">
        <el-input v-model="search" placeholder="搜索任务标题" clearable aria-label="搜索文件任务" />
        <el-radio-group v-model="statusFilter" aria-label="任务状态"><el-radio-button value="all">全部</el-radio-button><el-radio-button value="active">进行中</el-radio-button><el-radio-button value="expired">已截止</el-radio-button></el-radio-group>
        <span>{{ filteredTasks.length }} 项任务</span>
      </div>
      <el-table 
        v-if="!isMobile"
        :data="filteredTasks"
        style="width: 100%" 
        v-loading="loading"
        class="custom-table"
        :header-cell-style="{ background: '#F7F8FA', color: '#4E5969', fontWeight: '500' }"
      >
        <el-table-column prop="title" label="任务标题" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="task-title">{{ row.title }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="description" label="任务描述" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <RichContent class="task-desc" :content="row.description || '暂无描述'" />
          </template>
        </el-table-column>
        
        <el-table-column label="截止时间" min-width="160">
          <template #default="{ row }">
            <div class="deadline-cell">
              <el-icon class="deadline-icon" :class="{ 'is-expired': isExpired(row.deadline) }">
                <Timer />
              </el-icon>
              <span :class="{ 'is-expired-text': isExpired(row.deadline) }">
                {{ formatTime(row.deadline) }}
              </span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="submission_count" label="提交进度" min-width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="success" effect="light" round>
              {{ row.submission_count || 0 }} 份已交
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="author_name" label="发布人" min-width="140">
          <template #default="{ row }">
            <span>{{ row.author_name || '管理员' }}</span>
            <span v-if="row.author_qq" class="author-qq">QQ:{{ row.author_qq }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" type="primary" link :icon="View" @click="openDetailDialog(row)">详情收阅</el-button>
              <el-button v-if="!authStore.canViewAllData" size="small" type="success" link :icon="Upload" :disabled="isExpired(row.deadline)" @click="openSubmitDialog(row)">
                提交文件
              </el-button>
              <template v-if="authStore.canViewAllData">
                <el-button size="small" type="primary" link :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
                <el-button size="small" type="danger" link :icon="Delete" @click="handleDelete(row)">删除</el-button>
              </template>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-list" v-loading="loading">
        <el-card v-for="row in filteredTasks" :key="row.id" class="mobile-task-card" shadow="never">
          <div class="card-header">
            <span class="task-title">{{ row.title }}</span>
            <el-tag size="small" type="success" effect="light" round>{{ row.submission_count || 0 }} 份</el-tag>
          </div>
          <div class="card-body">
            <RichContent class="task-desc" :content="row.description || '暂无描述'" />
            <div class="meta-info">
              <span class="deadline" :class="{ 'is-expired-text': isExpired(row.deadline) }">
                <el-icon><Timer /></el-icon> {{ formatTime(row.deadline) }}
              </span>
              <span class="author">
                <el-icon><User /></el-icon> {{ row.author_name }}
                <span v-if="row.author_qq" class="author-qq">QQ:{{ row.author_qq }}</span>
              </span>
            </div>
          </div>
          <div class="card-footer">
            <el-button size="small" type="primary" plain :icon="View" @click="openDetailDialog(row)">详情</el-button>
            <el-button v-if="!authStore.canViewAllData" size="small" type="success" plain :icon="Upload" :disabled="isExpired(row.deadline)" @click="openSubmitDialog(row)">提交</el-button>
            <template v-if="authStore.canViewAllData">
              <el-button size="small" type="primary" plain :icon="Edit" @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" plain :icon="Delete" @click="handleDelete(row)">删除</el-button>
            </template>
          </div>
        </el-card>
        <el-empty v-if="filteredTasks.length === 0" description="暂无匹配的文件任务" />
      </div>
    </el-card>

    <el-dialog 
      v-model="detailVisible" 
      title="任务详情与收阅" 
      :width="isMobile ? '100%' : '750px'" 
      :fullscreen="isMobile"
      class="modern-dialog"
    >
      <template v-if="detailTask">
        <div class="task-detail-header">
          <h2 class="detail-title">{{ detailTask.title }}</h2>
          <div class="detail-meta">
            <span class="meta-item"><el-icon><Timer /></el-icon> 截止：{{ formatTime(detailTask.deadline) }}</span>
            <span class="meta-item"><el-icon><User /></el-icon> 发布人：{{ detailTask.author_name || '管理员' }}<template v-if="detailTask.author_qq"> (QQ:{{ detailTask.author_qq }})</template></span>
          </div>
          <RichContent class="detail-desc" :content="detailTask.description || '暂无详细描述'" />
        </div>
        
        <div class="submission-section">
          <div class="section-header-row">
            <span class="section-title">提交记录明细</span>
            <div class="action-buttons responsive-actions">
              <el-button v-if="authStore.canViewAllData" size="small" type="warning" plain :icon="ChatDotSquare" :loading="qqNotifyLoading" @click="handleQQNotify">
                QQ提醒
              </el-button>
              <el-button v-if="authStore.canViewAllData && submissions.length > 0" size="small" type="success" :icon="Download" @click="openDownloadZip">
                打包下载全部
              </el-button>
            </div>
          </div>
          
          <el-table 
            v-if="!isMobile"
            :data="groupedSubmissions" 
            style="width: 100%" 
            v-loading="subLoading" 
            size="small"
            row-key="student_id"
            class="submission-table"
            :header-cell-style="{ background: '#F7F8FA', color: '#4E5969' }"
          >
            <el-table-column type="expand">
              <template #default="{ row }">
                <div v-for="file in row.files" :key="file.id" class="sub-file-item">
                  <div class="file-info">
                    <el-icon><Document /></el-icon>
                    <span class="file-name">{{ file.original_name || file.file_path }}</span>
                  </div>
                  <div class="file-actions">
                    <span class="time-text">{{ formatTime(file.submitted_at) }}</span>
                    <el-button v-if="file.file_path" type="primary" link size="small" :icon="Download" @click="downloadFile(file)">下载</el-button>
                    <el-button v-if="authStore.canViewAllData || file.student_id === authStore.user?.id" type="danger" link size="small" :icon="Delete" @click="handleDeleteSubmission(file.id)">删除</el-button>
                  </div>
                </div>
                <div v-if="!row.files.length" class="empty-text" style="padding: 10px;">无文件记录</div>
              </template>
            </el-table-column>
            <el-table-column prop="student_name" label="姓名" min-width="90" />
            <el-table-column prop="student_student_id" label="学号" min-width="110">
              <template #default="{ row }">
                <span class="id-text">{{ row.student_student_id }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="latest_time" label="最新提交" min-width="140">
              <template #default="{ row }">
                <span class="time-text">{{ row.latest_time }}</span>
              </template>
            </el-table-column>
            <el-table-column label="文件数" width="80" align="center">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.file_count }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" align="center" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.files.length" type="primary" link size="small" :icon="Download" @click="downloadStudentZip(row)">打包</el-button>
                <el-button v-if="authStore.canViewAllData || row.student_id === authStore.user?.id" type="danger" link size="small" :icon="Delete" @click="handleDeleteStudentSubmissions(row)">清空</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div v-else class="mobile-sub-list" v-loading="subLoading">
            <div v-for="row in groupedSubmissions" :key="row.student_id" class="mobile-sub-card">
              <div class="mobile-sub-header" @click="toggleMobileExpand(row.student_id)">
                <div class="sub-main">
                  <div class="sub-name">{{ row.student_name }} <span class="sub-id">({{ row.student_student_id }})</span></div>
                  <div class="sub-time">{{ row.latest_time }} / {{ row.file_count }} 个文件</div>
                </div>
                <el-icon class="expand-icon" :class="{ 'is-expanded': expandedMobile[row.student_id] }">
                  <ArrowRight />
                </el-icon>
              </div>
              <el-collapse-transition>
                <div v-show="expandedMobile[row.student_id]" class="sub-files-list">
                  <div v-if="row.files.length" style="margin-bottom: 8px;">
                    <el-button type="primary" size="small" plain :icon="Download" @click.stop="downloadStudentZip(row)">打包下载全部文件</el-button>
                  </div>
                  <div v-for="file in row.files" :key="file.id" class="sub-file-item-mobile">
                    <div class="file-info-mobile">
                      <el-icon class="file-icon"><Document /></el-icon>
                      <span class="file-name">{{ file.original_name || file.file_path }}</span>
                    </div>
                    <div class="file-actions-mobile">
                      <span class="time-text">{{ formatTime(file.submitted_at) }}</span>
                      <div class="file-btns">
                        <el-button v-if="file.file_path" type="primary" size="small" plain @click.stop="downloadFile(file)">下载</el-button>
                        <el-button v-if="authStore.canViewAllData || file.student_id === authStore.user?.id" type="danger" size="small" plain @click.stop="handleDeleteSubmission(file.id)">删除</el-button>
                      </div>
                    </div>
                  </div>
                </div>
              </el-collapse-transition>
            </div>
            <div v-if="groupedSubmissions.length === 0" class="empty-text" style="text-align: center; padding: 10px 0;">暂无人提交</div>
          </div>

          <div v-if="authStore.canViewAllData" class="unsubmit-section">
            <el-divider border-style="dashed" />
            <div class="section-header-row">
              <span class="section-title">未提交名单</span>
              <div class="action-buttons responsive-actions">
                <el-button size="small" @click="loadUnsubmitted">刷新名单</el-button>
                <el-button size="small" type="warning" plain :icon="Message" :loading="sendingReminder" @click="handleSendReminder">
                  邮件提醒
                </el-button>
                <el-button size="small" type="primary" plain :icon="ChatDotSquare" :loading="qqRemindLoading" @click="handleQQRemind">
                  私聊提醒
                </el-button>
              </div>
            </div>
            <div v-if="unsubmittedList.length === 0" class="empty-hint-box">
              {{ unsubmittedLoaded ? '🎉 全部学生均已按时提交' : '点击“刷新名单”查询最新进度' }}
            </div>
            
            <el-table v-else-if="!isMobile" :data="unsubmittedList" size="small" class="submission-table" max-height="300">
              <el-table-column prop="real_name" label="姓名" min-width="100"/>
              <el-table-column prop="student_id" label="学号" min-width="120"/>
            </el-table>

            <div v-else class="mobile-unsub-tags">
              <el-tag 
                v-for="row in unsubmittedList" 
                :key="row.student_id" 
                type="info" 
                effect="plain"
                class="unsub-tag"
              >
                {{ row.real_name }} ({{ row.student_id }})
              </el-tag>
            </div>
          </div>
        </div>
      </template>
      <template #footer v-if="isMobile">
        <el-button @click="detailVisible = false" style="width: 100%;">关闭详情</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="downloadVisible"
      title="打包下载"
      :width="isMobile ? '100%' : '420px'"
      :fullscreen="isMobile"
      :close-on-click-modal="!downloadBusy"
      :close-on-press-escape="!downloadBusy"
      :show-close="!downloadBusy"
      destroy-on-close
    >
      <template v-if="!downloadBusy">
        <el-alert title="一次下载完整 ZIP，进度显示在浏览器下载列表。" type="info" :closable="false" style="margin-bottom:16px" />
        <p class="download-explanation">所有下载共享有限带宽。大文件需要较长时间，支持断点续传，请保留下载链接并保持网络连接。</p>
        <p>选择压缩包内的文件夹结构：</p>
        <el-radio-group v-model="downloadStructure" style="display:flex;flex-direction:column;gap:8px;">
          <el-radio value="per_student">每个人一个文件夹</el-radio>
          <el-radio value="flat">全部人一个文件夹</el-radio>
        </el-radio-group>
      </template>
      <template v-else>
        <div class="download-preparing" v-loading="downloadBusy">
          <p>正在检查文件并准备下载地址…</p>
        </div>
      </template>
      <template #footer>
        <div style="display:flex;justify-content:flex-end;gap:8px;">
          <el-button v-if="!downloadBusy" @click="downloadVisible = false">取消</el-button>
          <el-button v-if="!downloadBusy" type="primary" @click="startBatchDownload">下载完整 ZIP</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="submitVisible"
      title="提交任务附件" 
      :width="isMobile ? '100%' : '550px'" 
      :fullscreen="isMobile"
      class="modern-dialog" 
      destroy-on-close
    >
      <template v-if="submitTask">
        <div class="submit-task-info">
          <div class="info-row"><strong>对应任务：</strong>{{ submitTask.title }}</div>
          <div class="info-row">
            <strong>截止时间：</strong>
            <span :class="{ 'is-expired-text': isExpired(submitTask.deadline) }">{{ formatTime(submitTask.deadline) }}</span>
          </div>
        </div>

        <el-upload
          ref="uploadRef"
          class="drag-upload"
          drag
          multiple
          accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.zip,.rar,.jpg,.jpeg,.png,.gif,.webp"
          :auto-upload="false"
          :disabled="uploading"
          :on-change="handleFileChange"
          :on-remove="handleFileChange"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处，或 <em>点击浏览</em>
          </div>
          <template #tip>
            <div class="el-upload__tip" style="line-height: 1.5;">支持 PDF、图片、Word、PPT 等格式，每次最多 20 个文件、合计 100 MiB。重新提交将替换本任务的全部旧文件。</div>
          </template>
        </el-upload>

        <div v-if="uploading" class="upload-progress-wrapper">
          <el-progress :percentage="uploadPercent" :stroke-width="8" :color="progressColor" :status="uploadPercent === 100 ? 'success' : ''">
            <span class="progress-text">{{ uploadPercent }}%</span>
          </el-progress>
          <p class="progress-hint">正在安全上传，请勿关闭页面…</p>
        </div>
      </template>
      <template #footer>
        <div class="dialog-footer">
          <el-button :disabled="uploading" @click="submitVisible = false">取消</el-button>
          <el-button type="primary" :icon="Upload" :loading="uploading" :disabled="selectedFiles.length === 0" @click="handleSubmitFile">确认提交</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog 
      v-model="createVisible" 
      :title="editingTask ? '编辑任务' : '发布新任务'" 
      :width="isMobile ? '100%' : '680px'"
      :fullscreen="isMobile"
      class="modern-dialog" 
      destroy-on-close
    >
      <el-form :model="createForm" label-position="top" size="large">
        <el-form-item label="任务标题">
          <el-input v-model="createForm.title" placeholder="例如：期中考试总结报告" />
        </el-form-item>
        <el-form-item label="截止日期与时间（必填）">
          <el-date-picker 
            v-model="createForm.deadline" 
            type="datetime" 
            style="width: 100%"
            value-format="YYYY-MM-DD HH:mm:ss" 
            placeholder="请选择截止时间"
            :editable="false"
          />
        </el-form-item>
        <el-form-item label="任务详细描述 (选填)">
          <RichEditor v-model="createForm.description" />
        </el-form-item>
        <el-form-item label="关联小组项目">
          <el-select v-model="createForm.group_project_id" placeholder="可选：关联小组作业" clearable style="width: 100%"
          >
            <el-option v-for="gp in groupProjects" :key="gp.id" :label="gp.name" :value="gp.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="文件命名规则">
          <FileNamingRule ref="namingRuleRef" v-model="createForm.naming_pattern" :group-enabled="!!createForm.group_project_id"
            :task-title="createForm.title" :task-date="editingTask?.created_at" />
        </el-form-item>

      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="createVisible = false">取消</el-button>
          <el-button type="primary" :loading="creating" @click="handleCreate">{{ editingTask ? '保存修改' : '确认发布' }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, View, Upload, UploadFilled, Delete, Timer, User, Download, Edit, Message, Document, ArrowRight, ChatDotSquare } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'
import { browserDownload } from '../utils/download'
import FileNamingRule from '../components/FileNamingRule.vue'
import { showMailResult } from '../utils/notifications'

const authStore = useAuthStore()
const isMobile = ref(window.innerWidth < 768)

// 任务列表
const tasks = ref([])
const loading = ref(false)
const search = ref('')
const statusFilter = ref('all')
const namingRuleRef = ref(null)
const filteredTasks = computed(() => tasks.value.filter(task =>
  task.title.toLowerCase().includes(search.value.trim().toLowerCase()) &&
  (statusFilter.value === 'all' || (statusFilter.value === 'expired' ? isExpired(task.deadline) : !isExpired(task.deadline)))))
const activeTaskCount = computed(() => tasks.value.filter(task => !isExpired(task.deadline)).length)

// 创建/编辑
const createVisible = ref(false)
const creating = ref(false)
const editingTask = ref(null)
const createForm = reactive({
  title: '',
  description: '',
  naming_pattern: '{sid}-{name}-{seq}-{orig}',
  deadline: '',
  group_project_id: null,
})

// 小组项目列表
const groupProjects = ref([])

async function loadGroupProjects() {
  try {
    const res = await api.get('/api/group-projects')
    groupProjects.value = res.data
  } catch { /* ignore */ }
}

// 提交弹窗
const submitVisible = ref(false)
const submitTask = ref(null)
const uploadRef = ref(null)
const uploading = ref(false)
const uploadPercent = ref(0)
const selectedFiles = ref([])

const progressColor = computed(() => {
  if (uploadPercent.value === 100) return '#22C55E'
  return '#165DFF'
})

// 详情弹窗
const detailVisible = ref(false)
const detailTask = ref(null)
const detailActiveTab = ref('submissions')
const submissions = ref([])
const unsubmittedList = ref([])
const unsubmittedLoaded = ref(false)
const sendingReminder = ref(false)
const qqNotifyLoading = ref(false)
const qqRemindLoading = ref(false)
const expandedRows = ref([])
const expandedMobile = ref({})
const subLoading = ref(false)

// 下载（分批 + 进度）
const downloadStructure = ref('per_student')
const downloadVisible = ref(false)
const downloadBusy = ref(false)
const downloadScope = ref(null) // { taskId: number|null, baseName: string }

const groupedSubmissions = computed(() => {
  const map = new Map()
  for (const s of submissions.value) {
    if (!map.has(s.student_id)) {
      map.set(s.student_id, {
        ...s,
        files: [],
        file_count: 0,
        latest_time: s.submitted_at,
      })
    }
    const entry = map.get(s.student_id)
    entry.files.push(s)
    entry.file_count = entry.files.length
    if (s.submitted_at > entry.latest_time) entry.latest_time = s.submitted_at
  }
  return Array.from(map.values())
})

const now = ref(Date.now())
let timer = null

function formatTime(t) {
  if (!t) return '无限制'
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function isExpired(deadline) {
  if (!deadline) return false
  return now.value > new Date(deadline).getTime()
}

function isDesktop() { return window.innerWidth >= 768 }

async function loadTasks() {
  loading.value = true
  try {
    const res = await api.get('/api/file-tasks')
    tasks.value = res.data
  } catch { ElMessage.error('加载任务失败') }
  finally { loading.value = false }
}

function openCreateDialog() {
  editingTask.value = null
  createForm.title = ''
  createForm.description = ''
  createForm.naming_pattern = '{sid}-{name}-{seq}-{orig}'
  createForm.deadline = ''
  createForm.group_project_id = null
  createVisible.value = true
}

function openEditDialog(task) {
  editingTask.value = task
  createForm.title = task.title
  createForm.description = task.description
  createForm.naming_pattern = task.naming_pattern
  createForm.deadline = task.deadline ? task.deadline.replace('T', ' ').slice(0, 19) : ''
  createForm.group_project_id = task.group_project_id || null
  createVisible.value = true
}

async function handleCreate() {
  if (!createForm.title.trim()) return ElMessage.warning('请输入任务标题')
  if (!createForm.deadline) return ElMessage.warning('请选择截止时间')
  if (namingRuleRef.value?.patternError) return ElMessage.warning(namingRuleRef.value.patternError)
  if (creating.value) return
  const payload = { ...createForm }
  payload.deadline = payload.deadline.replace('T', ' ')
  if (payload.deadline.length === 16) payload.deadline += ':00'
  creating.value = true
  try {
    if (editingTask.value) {
      await api.put(`/api/file-tasks/${editingTask.value.id}`, payload)
      ElMessage.success('任务已更新')
    } else {
      await api.post('/api/file-tasks', payload)
      ElMessage.success('任务已创建')
    }
    createVisible.value = false
    loadTasks()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  } finally { creating.value = false }
}

async function handleDelete(task) {
  try {
    await ElMessageBox.confirm(`确定删除任务「${task.title}」吗？`, '删除确认', { type: 'warning' })
    await api.delete(`/api/file-tasks/${task.id}`)
    ElMessage.success('任务已删除')
    loadTasks()
  } catch { /* cancelled */ }
}

function openSubmitDialog(task) {
  submitTask.value = task
  selectedFiles.value = []
  uploadPercent.value = 0
  submitVisible.value = true
}

function handleFileChange(file, fileList) {
  selectedFiles.value = fileList.map(f => f.raw).filter(Boolean)
}

async function handleSubmitFile() {
  if (uploading.value) return
  if (selectedFiles.value.length === 0) return ElMessage.warning('请选择需要上传的文件')
  if (selectedFiles.value.length > 20) return ElMessage.warning('每次最多提交 20 个文件')
  if (selectedFiles.value.reduce((total, file) => total + file.size, 0) > 100 * 1024 * 1024) return ElMessage.warning('本次文件合计超过 100 MiB，请压缩后提交')
  uploading.value = true
  uploadPercent.value = 0
  const formData = new FormData()
  for (const f of selectedFiles.value) { formData.append('files', f) }
  try {
    const res = await api.post(`/api/file-tasks/${submitTask.value.id}/submit`, formData, {
      timeout: 0,
      onUploadProgress(progressEvent) {
        if (progressEvent.total) {
          uploadPercent.value = Math.round((progressEvent.loaded / progressEvent.total) * 100)
        }
      },
    })
    uploadPercent.value = 100
    ElMessage.success(res.data.message || '提交成功')
    submitVisible.value = false
    loadTasks()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '提交失败')
    uploadPercent.value = 0
  } finally { uploading.value = false }
}

async function openDetailDialog(task) {
  detailTask.value = task
  submissions.value = []
  unsubmittedList.value = []
  unsubmittedLoaded.value = false
  expandedMobile.value = {}
  detailActiveTab.value = 'submissions'
  detailVisible.value = true
  await loadSubmissions()
}

async function loadSubmissions() {
  if (!detailTask.value) return
  subLoading.value = true
  try {
    const res = await api.get(`/api/file-tasks/${detailTask.value.id}/submissions`)
    submissions.value = res.data
  } catch { ElMessage.error('加载提交记录失败') }
  finally { subLoading.value = false }
}

async function loadUnsubmitted() {
  if (!detailTask.value) return
  try {
    const res = await api.get(`/api/file-tasks/${detailTask.value.id}/unsubmitted`)
    unsubmittedList.value = res.data
    unsubmittedLoaded.value = true
  } catch { ElMessage.error('加载未提交名单失败') }
}

async function handleSendReminder() {
  if (!detailTask.value) return
  try {
    await ElMessageBox.confirm('确定向未提交学生发送邮件提醒吗？', '确认', { type: 'warning' })
  } catch { return }
  sendingReminder.value = true
  try {
    const { data } = await api.post(`/api/file-tasks/${detailTask.value.id}/send-email`)
    showMailResult(data)
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  } finally { sendingReminder.value = false }
}

async function handleQQNotify() {
  if (!detailTask.value) return
  try {
    await ElMessageBox.confirm('确定向 QQ 群发送该任务通知吗？', 'QQ群通知确认', { confirmButtonText: '发送', cancelButtonText: '取消', type: 'warning' })
  } catch { return }
  qqNotifyLoading.value = true
  try {
    const res = await api.post(`/api/qq/file-task/${detailTask.value.id}/notify`)
    ElMessage.success(res.data.message || 'QQ群通知已发送')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  } finally { qqNotifyLoading.value = false }
}

async function handleQQRemind() {
  if (!detailTask.value) return
  try {
    await ElMessageBox.confirm('将向所有未提交该任务的学生发送 QQ 私聊提醒。确定发送吗？', 'QQ私聊提醒确认', { confirmButtonText: '发送', cancelButtonText: '取消', type: 'warning' })
  } catch { return }
  qqRemindLoading.value = true
  try {
    const res = await api.post(`/api/qq/file-task/${detailTask.value.id}/remind`)
    ElMessage.success(`QQ私聊提醒完成：成功 ${res.data.sent || 0} 人，失败 ${res.data.failed || 0} 人`)
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  } finally { qqRemindLoading.value = false }
}

function openDownloadZip() {
  if (!detailTask.value) return
  downloadScope.value = { taskId: detailTask.value.id, baseName: `${detailTask.value.title}_提交文件` }
  downloadBusy.value = false
  downloadVisible.value = true
}

function openDownloadAllZip() {
  downloadScope.value = { taskId: null, baseName: '全部文件任务提交' }
  downloadBusy.value = false
  downloadVisible.value = true
}

async function startBatchDownload() {
  const scope = downloadScope.value
  if (!scope || downloadBusy.value) return
  downloadBusy.value = true
  try {
    const base = scope.taskId ? `/api/file-tasks/${scope.taskId}/download-zip` : '/api/file-tasks/download-all-zip'
    const { data: info } = await api.get(base + '-info', { params: { structure: downloadStructure.value } })
    if (!info.total_files) return ElMessage.warning('暂无可下载的文件')
    if (info.missing_files) ElMessage.warning(`有 ${info.missing_files} 条记录缺少原文件。将下载现存文件，并在 ZIP 中附上缺失清单，请核对备份或重新提交。`)
    await browserDownload(`${base}?structure=${downloadStructure.value}`)
    ElMessage.success('已交给浏览器下载完整 ZIP，可在浏览器下载列表查看进度')
    downloadVisible.value = false
  } catch (err) { showBlobError(err) }
  finally { downloadBusy.value = false }
}

function showBlobError(err) {
  if (err.response?.status === 404) {
    ElMessage.warning('暂无可下载的文件')
  } else {
    ElMessage.error(err.response?.data?.detail || '下载失败，请重试')
  }
}

async function downloadFile(sub) {
  try { await browserDownload(`/api/file-tasks/submissions/${sub.id}/download`) } catch (err) { showBlobError(err) }
}
async function downloadStudentZip(row) {
  try { await browserDownload(`/api/file-tasks/${detailTask.value.id}/students/${row.student_id}/download-zip`) } catch (err) { showBlobError(err) }
}

async function handleDeleteSubmission(id) {
  try {
    await ElMessageBox.confirm('确定删除该提交文件吗？', '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await api.delete(`/api/file-tasks/submissions/${id}`)
    ElMessage.success('删除成功')
    loadSubmissions()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '删除失败')
  }
}

async function handleDeleteStudentSubmissions(row) {
  try {
    await ElMessageBox.confirm('确定清空该学生在此任务的所有提交吗？', '清空确认', { type: 'warning' })
  } catch { return }
  try {
    const subs = submissions.value.filter(s => s.student_id === row.student_id)
    for (const s of subs) {
      await api.delete(`/api/file-tasks/submissions/${s.id}`)
    }
    ElMessage.success('清空成功')
    loadSubmissions()
  } catch (err) {
    ElMessage.error('清空失败')
  }
}

function toggleMobileExpand(studentId) {
  expandedMobile.value[studentId] = !expandedMobile.value[studentId]
}

function getStudentFiles(studentId) {
  return submissions.value.filter(s => s.student_id === studentId)
}

const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

onMounted(() => {
  window.addEventListener('resize', checkMobile)
  loadTasks()
  loadGroupProjects()
  timer = setInterval(() => { now.value = Date.now() }, 60000)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', checkMobile)
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.task-overview { display:flex; align-items:center; gap:24px; padding:24px; margin-bottom:20px; border:1px solid #d5e9e8; border-radius:14px; background:linear-gradient(120deg,#edf8f6,#f5f8fc); }
.task-overview strong { display:block; font-size:24px; color:#1d5360; margin-top:6px; }
.task-overview p { font-size:13px; line-height:1.8; color:#617e8a; margin:8px 0 0; }
.overview-label { color:#527784; font-size:12px; letter-spacing:2px; }
.overview-metric { margin-left:auto; text-align:center; min-width:70px; }
.overview-metric span { font-size:12px; color:#617e8a; }
.download-explanation { color:#627787; line-height:1.8; font-size:13px; }
.download-preparing { min-height:130px; padding-top:80px; text-align:center; color:#627787; }
@media(max-width:767px) { .task-overview { padding:18px; gap:12px; } .task-overview strong { font-size:20px; } }
/* 容器与卡片基底 */
.file-task-container {
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
  color: #1D2129;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

/* 移动端主列表卡片样式 */
.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mobile-task-card {
  border-radius: 8px;
  border: 1px solid #E5E6EB;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.mobile-task-card .task-title {
  font-weight: 600;
  font-size: 15px;
  color: #1D2129;
  flex: 1;
  margin-right: 12px;
  line-height: 1.4;
}

.mobile-task-card .task-desc {
  color: #86909C;
  font-size: 13px;
  margin: 0 0 12px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}

.mobile-task-card .meta-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: #4E5969;
}

.mobile-task-card .card-footer {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #F2F3F5;
  display: grid;
  gap: 10px;
}

/* PC 端操作按钮容器 */
.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.action-buttons .el-button {
  margin-left: 0 !important;
}

/* 详情弹窗顶部信息块 */
.task-detail-header {
  background-color: #F7F8FA;
  padding: 20px 24px;
  border-radius: 8px;
  margin-bottom: 24px;
}

.detail-title {
  margin: 0 0 12px 0;
  font-size: 18px;
  color: #1D2129;
  font-weight: 600;
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px 24px;
  color: #86909C;
  font-size: 13px;
  margin-bottom: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.detail-desc {
  color: #4E5969;
  line-height: 1.6;
  font-size: 14px;
  white-space: pre-wrap;
}

/* 提交记录明细 / 未提交名单 标题区 */
.section-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1D2129;
  padding-left: 4px;
}

/* PC 端展开的文件列表 */
.sub-file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid #F2F3F5;
}
.sub-file-item:last-child {
  border-bottom: none;
}
.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
.file-name {
  font-size: 13px;
  color: #1D2129;
  word-break: break-all;
}
.file-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* --- 移动端：子文件列表改造 --- */
.mobile-sub-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.mobile-sub-card {
  display: flex;
  flex-direction: column;
  background-color: #F7F8FA;
  border-radius: 8px;
  border: 1px solid #E5E6EB;
  overflow: hidden;
}

.mobile-sub-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  background: #fff;
}

.expand-icon {
  color: #86909C;
  transition: transform 0.3s;
}
.expand-icon.is-expanded {
  transform: rotate(90deg);
}

.sub-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sub-name {
  font-weight: 500;
  color: #1D2129;
  font-size: 15px;
}

.sub-id {
  color: #86909C;
  font-size: 13px;
  font-weight: normal;
}

.sub-time {
  font-size: 12px;
  color: #86909C;
}

.sub-files-list {
  background: #fff;
  border-top: 1px dashed #E5E6EB;
}

.sub-file-item-mobile {
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  border-bottom: 1px solid #F2F3F5;
  gap: 10px;
}

.sub-file-item-mobile:last-child {
  border-bottom: none;
}

.file-info-mobile {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.file-icon {
  margin-top: 2px;
  color: #165DFF;
}

.file-actions-mobile {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.file-btns {
  display: flex;
  gap: 8px;
}

.file-btns .el-button {
  margin-left: 0 !important;
}

/* 未提交名单区 */
.unsubmit-section {
  margin-top: 24px;
}

.empty-hint-box {
  color: #86909C;
  padding: 16px 0;
  text-align: center;
  background: #F7F8FA;
  border-radius: 6px;
  font-size: 13px;
}

.mobile-unsub-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
  padding-bottom: 10px;
}

.unsub-tag {
  font-size: 13px;
  padding: 6px 10px;
}

/* 学生提交区美化 */
.submit-task-info {
  background-color: #E8F3FF;
  border-radius: 6px;
  padding: 16px 20px;
  margin-bottom: 24px;
  color: #4E5969;
  font-size: 14px;
}

.info-row {
  margin-bottom: 8px;
  display: flex;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-row strong {
  color: #1D2129;
  flex-shrink: 0;
}

/* 占位符标签区 */
.tag-group {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.clickable-tag {
  cursor: pointer;
  user-select: none;
  padding: 6px 10px;
  height: auto;
}

.pattern-tip {
  font-size: 12px;
  color: #86909C;
  margin-top: 8px;
  line-height: 1.5;
}

/* 拖拽上传区域 */
:deep(.drag-upload .el-upload) {
  width: 100%;
}
:deep(.drag-upload .el-upload-dragger) {
  width: 100%;
  box-sizing: border-box;
  background-color: #F7F8FA;
  border-color: #E5E6EB;
  transition: all 0.3s;
}

:deep(.drag-upload .el-upload-dragger:hover) {
  background-color: #E8F3FF;
  border-color: #165DFF;
}

/* 进度条 */
.upload-progress-wrapper {
  margin-top: 20px;
  padding: 16px 20px;
  background: #F7F8FA;
  border-radius: 8px;
}
.progress-text {
  font-size: 13px;
  font-weight: 600;
  color: #1D2129;
}
.progress-hint {
  margin: 8px 0 0 0;
  font-size: 12px;
  color: #86909C;
  text-align: center;
}

/* 输入框高亮统一样式 */
:deep(.el-input__wrapper.is-focus),
:deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px #165DFF inset !important;
}
:deep(.custom-table::before),
:deep(.submission-table::before) {
  display: none;
}

/* 公用文字状态颜色 */
.deadline-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #4E5969;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 13px;
}
.deadline-icon { color: #165DFF; }
.is-expired { color: #F53F3F; }
.is-expired-text { color: #F53F3F; font-weight: 500; }
.id-text { font-family: -apple-system, BlinkMacSystemFont, sans-serif; color: #4E5969; }
.time-text { font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 13px; color: #86909C; }
.empty-text { color: #C9CDD4; font-size: 13px; }

/* ================= 移动端极致适配 ================= */
@media (max-width: 768px) {
  /* 顶部按钮铺满 */
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .header-actions {
    width: 100%;
    display: flex;
  }

  .header-actions .action-btn {
    flex: 1;
    margin-left: 0 !important;
  }

  /* 移动端任务卡片按钮：双列 Grid 排版完美对齐 */
  .mobile-task-card .card-footer {
    grid-template-columns: 1fr 1fr; 
  }
  
  .mobile-task-card .card-footer .el-button {
    width: 100%;
  }

  /* 弹窗内容流式重排 */
  .task-detail-header {
    padding: 16px;
  }

  .detail-meta {
    flex-direction: column;
    gap: 8px;
  }

  /* 二级操作栏（如下载全部、QQ通知）平铺 */
  .section-header-row {
    flex-direction: column;
    align-items: stretch;
  }
  
  .responsive-actions {
    width: 100%;
    display: flex;
    flex-wrap: wrap;
  }
  
  .responsive-actions .el-button {
    flex: auto;
    min-width: calc(33.33% - 8px);
    margin-bottom: 8px;
  }
  
  /* 弹窗底部操作按钮等宽铺满 */
  .dialog-footer {
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }
  .dialog-footer .el-button {
    flex: 1;
    margin-left: 0 !important;
  }

  /* 移除弹窗在手机上的 margin，彻底融入全屏 */
  :deep(.modern-dialog) {
    margin: 0 !important;
  }
  
  :deep(.modern-dialog .el-dialog__body) {
    padding: 10px 15px 20px;
  }
}

.author-qq {
  color: #86909C;
  font-size: 12px;
  margin-left: 4px;
}
</style>
