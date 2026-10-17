<template>
  <div class="survey-manage-container">
    <el-card class="page-card" shadow="never">
      <div class="page-header">
        <div class="header-left">
          <div class="title-indicator"></div>
          <h3 class="page-title">调查问卷</h3>
        </div>
        <el-button v-if="authStore.canViewAllData" type="primary" :icon="Plus" @click="$router.push('/survey-editor')" class="create-btn">
          创建问卷
        </el-button>
      </div>

      <div class="collection-toolbar">
        <el-input v-model="search" placeholder="搜索问卷标题" clearable aria-label="搜索问卷" />
        <el-radio-group v-model="statusFilter"><el-radio-button value="all">全部</el-radio-button><el-radio-button value="todo">待填写</el-radio-button><el-radio-button value="done">已填写</el-radio-button></el-radio-group>
        <span>{{ filteredSurveys.length }} 份问卷</span>
      </div>
      <el-table 
        v-if="!isMobile"
        :data="filteredSurveys"
        v-loading="loading" 
        style="width: 100%"
        :header-cell-style="{ background: '#F7F8FA', color: '#4E5969', fontWeight: '500' }"
        class="custom-table"
      >
        <el-table-column prop="title" label="问卷标题" min-width="160">
          <template #default="{ row }">
            <span class="survey-title">{{ row.title }}</span>
            <el-tag v-if="row.is_anonymous" size="small" type="info" effect="plain" style="margin-left: 6px; transform: scale(0.85);">匿名</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="问卷描述" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <RichContent class="survey-desc" :content="row.description || '暂无描述'" />
          </template>
        </el-table-column>
        <el-table-column label="截止时间" min-width="160">
          <template #default="{ row }">
            <div class="deadline-cell" :class="{ 'is-expired': isExpired(row.deadline) }">
              <el-icon class="deadline-icon"><Timer /></el-icon>
              <span>{{ row.deadline ? formatTime(row.deadline) : '无截止' }}</span>
              <el-tag v-if="isExpired(row.deadline)" size="small" type="danger" effect="dark" style="margin-left: 6px;">已截止</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="160">
          <template #default="{ row }">
            <span class="time-text">{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="author_name" label="发布人" min-width="140">
          <template #default="{ row }">
            <span>{{ row.author_name || '管理员' }}</span>
            <span v-if="row.author_qq" class="author-qq">QQ:{{ row.author_qq }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="authStore.canViewAllData" prop="response_count" label="回收数量" min-width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="success" effect="light" round>{{ row.response_count || 0 }} 份</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button v-if="authStore.canViewAllData" size="small" type="primary" link :icon="DataAnalysis" @click="openResultDialog(row)">
                结果分析
              </el-button>
              <el-button v-if="authStore.canViewAllData" size="small" type="info" link :icon="EditPen" @click="$router.push(`/survey-editor?id=${row.id}`)">
                编辑
              </el-button>
              <el-button v-if="authStore.canViewAllData" size="small" type="warning" link :icon="ChatDotSquare" :loading="qqNotifyMap[row.id]" @click="handleQQNotify(row)">
                QQ通知
              </el-button>
              <el-button v-if="!authStore.canViewAllData" size="small" type="primary" link :icon="EditPen" :disabled="isExpired(row.deadline) || (row.user_submitted && !row.allow_multiple)" @click="openFillDialog(row)">
                {{ row.user_submitted ? (row.allow_multiple ? '再次填写' : '已提交') : '填写问卷' }}
              </el-button>
              <el-button v-if="!authStore.canViewAllData && row.show_results" size="small" type="success" link :icon="DataAnalysis" @click="openStudentResult(row)">
                查看结果
              </el-button>
              <el-button v-if="authStore.canViewAllData" size="small" type="danger" link :icon="Delete" @click="handleDelete(row)">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="mobile-list" v-loading="loading">
        <el-card v-for="row in filteredSurveys" :key="row.id" class="mobile-survey-card" shadow="sm">
          <div class="card-header">
            <span class="survey-title">{{ row.title }}</span>
            <div class="card-tags">
              <el-tag v-if="row.is_anonymous" size="small" type="info" effect="plain" style="margin-right: 4px;">匿名</el-tag>
              <el-tag v-if="authStore.canViewAllData" size="small" type="success" effect="light" round>
                {{ row.response_count || 0 }} 份
              </el-tag>
            </div>
          </div>
          <div class="card-body">
            <RichContent class="survey-desc" :content="row.description || '暂无描述'" />
            <div class="meta-info">
              <div class="time-text">发布：{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</div>
              <div class="time-text" style="margin-top: 2px;">
                发布人：{{ row.author_name || '管理员' }}<template v-if="row.author_qq"> (QQ:{{ row.author_qq }})</template>
              </div>
              <div v-if="row.deadline" class="time-text" :class="{ 'is-expired': isExpired(row.deadline) }" style="margin-top: 4px;">
                <el-icon><Timer style="vertical-align: middle; margin-right: 2px;"/></el-icon> 
                截止：{{ formatTime(row.deadline) }}
                <el-tag v-if="isExpired(row.deadline)" size="small" type="danger" effect="dark" style="margin-left: 6px; transform: scale(0.9);">已截止</el-tag>
              </div>
            </div>
          </div>
          <div class="card-footer">
            <template v-if="authStore.canViewAllData">
              <el-button size="small" type="primary" plain :icon="DataAnalysis" @click="openResultDialog(row)">结果</el-button>
              <el-button size="small" type="info" plain :icon="EditPen" @click="$router.push(`/survey-editor?id=${row.id}`)">编辑</el-button>
              <el-button size="small" type="warning" plain :icon="ChatDotSquare" :loading="qqNotifyMap[row.id]" @click="handleQQNotify(row)">QQ群</el-button>
              <el-button size="small" type="danger" plain :icon="Delete" @click="handleDelete(row)">删除</el-button>
            </template>
            <template v-else>
              <el-button v-if="!authStore.canViewAllData" size="small" type="primary" plain :icon="EditPen" :disabled="isExpired(row.deadline) || (row.user_submitted && !row.allow_multiple)" @click="openFillDialog(row)">
                {{ row.user_submitted ? (row.allow_multiple ? '再次填写' : '已提交') : '填写' }}
              </el-button>
            <el-button v-if="!authStore.canViewAllData && row.show_results" size="small" type="success" plain :icon="DataAnalysis" @click="openStudentResult(row)">结果</el-button>
            </template>
          </div>
        </el-card>
        <el-empty v-if="surveys.length === 0" description="暂无问卷数据" />
      </div>
    </el-card>

    <el-dialog 
      v-model="fillVisible" 
      :title="currentSurvey?.title" 
      :width="isMobile ? '100%' : '650px'" 
      :fullscreen="isMobile"
      class="modern-dialog flex-dialog"
      destroy-on-close
    >
      <template v-if="currentSurvey">
        <div class="survey-progress" aria-live="polite"><span>已完成 {{ completedCount }} / {{ currentSurvey.questions.length }} 题 · 每题均需填写</span><el-progress :percentage="Math.round(completedCount / Math.max(1,currentSurvey.questions.length) * 100)" :show-text="false" /></div>
        <div class="dialog-scroll-body">
          <div class="survey-fill-header">
            <RichContent class="survey-fill-desc" :content="currentSurvey.description || '感谢您参与本次问卷调查。'" />
            <el-tag v-if="currentSurvey.is_anonymous" size="small" type="info" style="margin-top: 8px;">本问卷为匿名提交</el-tag>
          </div>
          <div class="survey-questions-wrapper">
            <div v-for="(q, index) in currentSurvey.questions" :key="index" class="fill-question-item" :id="`question-${index}`">
              <div class="fq-title">
                <span class="fq-index">{{ index + 1 }}.</span>
                <span class="fq-text">{{ q.question_text }}</span>
                <el-tag size="small" type="info" class="fq-type-tag">
                  {{ getTypeLabel(q.question_type) }}
                </el-tag>
              </div>
              <RichContent v-if="q.description" class="fq-desc" :content="q.description" />

              <div class="fq-answer-area">
                <el-input 
                  v-if="q.question_type === 'text'" 
                  v-model="answers[q.id || index]" 
                  type="textarea" 
                  :rows="3" 
                  placeholder="请输入您的回答..." 
                />
                <el-radio-group v-else-if="q.question_type === 'single'" v-model="answers[q.id || index]" class="vertical-group">
                  <el-radio v-for="(opt, oi) in getFillOptions(q)" :key="oi" :value="opt" class="option-item">{{ opt }}</el-radio>
                </el-radio-group>
                <el-checkbox-group v-else-if="q.question_type === 'multiple'" v-model="answers[q.id || index]" class="vertical-group">
                  <el-checkbox v-for="(opt, oi) in getFillOptions(q)" :key="oi" :value="opt" class="option-item">{{ opt }}</el-checkbox>
                </el-checkbox-group>
                <div v-else-if="q.question_type === 'rating'" class="fill-rating">
                  <el-rate v-model="answers[q.id || index]" :max="5" show-text />
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="fillVisible = false">取消</el-button>
          <el-button type="primary" :loading="filling" @click="handleSubmitFill">提交答卷</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog 
      v-model="resultVisible" 
      :title="`结果分析：${resultSurvey?.title}`" 
      :width="isMobile ? '100%' : '800px'" 
      :fullscreen="isMobile"
      class="modern-dialog flex-dialog"
    >
      <template v-if="resultSurvey">
        <div class="dialog-scroll-body">
          <div class="section-header-row">
            <span class="section-title" style="margin-bottom: 0;">问卷结果分析</span>
            <el-button type="success" :icon="Download" @click="exportVisible = true">导出Excel</el-button>
          </div>
          <div v-if="resultSurvey.questions.length === 0" class="empty-questions">暂无题目数据</div>
          <div v-for="(q, index) in resultSurvey.questions" :key="index" class="result-card">
            <div class="rq-header">
              <span class="rq-index">Q{{ index + 1 }}</span>
              <span class="rq-text">{{ q.question_text }}</span>
              <el-tag size="small" type="info">{{ getTypeLabel(q.question_type) }}</el-tag>
            </div>
            <RichContent v-if="q.description" class="rq-desc" :content="q.description" />
            <!-- 选项票数统计 -->
            <div v-if="hasVoteCounts(q)" class="vote-summary">
              <div class="vote-title">票数统计</div>
              <div v-for="(count, opt) in getVoteCounts(q)" :key="opt" class="vote-bar-row">
                <span class="vote-opt-name">{{ opt }}</span>
                <div class="vote-bar-track">
                  <div class="vote-bar-fill" :style="{ width: getVotePercent(q, count) + '%' }"></div>
                </div>
                <span class="vote-count-num">{{ count }} 票</span>
              </div>
            </div>
            
            <el-table 
              v-if="!isMobile"
              :data="getQuestionAnswers(q)" 
              style="width: 100%" 
              size="small"
              class="result-table"
              :header-cell-style="{ background: '#F7F8FA', color: '#4E5969' }"
            >
              <el-table-column prop="student_name" label="答卷人" min-width="100" />
              <el-table-column label="提交答案" min-width="200">
                <template #default="{ row: r }">
                  <template v-if="q.question_type === 'rating'">
                    <span v-for="i in 5" :key="i" style="color: #F7BA1E;">{{ i <= r.answer ? '★' : '☆' }}</span>
                    <span style="margin-left: 4px; color: var(--el-text-color-secondary); font-size: 12px;">{{ r.answer }} 分</span>
                  </template>
                  <template v-else>{{ r.answer }}</template>
                </template>
              </el-table-column>
              <el-table-column prop="submitted_at" label="提交时间" min-width="150">
                <template #default="{ row: r }">
                  <span class="time-text">{{ new Date(r.submitted_at).toLocaleString('zh-CN', { hour12: false }) }}</span>
                </template>
              </el-table-column>
              <template #empty>
                <span style="color: var(--el-text-color-secondary); font-size: 13px;">暂无人作答此题</span>
              </template>
            </el-table>

            <div v-else class="mobile-result-list">
              <div v-for="(ans, aIndex) in getQuestionAnswers(q)" :key="aIndex" class="mobile-result-item">
                <div class="mr-header">
                  <span class="mr-name">{{ ans.student_name }}</span>
                  <span class="mr-time">{{ new Date(ans.submitted_at).toLocaleString('zh-CN', { hour12: false }) }}</span>
                </div>
                <div class="mr-answer">
                  <template v-if="q.question_type === 'rating'">
                    <span v-for="i in 5" :key="i" style="color: #F7BA1E;">{{ i <= ans.answer ? '★' : '☆' }}</span>
                    <span style="margin-left: 4px; color: var(--el-text-color-secondary); font-size: 12px;">{{ ans.answer }} 分</span>
                  </template>
                  <template v-else>{{ ans.answer }}</template>
                </div>
              </div>
              <div v-if="getQuestionAnswers(q).length === 0" class="empty-questions" style="padding: 15px 0;">暂无人作答此题</div>
            </div>
          </div>

          <el-divider />
          <div class="section-header-row">
            <span class="section-title" style="margin-bottom: 0;">未填写名单</span>
            <div class="action-buttons responsive-actions">
              <el-button size="small" @click="loadUnanswered">刷新</el-button>
              <el-button size="small" type="warning" plain :icon="Message" :loading="sendingReminder" @click="handleSendReminder">
                邮件提醒
              </el-button>
              <el-button size="small" type="primary" plain :icon="ChatDotSquare" :loading="qqRemindLoading" @click="handleQQRemind">
                私聊提醒
              </el-button>
            </div>
          </div>
          <div v-if="unansweredList.length === 0" class="empty-questions" style="padding: 15px 0;">
            {{ unansweredLoaded ? '🎉 全部学生已填写' : '点击刷新查询最新进度' }}
          </div>
          
          <el-table v-else-if="!isMobile" :data="unansweredList" size="small" max-height="300">
            <el-table-column prop="real_name" label="姓名" min-width="100" />
            <el-table-column prop="student_id" label="学号" min-width="120" />
          </el-table>

          <div v-else class="mobile-unsub-tags">
            <el-tag 
              v-for="row in unansweredList" 
              :key="row.student_id" 
              type="info" 
              effect="plain"
              class="unsub-tag"
            >
              {{ row.real_name }} ({{ row.student_id }})
            </el-tag>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 学生端查看结果 -->
    <el-dialog 
      v-model="studentResultVisible" 
      :title="`投票结果：${resultSurvey?.title}`" 
      :width="isMobile ? '100%' : '600px'" 
      :fullscreen="isMobile"
      class="modern-dialog flex-dialog"
    >
      <template v-if="resultSurvey">
        <div class="dialog-scroll-body">
          <div v-for="(q, index) in resultSurvey.questions" :key="index" class="result-card">
            <div class="rq-header">
              <span class="rq-index">Q{{ index + 1 }}</span>
              <span class="rq-text">{{ q.question_text }}</span>
              <el-tag size="small" type="info">{{ getTypeLabel(q.question_type) }}</el-tag>
            </div>
            <div v-if="hasVoteCounts(q)" class="vote-summary">
              <div class="vote-title">票数统计</div>
              <div v-for="(count, opt) in getVoteCounts(q)" :key="opt" class="vote-bar-row">
                <span class="vote-opt-name">{{ opt }}</span>
                <div class="vote-bar-track">
                  <div class="vote-bar-fill" :style="{ width: getVotePercent(q, count) + '%' }"></div>
                </div>
                <span class="vote-count-num">{{ count }} 票</span>
              </div>
            </div>
            <div v-if="!hasVoteCounts(q)" class="empty-questions" style="padding: 12px 0;">
              {{ q.question_type === 'text' ? '文本题无统计数据' : (q.question_type === 'rating' ? '评分题暂无数据' : '暂无投票数据') }}
            </div>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 导出Excel选项对话框 -->
    <el-dialog 
      v-model="exportVisible" 
      title="导出问卷结果" 
      :width="isMobile ? '100%' : '480px'" 
      :fullscreen="isMobile"
      class="modern-dialog"
    >
      <el-form label-width="100px" label-position="top">
        <el-form-item label="排序方式">
          <el-radio-group v-model="exportSortBy">
            <el-radio value="student_id">按学号排序</el-radio>
            <el-radio value="submitted_at">按提交时间排序</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="排序方向">
          <el-radio-group v-model="exportSortOrder" :disabled="exportSortBy === 'submitted_at'">
            <el-radio value="asc">升序（从小到大）</el-radio>
            <el-radio value="desc">降序（从大到小）</el-radio>
          </el-radio-group>
          <div v-if="exportSortBy === 'submitted_at'" style="font-size: 12px; color: var(--el-text-color-secondary); margin-top: 4px;">
            按提交时间排序时，先提交的在前，未提交的排最后
          </div>
        </el-form-item>
        <el-form-item label="导出范围">
          <el-radio-group v-model="exportIncludeAll">
            <el-radio :value="false">仅导出已提交学生</el-radio>
            <el-radio :value="true">导出全部学生（含未提交）</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="exportVisible = false">取消</el-button>
          <el-button type="primary" :loading="exportLoading" @click="handleExport">导出Excel</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, EditPen, DataAnalysis, Message, Timer, ChatDotSquare, Download } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'
import { optionsList } from '../utils/richtext'
import { showMailResult } from '../utils/notifications'

const authStore = useAuthStore()
const surveys = ref([])
const loading = ref(false)
const search = ref(''), statusFilter = ref('all')
const filteredSurveys = computed(() => surveys.value.filter(s => s.title.includes(search.value.trim()) && (statusFilter.value === 'all' || (statusFilter.value === 'done' ? s.user_submitted : !s.user_submitted && !isExpired(s.deadline)))))
const completedCount = computed(() => Object.values(answers.value).filter(v => Array.isArray(v) ? v.length > 0 : String(v ?? '').trim() !== '' && v !== 0).length)

// 响应式状态探测
const isMobile = ref(false)

// 弹窗状态
const fillVisible = ref(false)
const filling = ref(false)
const resultVisible = ref(false)
const studentResultVisible = ref(false)

// 数据存储
const currentSurvey = ref(null)
const resultSurvey = ref(null)
const resultData = ref([])
const answers = ref({})

// 未填写名单
const unansweredList = ref([])
const unansweredLoaded = ref(false)
const sendingReminder = ref(false)
const qqNotifyMap = reactive({})
const qqRemindLoading = ref(false)

// 导出相关
const exportVisible = ref(false)
const exportSortBy = ref('student_id')
const exportSortOrder = ref('asc')
const exportIncludeAll = ref(false)
const exportLoading = ref(false)

// 监听窗口尺寸变化，判断是否为移动端
const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  loadSurveys()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', checkMobile)
})

function formatTime(t) {
  if (!t) return '无限制'
  return new Date(t).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}

function isExpired(deadline) {
  if (!deadline) return false
  return new Date() > new Date(deadline)
}

function getOptions(q) { return optionsList(q.options || q.options_str) }
function getFillOptions(q) { return getOptions(q) }

function getTypeLabel(type) {
  const map = { text: '简答', single: '单选', multiple: '多选', rating: '评分' }
  return map[type] || type
}

function hasVoteCounts(q) {
  if (q.question_type !== 'single' && q.question_type !== 'multiple') return false
  const found = resultData.value.find(item => item.id === (q.id || q.row_index))
  return found && found.vote_counts && Object.keys(found.vote_counts).length > 0
}

function getVoteCounts(q) {
  const found = resultData.value.find(item => item.id === (q.id || q.row_index))
  return found ? (found.vote_counts || {}) : {}
}

function getVotePercent(q, count) {
  const counts = getVoteCounts(q)
  const total = Object.values(counts).reduce((s, c) => s + c, 0)
  return total > 0 ? Math.round((count / total) * 100) : 0
}

function getQuestionAnswers(q) {
  // 新格式：resultData 的每项包含 id + details 数组
  const found = resultData.value.find(item => item.id === (q.id || q.row_index))
  if (found && found.details) {
    return found.details.map(d => ({
      student_name: d.student_name || '匿名用户',
      answer: d.answer,
      submitted_at: d.submitted_at,
    }))
  }
  // 兼容旧格式
  return resultData.value
    .filter(item => item.question_id === (q.id || q.row_index))
    .map(item => ({
      student_name: item.student_name,
      answer: Array.isArray(item.answer) ? item.answer.join(', ') : item.answer,
      submitted_at: item.submitted_at,
    }))
}

async function loadSurveys() {
  loading.value = true
  try {
    const res = await api.get('/api/surveys')
    surveys.value = res.data
  } catch {
    ElMessage.error('加载问卷失败')
  } finally {
    loading.value = false
  }
}

async function openFillDialog(row) {
  currentSurvey.value = { ...row }
  answers.value = Object.fromEntries(row.questions.map(q => [q.id, q.question_type === 'multiple' ? [] : q.question_type === 'rating' ? 0 : '']))
  fillVisible.value = true
}

async function handleSubmitFill() {
  if (filling.value) return
  const missing = currentSurvey.value.questions.findIndex(q => { const a = answers.value[q.id]; return Array.isArray(a) ? !a.length : !String(a ?? '').trim() || a === 0 })
  if (missing >= 0) {
    document.getElementById(`question-${missing}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    return ElMessage.warning(`请完成第 ${missing + 1} 题`)
  }

  filling.value = true
  try {
    const payload = {
      answers: Object.entries(answers.value).map(([questionId, answer]) => ({
        question_id: Number(questionId),
        answer_text: Array.isArray(answer) ? JSON.stringify(answer) : String(answer),
      })),
    }
    await api.post(`/api/surveys/${currentSurvey.value.id}/submit`, payload)
    ElMessage.success('答卷提交成功')
    fillVisible.value = false
    loadSurveys()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '提交失败')
  } finally {
    filling.value = false
  }
}

async function openResultDialog(row) {
  resultSurvey.value = row
  resultVisible.value = true
  unansweredLoaded.value = false
  unansweredList.value = []
  try {
    const res = await api.get(`/api/surveys/${row.id}/results`)
    const data = res.data
    resultData.value = data.questions || []
    resultSurvey.value.is_anonymous = data.is_anonymous
    resultSurvey.value.show_results = data.show_results
  } catch {
    ElMessage.error('加载结果失败')
  }
}

async function loadUnanswered() {
  if (!resultSurvey.value) return
  unansweredLoaded.value = false
  try {
    const res = await api.get(`/api/surveys/${resultSurvey.value.id}/unanswered`)
    unansweredList.value = res.data
    unansweredLoaded.value = true
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '加载失败')
  }
}

async function handleSendReminder() {
  if (!resultSurvey.value) return
  try {
    await ElMessageBox.confirm(
      '将向所有未填写该问卷的学生发送邮件提醒（分批发送，可能需要一些时间）。确定发送吗？',
      '邮件提醒确认',
      { confirmButtonText: '发送', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }
  sendingReminder.value = true
  try {
    const res = await api.post(`/api/surveys/${resultSurvey.value.id}/send-email`)
    showMailResult(res.data)
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '邮件发送失败')
  } finally {
    sendingReminder.value = false
  }
}

async function handleQQNotify(row) {
  try {
    await ElMessageBox.confirm(`确定向 QQ 群发送问卷「${row.title}」的通知吗？`, 'QQ群通知确认', {
      confirmButtonText: '发送', cancelButtonText: '取消', type: 'warning'
    })
  } catch { return }
  qqNotifyMap[row.id] = true
  try {
    const res = await api.post(`/api/qq/survey/${row.id}/notify`)
    ElMessage.success(res.data.message || 'QQ群通知已发送')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  } finally {
    qqNotifyMap[row.id] = false
  }
}

async function handleQQRemind() {
  if (!resultSurvey.value) return
  try {
    await ElMessageBox.confirm(
      '将向所有未填写该问卷的学生发送 QQ 私聊提醒。确定发送吗？',
      'QQ私聊提醒确认',
      { confirmButtonText: '发送', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }
  qqRemindLoading.value = true
  try {
    const res = await api.post(`/api/qq/survey/${resultSurvey.value.id}/remind`)
    const info = res.data
    ElMessage.success(`QQ私聊提醒完成：成功 ${info.sent || 0} 人，失败 ${info.failed || 0} 人`)
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  } finally {
    qqRemindLoading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除问卷 "${row.title}" 吗？删除后相关答卷数据将一并清除。`, '删除确认', { 
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消'
    })
    await api.delete(`/api/surveys/${row.id}`)
    ElMessage.success('删除成功')
    loadSurveys()
  } catch {}
}

async function handleExport() {
  if (!resultSurvey.value) return
  exportLoading.value = true
  try {
    const params = {
      sort_by: exportSortBy.value,
      sort_order: exportSortBy.value === 'submitted_at' ? 'asc' : exportSortOrder.value,
      include_all: exportIncludeAll.value,
    }
    const res = await api.get(`/api/surveys/${resultSurvey.value.id}/export`, {
      params,
      responseType: 'blob',
    })
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${resultSurvey.value.title}_问卷结果.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
    exportVisible.value = false
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '导出失败')
  } finally {
    exportLoading.value = false
  }
}

async function openStudentResult(row) {
  resultSurvey.value = row
  studentResultVisible.value = true
  try {
    const res = await api.get(`/api/surveys/${row.id}/student-results`)
    const data = res.data
    resultData.value = data.questions || []
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '加载结果失败')
  }
}
</script>

<style scoped>
/* 容器基底 */
.survey-manage-container {
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
  color: var(--el-text-color-primary);
}

/* --- 移动端卡片视图样式 --- */
.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mobile-survey-card {
  border-radius: 8px;
  border: 1px solid #E5E6EB;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.mobile-survey-card .survey-title {
  font-weight: 600;
  font-size: 15px;
  color: var(--el-text-color-primary);
  flex: 1;
  margin-right: 12px;
  line-height: 1.4;
  word-break: break-all;
}

.mobile-survey-card .survey-desc {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin: 0 0 12px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: pre-wrap;
  line-height: 1.5;
}

.mobile-survey-card .meta-info {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.mobile-survey-card .card-footer {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #F2F3F5;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.mobile-survey-card .card-footer .el-button {
  width: 100%;
  margin-left: 0 !important;
}

/* 表格内文字美化 */
.survey-title {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.survey-desc {
  color: var(--el-text-color-regular);
  font-size: 13px;
  white-space: pre-wrap;
}

.time-text {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.is-expired {
  color: #F53F3F;
}

.deadline-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.deadline-icon {
  color: var(--el-color-primary);
}

:deep(.custom-table::before) {
  display: none;
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

.section-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

/* 填写问卷样式 */
.survey-fill-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px dashed #E5E6EB;
}

.survey-fill-desc {
  color: var(--el-text-color-regular);
  line-height: 1.6;
  margin: 0;
  font-size: 14px;
  white-space: pre-wrap;
}

.fill-question-item {
  margin-bottom: 24px;
}

.fq-title {
  display: flex;
  align-items: flex-start;
  margin-bottom: 12px;
  line-height: 1.5;
}

.fq-index {
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-right: 8px;
  font-size: 15px;
}

.fq-text {
  font-weight: 500;
  color: var(--el-text-color-primary);
  font-size: 15px;
  margin-right: 8px;
  flex: 1;
}

.fq-type-tag {
  transform: scale(0.9);
  flex-shrink: 0;
  margin-top: 2px;
}

.fq-answer-area {
  padding-left: 20px;
}

.fq-desc {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin: 0 0 12px 20px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.fill-rating {
  padding: 4px 0;
}

/* 选项组垂直排版 */
.vertical-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-item {
  margin-right: 0;
  white-space: normal;
  height: auto;
  line-height: 1.4;
}

/* 结果弹窗样式 */
.result-card {
  background: var(--surface);
  border: 1px solid #E5E6EB;
  border-radius: 8px;
  margin-bottom: 20px;
  overflow: hidden;
}

.rq-header {
  background: var(--surface-soft);
  padding: 12px 16px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  border-bottom: 1px solid #E5E6EB;
}

.rq-index {
  font-weight: 600;
  color: var(--el-color-primary);
}

.rq-text {
  font-weight: 500;
  color: var(--el-text-color-primary);
  flex: 1;
}

.rq-desc {
  padding: 0 16px 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
  white-space: pre-wrap;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.result-table {
  border-top: none;
}

/* --- 移动端：结果分析专属组件 --- */
.mobile-result-list {
  display: flex;
  flex-direction: column;
}

.mobile-result-item {
  padding: 12px 16px;
  border-bottom: 1px solid #F2F3F5;
}

.mobile-result-item:last-child {
  border-bottom: none;
}

.mr-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.mr-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.mr-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.mr-answer {
  font-size: 14px;
  color: var(--el-text-color-regular);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all; /* 防止长字母/数字不换行 */
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
  padding: 4px 10px;
}

/* 票数统计柱状图 */
.vote-summary {
  background: var(--surface-soft);
  border-radius: 6px;
  padding: 12px 16px;
  margin: 0 0 12px 0;
}

.vote-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 10px;
}

.vote-bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.vote-opt-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-regular);
  min-width: 80px;
  flex-shrink: 0;
}

.vote-bar-track {
  flex: 1;
  height: 20px;
  background: #E5E6EB;
  border-radius: 4px;
  overflow: hidden;
}

.vote-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #165DFF, #4080FF);
  border-radius: 4px;
  min-width: 2px;
  transition: width 0.4s ease;
}

.vote-count-num {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-color-primary);
  min-width: 36px;
  text-align: right;
}

/* 统一弹窗内边距优化 */
:deep(.modern-dialog .el-dialog__body) {
  padding-top: 10px;
  padding-bottom: 20px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.dialog-footer .el-button {
  margin-left: 0 !important;
}

/* 全屏弹窗滚动结构优化 */
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
  padding: 15px 20px;
}

/* ================= 移动端响应式适配 ================= */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .create-btn {
    width: 100%;
  }

  .fq-answer-area {
    padding-left: 10px;
  }
  
  /* 弹窗全屏覆盖优化 */
  :deep(.modern-dialog) {
    margin: 0 !important;
    height: 100vh !important;
  }
  
  .dialog-scroll-body {
    padding: 15px;
  }

  .section-header-row {
    flex-direction: column;
    align-items: stretch;
  }
  
  .responsive-actions {
    width: 100%;
    display: flex;
    gap: 8px;
  }
  
  .responsive-actions .el-button {
    flex: 1;
    padding: 8px 0; /* 压缩内边距防止按钮拥挤 */
  }

  .dialog-footer {
    justify-content: space-between;
  }
  .dialog-footer .el-button {
    flex: 1;
  }
}

.author-qq {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-left: 4px;
}
</style>
