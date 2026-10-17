<template>
  <div class="survey-editor-container">
    <div class="editor-topbar">
      <el-button link :icon="ArrowLeft" @click="goBack">返回</el-button>
      <div class="topbar-actions">
        <el-button :icon="View" @click="previewVisible = true">预览</el-button>
        <el-button type="primary" :icon="Check" :loading="saving" @click="handleSave">发布</el-button>
      </div>
    </div>

    <div class="settings-panel">
      <div class="settings-toggle" @click="settingsOpen = !settingsOpen">
        <span class="toggle-title">
          <el-icon :class="{ rotated: settingsOpen }"><ArrowRight /></el-icon>
          问卷设置
        </span>
        <span class="toggle-summary" v-if="!settingsOpen">{{ form.title || '未命名问卷' }}</span>
      </div>
      <el-collapse-transition>
        <div v-show="settingsOpen" class="settings-body">
          <el-form 
            :model="form" 
            :label-width="isMobile ? 'auto' : '80px'" 
            :label-position="isMobile ? 'top' : 'right'"
            size="default"
          >
            <el-form-item label="问卷标题">
              <el-input v-model="form.title" placeholder="请输入问卷标题" />
            </el-form-item>
            <el-form-item label="问卷说明">
              <el-input v-model="form.description" type="textarea" :rows="3" placeholder="简要描述问卷目的（选填，支持换行）" />
            </el-form-item>
            <el-form-item label="截止时间">
              <el-date-picker
                v-model="form.deadline"
                type="datetime"
                value-format="YYYY-MM-DD HH:mm:ss"
                placeholder="不填则无截止时间限制"
                :style="isMobile ? 'width: 100%' : 'width: 260px;'"
                :editable="false"
              />
            </el-form-item>
            <el-divider style="margin: 12px 0;" />
            <el-form-item label="提交方式">
              <el-switch v-model="form.is_anonymous" active-text="匿名" inactive-text="实名" />
              <span class="setting-tip">匿名提交后，查看结果时不显示提交人姓名，但仍可看到未提交名单</span>
            </el-form-item>
            <el-form-item label="结果可见">
              <el-switch v-model="form.show_results" active-text="公布" inactive-text="不公布" />
              <span class="setting-tip">是否允许学生查看投票统计结果</span>
            </el-form-item>
            <el-form-item label="多次提交">
              <el-switch v-model="form.allow_multiple" active-text="允许多次" inactive-text="仅一次" />
              <span class="setting-tip">开启后，同一学生可多次提交问卷（每次提交覆盖上次）</span>
            </el-form-item>
          </el-form>
        </div>
      </el-collapse-transition>
    </div>

    <div class="question-toolbar">
      <el-button type="primary" :icon="Plus" @click="addQuestion('text')">添加题目</el-button>
      <el-divider direction="vertical" v-if="!isMobile" />
      <div class="type-btns">
        <el-button 
          v-for="t in questionTypes" :key="t.value"
          :type="'default'"
          plain
          size="small"
          @click="addQuestion(t.value)"
        >
          {{ t.icon }} {{ t.label }}
        </el-button>
      </div>
      <span class="toolbar-hint" v-if="form.questions.length === 0">点击上方按钮添加第一道题目</span>
      <span class="toolbar-hint" v-else>共 {{ form.questions.length }} 题 · 拖拽左侧手柄排序</span>
    </div>

    <div class="question-list" ref="questionListRef">
      <div
        v-for="(q, index) in form.questions"
        :key="q._key"
        class="question-card"
        :class="{ dragging: dragIndex === index }"
        draggable="true"
        @dragstart="onDragStart(index, $event)"
        @dragover.prevent="onDragOver(index, $event)"
        @dragend="onDragEnd"
        @drop="onDrop(index)"
      >
        <div class="card-drag-handle" title="拖拽排序">
          <el-icon><Rank /></el-icon>
        </div>

        <div class="card-body">
          <div class="q-title-row">
            <span class="q-number">{{ q.type_label || 'Q' + (index + 1) }}</span>
            <el-input
              v-model="q.question_text"
              placeholder="请输入题干内容"
              class="q-input"
              :class="{ 'is-empty': !q.question_text }"
            />
            <el-dropdown trigger="click" @command="(cmd) => handleQAction(cmd, index)">
              <el-button link class="q-more-btn"><el-icon><MoreFilled /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="copy"><el-icon><CopyDocument /></el-icon> 复制此题</el-dropdown-item>
                  <el-dropdown-item command="delete" divided><el-icon><Delete /></el-icon> 删除此题</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <div class="q-meta-row">
            <el-radio-group v-model="q.question_type" size="small" @change="onTypeChange(q)" class="mobile-wrap-group">
              <el-radio-button value="text">📝 文本</el-radio-button>
              <el-radio-button value="single">○ 单选</el-radio-button>
              <el-radio-button value="multiple">☑ 多选</el-radio-button>
              <el-radio-button value="rating">⭐ 评分</el-radio-button>
            </el-radio-group>
            <span class="q-type-hint">{{ getTypeHint(q.question_type) }}</span>
          </div>

          <div class="q-desc-row">
            <el-input
              v-model="q.description"
              placeholder="题目说明（选填，可补充填写注意事项等）"
              class="q-desc-input"
              size="small"
            />
          </div>

          <div v-if="q.question_type === 'single' || q.question_type === 'multiple'" class="q-options">
            <div class="options-header">
              <span class="options-label">选项列表</span>
              <span class="options-required">至少 2 个选项</span>
            </div>
            <div
              v-for="(opt, oi) in getOptions(q)"
              :key="oi"
              class="option-row"
            >
              <span class="option-letter">{{ String.fromCharCode(65 + oi) }}</span>
              <el-input
                v-model="q._options[oi]"
                :placeholder="'选项 ' + String.fromCharCode(65 + oi)"
                class="option-input"
                size="default"
              />
              <el-button
                v-if="getOptions(q).length > 2"
                link
                type="danger"
                :icon="Close"
                @click="removeOption(q, oi)"
              />
            </div>
            <el-button link type="primary" :icon="Plus" class="add-option-btn" @click="addOption(q)">
              {{ getOptions(q).some(o => !o) ? '' : '添加选项' }}
            </el-button>
          </div>

          <div v-if="q.question_type === 'rating'" class="q-rating-preview">
            <div class="rating-stars">
              <span v-for="i in 5" :key="i" class="star" :style="{ color: i <= 3 ? '#F7BA1E' : '#E5E6EB' }">★</span>
            </div>
            <span class="rating-hint">学生将看到 1-5 星评分</span>
          </div>
        </div>
      </div>

      <el-empty v-if="form.questions.length === 0" description="暂无题目，请使用上方工具栏添加" :image-size="80" />
    </div>

    <el-drawer
      v-model="previewVisible"
      title="问卷预览"
      direction="rtl"
      :size="isMobile ? '100%' : '420px'"
      :close-on-click-modal="true"
    >
      <div class="preview-survey">
        <h3 class="preview-title">{{ form.title || '未命名问卷' }}</h3>
        <p class="preview-desc" v-if="form.description" style="white-space: pre-wrap;">{{ form.description }}</p>
        <el-tag v-if="form.is_anonymous" size="small" type="info" style="margin-bottom: 12px;">匿名问卷</el-tag>

        <div v-for="(q, index) in form.questions" :key="q._key" class="preview-q">
          <div class="preview-q-num">{{ index + 1 }}. {{ q.question_text || '未命名题目' }}</div>
          <p v-if="q.description" class="preview-q-desc">{{ q.description }}</p>

          <el-input v-if="q.question_type === 'text'" disabled placeholder="请在此输入您的回答..." />

          <el-radio-group v-if="q.question_type === 'single'" disabled class="preview-options">
            <el-radio v-for="(opt, oi) in getOptions(q)" :key="oi" :value="oi" class="preview-option">
              {{ opt || '选项 ' + String.fromCharCode(65 + oi) }}
            </el-radio>
          </el-radio-group>

          <el-checkbox-group v-if="q.question_type === 'multiple'" disabled class="preview-options">
            <el-checkbox v-for="(opt, oi) in getOptions(q)" :key="oi" :value="oi" class="preview-option">
              {{ opt || '选项 ' + String.fromCharCode(65 + oi) }}
            </el-checkbox>
          </el-checkbox-group>

          <div v-if="q.question_type === 'rating'" class="preview-rating">
            <span v-for="i in 5" :key="i" class="preview-star" style="font-size: 28px; color: #E5E6EB; margin-right: 4px;">★</span>
          </div>
        </div>

        <el-empty v-if="form.questions.length === 0" description="暂无题目" :image-size="60" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, View, Check, Plus, Rank, MoreFilled, CopyDocument, Delete, Close, ArrowRight } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()
const route = useRoute()

const editId = route.query.id ? parseInt(route.query.id) : null

// 响应式状态
const isMobile = ref(false)

const form = reactive({
  title: '',
  description: '',
  deadline: '',
  is_anonymous: false,
  show_results: true,
  allow_multiple: false,
  questions: [],
})

const settingsOpen = ref(true)
const saving = ref(false)
const previewVisible = ref(false)
const dragIndex = ref(-1)
const questionListRef = ref(null)

const questionTypes = [
  { value: 'text', label: '文本题', icon: '📝' },
  { value: 'single', label: '单选题', icon: '○' },
  { value: 'multiple', label: '多选题', icon: '☑' },
  { value: 'rating', label: '评分题', icon: '⭐' },
]

const typeHints = {
  text: '学生将看到一个文本输入框',
  single: '学生单选一个选项',
  multiple: '学生可选择多个选项',
  rating: '学生给出 1-5 星评分',
}

let _keyCounter = 0
function nextKey() { return 'q_' + (++_keyCounter) }

// 监听窗口尺寸
const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  loadSurvey()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', checkMobile)
})

function initOptions(q) {
  if (!q._options) q._options = ['', '']
}

function getOptions(q) {
  initOptions(q)
  return q._options
}

function addOption(q) {
  initOptions(q)
  q._options.push('')
}

function removeOption(q, idx) {
  initOptions(q)
  if (q._options.length <= 2) return
  q._options.splice(idx, 1)
}

function getTypeHint(type) {
  return typeHints[type] || ''
}

function onTypeChange(q) {
  if (q.question_type === 'single' || q.question_type === 'multiple') {
    initOptions(q)
  }
}

function addQuestion(type) {
  const q = {
    _key: nextKey(),
    question_text: '',
    description: '',
    question_type: type,
  }
  if (type === 'single' || type === 'multiple') {
    initOptions(q)
  }
  // Set type label icon
  const t = questionTypes.find(x => x.value === type)
  q.type_label = t ? t.icon : 'Q'
  form.questions.push(q)
}

function handleQAction(cmd, index) {
  if (cmd === 'copy') {
    const orig = form.questions[index]
    const copy = JSON.parse(JSON.stringify(orig))
    copy._key = nextKey()
    form.questions.splice(index + 1, 0, copy)
    ElMessage.success('题目已复制')
  } else if (cmd === 'delete') {
    form.questions.splice(index, 1)
    ElMessage.success('题目已删除')
  }
}

// 拖拽排序
function onDragStart(index, e) {
  dragIndex.value = index
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', index)
}

function onDragOver(index, e) {
  e.dataTransfer.dropEffect = 'move'
}

function onDrop(targetIndex) {
  const fromIndex = dragIndex.value
  if (fromIndex === targetIndex) return
  const items = [...form.questions]
  const [moved] = items.splice(fromIndex, 1)
  items.splice(targetIndex, 0, moved)
  form.questions = items
}

function onDragEnd() {
  dragIndex.value = -1
}

function goBack() {
  router.push('/surveys')
}

async function handleSave() {
  if (!form.title.trim()) return ElMessage.warning('请输入问卷标题')
  if (form.questions.length === 0) return ElMessage.warning('请至少添加一道题目')
  
  // 验证选择题至少2个选项
  const invalidQ = form.questions.findIndex(q => {
    if (q.question_type === 'single' || q.question_type === 'multiple') {
      const opts = getOptions(q).filter(o => o.trim())
      return opts.length < 2
    }
    return false
  })
  if (invalidQ >= 0) {
    return ElMessage.warning(`第 ${invalidQ + 1} 题：选项类题目至少需要 2 个有效选项`)
  }

  saving.value = true
  try {
    const payload = {
      title: form.title,
      description: form.description,
      deadline: form.deadline || undefined,
      is_anonymous: form.is_anonymous,
      show_results: form.show_results,
      allow_multiple: form.allow_multiple,
      questions: form.questions.map(q => ({
        question_text: q.question_text,
        description: q.description || '',
        question_type: q.question_type,
        options: (q.question_type === 'single' || q.question_type === 'multiple')
          ? getOptions(q).filter(o => o.trim()).join(',')
          : '',
      })),
    }

    if (editId) {
      await api.put(`/api/surveys/${editId}`, payload)
      ElMessage.success('问卷已更新')
    } else {
      await api.post('/api/surveys', payload)
      ElMessage.success('问卷已发布')
    }
    router.push('/surveys')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function loadSurvey() {
  if (!editId) return
  try {
    const res = await api.get(`/api/surveys/${editId}`)
    const survey = res.data
    form.title = survey.title
    form.description = survey.description || ''
    form.deadline = survey.deadline ? survey.deadline.slice(0, 16).replace('T', ' ') : ''
    form.is_anonymous = survey.is_anonymous || false
    form.show_results = survey.show_results !== false
    form.allow_multiple = survey.allow_multiple || false
    form.questions = (survey.questions || []).map(q => {
      const item = {
        _key: nextKey(),
        question_text: q.question_text,
        description: q.description || '',
        question_type: q.question_type,
        _options: q.options ? q.options.split(',').map(s => s.trim()) : [],
      }
      if (item.question_type === 'single' || item.question_type === 'multiple') {
        if (item._options.length < 2) item._options = ['', '']
      }
      return item
    })
  } catch {
    ElMessage.error('加载问卷失败')
    router.push('/surveys')
  }
}
</script>

<style scoped>
.survey-editor-container {
  max-width: 820px;
  margin: 0 auto;
  padding: 16px 16px 60px;
  background: #fff;
  min-height: 100vh;
}

/* 顶部操作栏 */
.editor-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0 16px;
  border-bottom: 1px solid #E5E6EB;
  margin-bottom: 16px;
}

.topbar-actions {
  display: flex;
  gap: 10px;
}

/* 设置面板 */
.settings-panel {
  background: #F7F8FA;
  border-radius: 8px;
  margin-bottom: 16px;
  overflow: hidden;
}

.settings-toggle {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  gap: 8px;
}

.settings-toggle:hover {
  background: #EEF0F5;
}

.toggle-title {
  font-weight: 600;
  color: #1D2129;
  display: flex;
  align-items: center;
  gap: 4px;
}

.toggle-title .el-icon {
  transition: transform 0.2s;
  font-size: 14px;
}

.toggle-title .el-icon.rotated {
  transform: rotate(90deg);
}

.toggle-summary {
  margin-left: 12px;
  color: #86909C;
  font-size: 13px;
  /* 移动端文本过长防溢出 */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.settings-body {
  padding: 0 16px 16px;
}

.setting-tip {
  display: block;
  font-size: 12px;
  color: #86909C;
  margin-top: 4px;
  line-height: 1.5;
}

/* 题目工具栏 */
.question-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 0;
  flex-wrap: wrap;
}

.toolbar-hint {
  font-size: 13px;
  color: #86909C;
  margin-left: auto;
}

.type-btns {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* 题目卡片 */
.question-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.question-card {
  display: flex;
  background: #fff;
  border: 1px solid #E5E6EB;
  border-radius: 8px;
  transition: all 0.2s;
  overflow: hidden;
}

.question-card:hover {
  border-color: #165DFF;
  box-shadow: 0 2px 8px rgba(22, 93, 255, 0.08);
}

.question-card.dragging {
  opacity: 0.5;
  border-color: #165DFF;
  border-style: dashed;
}

.card-drag-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  background: #F7F8FA;
  cursor: grab;
  color: #C9CDD4;
  font-size: 18px;
  user-select: none;
  flex-shrink: 0;
}

.card-drag-handle:active {
  cursor: grabbing;
}

.card-body {
  flex: 1;
  padding: 16px;
  min-width: 0;
}

.q-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.q-number {
  font-size: 18px;
  font-weight: 600;
  color: #165DFF;
  flex-shrink: 0;
  min-width: 28px;
}

.q-input {
  flex: 1;
}

.q-input.is-empty :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #F7BA1E inset;
}

.q-more-btn {
  font-size: 18px;
  color: #C9CDD4;
  flex-shrink: 0;
}

.q-more-btn:hover {
  color: #4E5969;
}

.q-meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.q-type-hint {
  font-size: 12px;
  color: #86909C;
}

.q-desc-row {
  margin-bottom: 12px;
}

.q-desc-input :deep(.el-input__wrapper) {
  background: #F7F8FA;
  box-shadow: none;
}

/* 选项区 */
.q-options {
  background: #F7F8FA;
  border-radius: 6px;
  padding: 12px;
}

.options-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.options-label {
  font-size: 13px;
  font-weight: 600;
  color: #4E5969;
}

.options-required {
  font-size: 12px;
  color: #F53F3F;
}

.option-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.option-letter {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #165DFF;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.option-input {
  flex: 1;
}

.add-option-btn {
  margin-top: 4px;
}

/* 评分预览 */
.q-rating-preview {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}

.rating-stars {
  display: flex;
  gap: 2px;
}

.star {
  font-size: 24px;
}

.rating-hint {
  font-size: 13px;
  color: #86909C;
}

/* 预览面板 */
.preview-survey {
  padding: 0 12px;
}

.preview-title {
  font-size: 18px;
  font-weight: 700;
  color: #1D2129;
  margin: 0 0 8px;
}

.preview-desc {
  font-size: 14px;
  color: #4E5969;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #E5E6EB;
}

.preview-q {
  margin-bottom: 20px;
}

.preview-q-num {
  font-size: 15px;
  font-weight: 600;
  color: #1D2129;
  margin-bottom: 10px;
}

.preview-q-desc {
  font-size: 13px;
  color: #86909C;
  margin: 0 0 10px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.preview-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-option {
  margin: 0;
}

.preview-rating {
  display: flex;
  gap: 4px;
}

/* ================= 移动端响应式适配 ================= */
@media (max-width: 768px) {
  .survey-editor-container {
    padding: 12px 12px 40px;
  }

  /* 工具栏堆叠 */
  .question-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .type-btns {
    width: 100%;
    margin-top: 8px;
  }

  .toolbar-hint {
    display: none;
  }

  /* 题目卡片内边距收缩 */
  .card-body {
    padding: 12px;
  }

  .card-drag-handle {
    width: 28px;
    font-size: 16px;
  }

  .q-title-row {
    align-items: flex-start;
  }

  .q-number {
    margin-top: 6px;
  }

  /* 题型切换按钮换行 */
  .q-meta-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .mobile-wrap-group {
    display: flex;
    flex-wrap: wrap;
  }
  
  /* 选项调整 */
  .option-row {
    gap: 4px;
  }
  
  .option-letter {
    width: 24px;
    height: 24px;
    font-size: 12px;
  }
}
</style>