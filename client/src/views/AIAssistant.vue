<template>
  <div class="ai-page">
    <div class="ai-heading"><div><div class="eyebrow">班务 · 学习 · 公告</div><h2>AI 班务助手</h2><p>问操作、读公告，也能一起分析公告图片里的题目。</p></div><el-tag effect="plain">GLM-4.6V-Flash</el-tag></div>
    <el-alert v-if="statusLoaded && !status.enabled" title="AI 问答尚未启用，请联系系统管理员在「AI 服务设置」填写智谱 API Key 并启用。" type="info" :closable="false" show-icon />
    <el-alert v-if="statusError" :title="statusError" type="warning" :closable="false" show-icon />
    <section class="context-card">
      <div class="context-heading"><div><h3>本轮参考资料</h3><p>{{ selectedNotices.length ? `已关联 ${selectedNotices.length} 条公告` : '未关联公告，可直接询问系统操作' }} · 已选 {{ imageCount }} / 4 张图片</p></div><el-button :disabled="sending" @click="openContext">关联 / 导入公告</el-button></div>
      <div v-if="selectedNotices.length || importedText.trim() || importedImages.length" class="context-tags">
        <el-tag v-for="notice in selectedNotices" :key="notice.id" class="notice-chip" :closable="!sending" @close="removeNotice(notice.id)">#{{ notice.id }} {{ notice.title }}</el-tag>
        <el-tag v-if="importedText.trim()" type="info">导入公告文字</el-tag><el-tag v-if="importedImages.length" type="info">导入图片 {{ importedImages.length }} 张</el-tag>
      </div>
      <p class="privacy-note">点击发送时，问题、当前选择的公告正文 / 图片及最近对话会发给智谱处理。请勿输入密码、验证码或其他敏感资料。图片最多 4 张，每张压缩至 160 KiB。</p>
    </section>
    <section class="chat-card">
      <div class="chat-toolbar"><el-radio-group v-model="mode" :disabled="sending" aria-label="问答方式"><el-radio-button value="general">操作问答</el-radio-button><el-radio-button value="notice">公告解读</el-radio-button><el-radio-button value="exercise">图片解题</el-radio-button></el-radio-group><el-button :disabled="sending || !messages.length" @click="clearConversation">新对话</el-button></div>
      <div v-if="!messages.length" class="chat-welcome"><div class="welcome-mark">AI</div><h3>今天想了解什么？</h3><p>关联公告后，可以问“如何报名、要准备什么”，或选择图片询问某道题的解法。</p><div class="suggestions"><button v-for="prompt in suggestions" :key="prompt" type="button" @click="question = prompt">{{ prompt }}</button></div></div>
      <div v-else class="messages" role="log" aria-label="问答记录" aria-live="polite">
        <article v-for="(message, index) in messages" :key="index" class="message" :class="message.role"><div class="message-label">{{ message.role === 'user' ? '你' : '班务助手' }}</div><p class="message-text">{{ message.content }}</p><div v-if="message.sources?.length" class="answer-sources"><span>参考公告：</span><el-button v-for="source in message.sources" :key="source.id" link type="primary" @click="previewSource(source)">#{{ source.id }} {{ source.title }}（{{ source.images_used }} 张图）</el-button></div><p v-if="message.truncated" class="answer-note">回答已达到长度上限，可以继续追问某一步。</p></article>
      </div>
      <p v-if="sending" class="thinking" role="status">正在阅读资料并生成回答，请稍候…</p>
      <el-alert v-if="chatError" :title="chatError" type="warning" :closable="false" show-icon class="chat-error" />
      <el-form class="composer" @submit.prevent="sendQuestion"><el-input v-model="question" type="textarea" :rows="4" :maxlength="2000" show-word-limit resize="vertical" aria-label="你的问题" placeholder="例如：请根据这条公告告诉我报名入口、准备材料和具体步骤；或说明第 2 张图片第 3 题的解法。" :disabled="sending" /><div class="composer-actions"><span>{{ cooldown > 0 ? `${cooldown} 秒后可重试` : `每人每分钟 ${status.user_per_minute} 次，最近 24 小时 ${status.user_per_day} 次` }}</span><el-button type="primary" native-type="submit" :loading="sending" :disabled="!status.enabled || !question.trim() || cooldown > 0 || contextBusy || importing">{{ sending ? '正在回答' : '发送问题' }}</el-button></div></el-form>
      <p class="answer-note">AI 回答可能有误。题目先核对题干，报名与截止时间以原公告和主办方回执为准；AI 只提供指导，不代为报名或提交。对话仅保留在当前页面，刷新即清除。</p>
    </section>

    <el-dialog v-model="contextVisible" title="关联或导入公告" width="min(940px, calc(100vw - 24px))" :fullscreen="phone" class="ai-context-dialog" :close-on-click-modal="false">
      <div class="context-scroll">
        <el-tabs v-model="contextTab"><el-tab-pane label="系统通知公告" name="system"><div class="notice-search"><el-input v-model="search" maxlength="100" clearable placeholder="搜索公告标题" aria-label="搜索公告标题" @keyup.enter="searchNotices" /><el-button :loading="searching" @click="searchNotices">搜索公告</el-button></div><div class="notice-picker"><el-select v-model="pickedNotice" placeholder="选择公告（显示最近或搜索到的 30 条）" filterable aria-label="选择关联公告"><el-option v-for="item in noticeOptions" :key="item.id" :label="`#${item.id} ${item.title}`" :value="item.id" /></el-select><el-button type="primary" :loading="contextBusy" :disabled="!pickedNotice || selectedNotices.length >= 3" @click="addNotice(pickedNotice)">关联公告</el-button></div>
          <p class="field-hint">最多关联 3 条。正文随问题一起发送；点击下方图片勾选本次需要阅读的题目或报名说明，共限 4 张。未选中的图片不会交给 AI。</p>
          <div v-for="notice in selectedNotices" :key="notice.id" class="selected-notice"><div class="selected-heading"><h4>#{{ notice.id }} {{ notice.title }}</h4><el-button type="danger" link @click="removeNotice(notice.id)">移除</el-button></div><p>{{ notice.text_preview || '此公告主要包含图片或附件' }}</p><div class="notice-tools"><el-button link type="primary" @click="preview = notice">查看原公告</el-button><span>{{ notice.images.length }} 张图片，已选 {{ notice.images.filter(image => image.selected).length }} 张</span></div><div v-if="notice.images.length" class="image-grid"><label v-for="image in notice.images" :key="image.index" class="image-choice" :class="{ selected: image.selected }"><input type="checkbox" v-model="image.selected" :disabled="!image.selected && imageCount >= 4" :aria-label="`公告 ${notice.id} 第 ${image.index + 1} 张图片`" /><img :src="image.url" :alt="`公告第 ${image.index + 1} 张图片`" loading="lazy" /><span>第 {{ image.index + 1 }} 张</span></label></div></div><el-empty v-if="!selectedNotices.length" description="选择公告，AI 才能结合其正文和图片回答" :image-size="65" /></el-tab-pane>
          <el-tab-pane label="导入公告文字 / 图片" name="import"><p class="field-hint">可粘贴外部公告、导入 UTF-8 TXT，或添加公告截图 / 题目图片。不会发布到通知公告，也不会向其他用户展示。</p><el-input v-model="importedText" type="textarea" :rows="7" maxlength="10000" show-word-limit aria-label="导入公告文字" placeholder="在这里粘贴公告全文、报名说明或题目条件…" /><div class="import-actions"><el-button @click="textFile?.click()">导入 TXT</el-button><el-button :loading="importing" :disabled="imageCount >= 4" @click="imageFiles?.click()">导入公告图片</el-button><el-button v-if="importedText || importedImages.length" type="danger" plain @click="clearImport">清空导入</el-button></div><input ref="textFile" type="file" accept=".txt,text/plain" class="hidden-input" aria-label="导入 TXT 文件" @change="importTextFile" /><input ref="imageFiles" type="file" multiple accept="image/jpeg,image/png,image/webp" class="hidden-input" aria-label="导入公告图片文件" @change="importImageFiles" /><div class="image-grid"><div v-for="(image, index) in importedImages" :key="image.data_url" class="imported-image"><img :src="image.data_url" :alt="image.name" /><span>{{ image.name }}</span><el-button type="danger" link @click="importedImages.splice(index, 1)">移除</el-button></div></div></el-tab-pane></el-tabs>
      </div><template #footer><div class="context-footer"><span>{{ selectedNotices.length }} / 3 条公告 · {{ imageCount }} / 4 张图片</span><el-button type="primary" :disabled="importing || contextBusy" @click="contextVisible = false">完成关联</el-button></div></template>
    </el-dialog>
    <el-dialog :model-value="!!preview" :title="preview?.title || '公告原文'" width="min(740px, calc(100vw - 24px))" :fullscreen="phone" @close="preview = null"><div class="source-preview"><RichContent :content="preview?.content || ''" /></div><template #footer><el-button @click="preview = null">关闭原文</el-button></template></el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { prepareAiImage } from '../utils/aiImages'
const route = useRoute()
const status = ref({ enabled: false, user_per_minute: 3, user_per_day: 40 })
const statusLoaded = ref(false), statusError = ref(''), sending = ref(false), contextBusy = ref(false), chatError = ref(''), question = ref(''), mode = ref('general'), messages = ref([])
const selectedNotices = ref([]), importedText = ref(''), importedImages = ref([]), preview = ref(null)
const contextVisible = ref(false), contextTab = ref('system'), search = ref(''), noticeOptions = ref([]), pickedNotice = ref(null), searching = ref(false), importing = ref(false)
const textFile = ref(null), imageFiles = ref(null), cooldown = ref(0), phone = ref(window.innerWidth <= 600)
const imageCount = computed(() => importedImages.value.length + selectedNotices.value.reduce((count, notice) => count + notice.images.filter(image => image.selected).length, 0))
const suggestions = ['怎样提交文件任务，文件名要怎么写？', '请列出这条公告的报名步骤、材料和截止时间。', '请先核对所选图片题干，再讲解这道题的解法。']
const signature = computed(() => JSON.stringify({ ids: selectedNotices.value.map(item => [item.id, item.images.filter(image => image.selected).map(image => image.index)]), text: importedText.value, images: importedImages.value.map(image => image.data_url) }))
let disposed = false, searchToken = 0, cooldownTimer = null
const controller = new AbortController()
watch(signature, () => { if (messages.value.length) { messages.value = []; chatError.value = ''; ElMessage.info('参考资料已变更，已开始新对话') } })
function clearConversation() { messages.value = []; chatError.value = '' }
function removeNotice(id) { selectedNotices.value = selectedNotices.value.filter(item => item.id !== id) }
function clearImport() { importedText.value = ''; importedImages.value = [] }
function resize() { phone.value = window.innerWidth <= 600 }
async function searchNotices() {
  const token = ++searchToken; searching.value = true
  try { const response = await api.get('/api/ai/notices', { params: { q: search.value.trim() }, signal: controller.signal }); if (token === searchToken) noticeOptions.value = response.data }
  catch (error) { if (!disposed) ElMessage.error(error.response?.data?.detail || '公告搜索失败') }
  finally { if (token === searchToken) searching.value = false }
}
async function openContext() { contextVisible.value = true; if (!noticeOptions.value.length) await searchNotices() }
async function addNotice(id) {
  if (contextBusy.value || selectedNotices.value.some(item => item.id === Number(id))) return
  if (selectedNotices.value.length >= 3) return ElMessage.warning('最多关联 3 条公告')
  contextBusy.value = true
  try {
    const response = await api.get(`/api/ai/notices/${Number(id)}`, { signal: controller.signal })
    let remaining = 4 - imageCount.value
    const notice = { ...response.data, images: response.data.images.map(image => ({ ...image, selected: remaining-- > 0 })) }
    selectedNotices.value.push(notice); pickedNotice.value = null
    if (notice.images.some(image => !image.selected)) ElMessage.info('本次最多阅读 4 张图片，请勾选需要解读的图片')
    await api.post('/api/media-session', {}, { signal: controller.signal })
  } catch (error) { if (!disposed) ElMessage.error(error.response?.data?.detail || '无法关联公告') }
  finally { contextBusy.value = false }
}
async function importTextFile(event) {
  const file = event.target.files?.[0]; event.target.value = ''
  if (!file) return
  if (!/\.txt$/i.test(file.name) || file.size > 40 * 1024) return ElMessage.warning('请选择 40 KiB 以内的 UTF-8 TXT 文件')
  try { const text = await file.text(); if (text.length > 10000) throw new Error('公告文字不能超过 10000 字'); importedText.value = text }
  catch (error) { ElMessage.error(error.message || '文字读取失败') }
}
async function importImageFiles(event) {
  const files = [...(event.target.files || [])]; event.target.value = ''
  if (!files.length) return
  if (files.length > 4 - imageCount.value) return ElMessage.warning('系统公告图片与导入图片合计最多 4 张')
  importing.value = true
  try { for (const file of files) { const image = await prepareAiImage(file); if (!disposed) importedImages.value.push(image) } }
  catch (error) { ElMessage.error(error.message || '图片读取失败') }
  finally { importing.value = false }
}
async function previewSource(source) {
  const local = selectedNotices.value.find(item => item.id === source.id)
  if (local) { preview.value = local; return }
  try { preview.value = (await api.get(`/api/ai/notices/${source.id}`, { signal: controller.signal })).data; await api.post('/api/media-session', {}, { signal: controller.signal }) }
  catch (error) { if (!disposed) ElMessage.error(error.response?.data?.detail || '原公告已不存在') }
}
function startCooldown(seconds) {
  clearInterval(cooldownTimer); cooldown.value = Math.max(0, Math.min(86400, Number(seconds) || 0))
  if (cooldown.value) cooldownTimer = setInterval(() => { if (--cooldown.value <= 0) clearInterval(cooldownTimer) }, 1000)
}
async function sendQuestion() {
  if (sending.value || cooldown.value || !status.value.enabled || !question.value.trim() || contextBusy.value || importing.value) return
  if (mode.value === 'exercise' && !imageCount.value) { ElMessage.warning('请先关联公告并选择题目图片，或导入题目截图'); await openContext(); return }
  if (mode.value === 'notice' && !selectedNotices.value.length && !importedText.value.trim() && !importedImages.value.length) { ElMessage.warning('请先关联或导入需要解读的公告'); await openContext(); return }
  const currentQuestion = question.value.trim()
  const history = messages.value.slice(-8).map(item => ({ role: item.role, content: item.content.slice(0, 1400) }))
  const payload = { question: currentQuestion, mode: mode.value, notice_ids: selectedNotices.value.map(item => item.id), notice_images: selectedNotices.value.flatMap(notice => notice.images.filter(image => image.selected).map(image => ({ notice_id: notice.id, image_index: image.index }))), imported_text: importedText.value, imported_images: importedImages.value, history }
  sending.value = true; chatError.value = ''
  try {
    const response = await api.post('/api/ai/chat', payload, { signal: controller.signal })
    if (disposed) return
    messages.value.push({ role: 'user', content: currentQuestion }, { role: 'assistant', content: response.data.answer, sources: response.data.sources, truncated: response.data.truncated })
    if (messages.value.length > 20) messages.value.splice(0, 2)
    question.value = ''; startCooldown(status.value.min_interval_seconds)
  } catch (error) {
    if (!disposed) { chatError.value = error.response?.data?.detail || 'AI 请求失败，请稍后重试'; startCooldown(error.response?.headers?.['retry-after'] || (error.response?.status === 503 ? 5 : 0)) }
  } finally { sending.value = false }
}
onMounted(async () => {
  window.addEventListener('resize', resize)
  try { status.value = (await api.get('/api/ai/status', { signal: controller.signal })).data; statusLoaded.value = true }
  catch { if (!disposed) statusError.value = '无法读取 AI 服务状态，请刷新页面重试' }
  const id = Number(route.query.notice)
  if (Number.isInteger(id) && id > 0) { mode.value = 'notice'; contextVisible.value = true; await addNotice(id); await searchNotices() }
})
onBeforeUnmount(() => { disposed = true; controller.abort(); clearInterval(cooldownTimer); window.removeEventListener('resize', resize) })
</script>

<style scoped>
.ai-page { max-width: 1100px; min-width: 0; margin: 0 auto; }
.ai-heading, .context-heading, .chat-toolbar, .composer-actions, .context-footer, .selected-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; }
.ai-heading { margin-bottom: 22px; }.eyebrow { color: var(--el-color-primary); font-size: 12px; letter-spacing: 2px; margin-bottom: 8px; }h2 { margin: 0 0 10px; font-size: 26px; }h3 { margin: 0 0 8px; font-size: 17px; }
.ai-heading p, .context-heading p, .privacy-note, .field-hint, .answer-note { color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.8; margin: 0; }
.context-card, .chat-card { padding: 24px; background: var(--el-bg-color); border: 1px solid var(--el-border-color-lighter); border-radius: 16px; margin-top: 18px; min-width: 0; }
.context-heading .el-button { flex-shrink: 0; }.context-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }.notice-chip { height: auto; min-height: 28px; max-width: 100%; white-space: normal; overflow-wrap: anywhere; }.notice-chip :deep(.el-tag__content) { min-width: 0; }.privacy-note { font-size: 12px; margin-top: 14px; }
.chat-toolbar { align-items: center; flex-wrap: wrap; }.chat-welcome { padding: 36px 0; text-align: center; }.welcome-mark { margin: 0 auto 16px; border-radius: 18px; background: var(--el-color-primary-light-9); color: var(--el-color-primary); font-size: 24px; font-weight: 700; width: 62px; height: 62px; display: grid; place-items: center; }.chat-welcome p { color: var(--el-text-color-secondary); line-height: 1.8; font-size: 14px; }.suggestions { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-top: 22px; }.suggestions button { border: 1px solid var(--el-border-color); border-radius: 12px; padding: 12px 16px; color: var(--el-text-color-primary); background: var(--el-fill-color-light); cursor: pointer; text-align: left; line-height: 1.7; }
.messages { padding: 14px 0; }.message { padding: 18px; border-radius: 14px; margin: 16px 0; background: var(--el-fill-color-light); min-width: 0; }.message.user { background: var(--el-color-primary-light-9); margin-left: 8%; }.message-label { color: var(--el-color-primary); font-size: 12px; font-weight: 700; }.message-text { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 15px; line-height: 1.9; margin: 8px 0 0; }.answer-sources { display: flex; flex-wrap: wrap; gap: 6px 12px; border-top: 1px solid var(--el-border-color-lighter); padding-top: 12px; margin-top: 14px; font-size: 12px; }.answer-sources .el-button { height: auto; white-space: normal; text-align: left; line-height: 1.7; margin-left: 0; }.thinking { color: var(--el-color-primary); font-size: 14px; }.chat-error { margin: 16px 0; }.composer { margin-top: 18px; }.composer-actions { align-items: center; margin: 12px 0 16px; }.composer-actions span { font-size: 12px; color: var(--el-text-color-secondary); line-height: 1.7; }.composer-actions .el-button { flex-shrink: 0; }.answer-note { font-size: 12px; }
.context-scroll { max-height: 62dvh; overflow-y: auto; overscroll-behavior: contain; padding: 0 3px; }.notice-search, .notice-picker { display: flex; gap: 10px; margin-bottom: 14px; }.notice-picker .el-select { flex: 1; min-width: 0; }.notice-search .el-input { min-width: 0; }.field-hint { margin-bottom: 14px; }.selected-notice { border: 1px solid var(--el-border-color-lighter); border-radius: 12px; padding: 16px; margin-top: 16px; min-width: 0; }.selected-heading h4 { margin: 0; overflow-wrap: anywhere; }.selected-notice > p { font-size: 13px; line-height: 1.7; color: var(--el-text-color-secondary); overflow-wrap: anywhere; }.notice-tools { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; font-size: 12px; color: var(--el-text-color-secondary); }.image-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 14px; }.image-choice, .imported-image { display: flex; flex-direction: column; position: relative; min-width: 0; padding: 8px; border: 2px solid var(--el-border-color-lighter); border-radius: 10px; font-size: 12px; gap: 8px; overflow-wrap: anywhere; }.image-choice { cursor: pointer; }.image-choice.selected { border-color: var(--el-color-primary); background: var(--el-color-primary-light-9); }.image-choice input { position: absolute; top: 12px; left: 12px; width: 18px; height: 18px; accent-color: var(--el-color-primary); }.image-grid img { width: 100%; height: 110px; object-fit: contain; background: #fff; border-radius: 5px; }.import-actions { display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0; }.import-actions .el-button { margin-left: 0; }.hidden-input { display: none; }.context-footer { align-items: center; font-size: 13px; color: var(--el-text-color-secondary); }.source-preview { max-height: 68dvh; overflow: auto; overflow-wrap: anywhere; }
@media (max-width: 600px) { .ai-heading { flex-direction: column; gap: 10px; }h2 { font-size: 23px; }.context-card, .chat-card { padding: 18px 14px; }.context-heading { flex-direction: column; }.context-heading .el-button { width: 100%; }.chat-toolbar { gap: 12px; }.chat-toolbar :deep(.el-radio-button__inner) { padding: 9px 12px; }.chat-welcome { padding: 28px 0 18px; }.suggestions { flex-direction: column; }.message { padding: 14px; }.message-text { font-size: 14px; }.image-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }.context-scroll { max-height: calc(100dvh - 170px - env(safe-area-inset-top) - env(safe-area-inset-bottom)); }.composer-actions { align-items: flex-end; }.source-preview { max-height: 73dvh; } }
</style>
