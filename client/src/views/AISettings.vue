<template>
  <div class="ai-settings-page" v-loading="loading">
    <div class="settings-heading"><div><h2>AI 服务设置</h2><p>为班级启用公告解读、图片解题和系统操作问答。</p></div><el-tag>{{ model }}</el-tag></div>
    <el-alert title="仅系统管理员可配置密钥。API Key 只保存在服务器私密配置中，保存后不会回传到页面。" type="info" :closable="false" show-icon />
    <el-form label-position="top" @submit.prevent="save">
      <section class="settings-card">
        <h3>连接智谱</h3>
        <el-form-item label="启用 AI 问答"><el-switch v-model="form.enabled" /><span class="field-note">{{ configured ? '已保存 API Key' : '尚未配置 API Key' }}</span></el-form-item>
        <el-form-item label="智谱 API Key"><el-input v-model="form.api_key" type="password" show-password autocomplete="new-password" :disabled="form.clear_api_key" :placeholder="configured ? '留空保留已有密钥，填写则替换' : '填写智谱开放平台 API Key'" maxlength="512" /></el-form-item>
        <el-checkbox v-model="form.clear_api_key" @change="clearKeyChanged">删除已保存密钥并停用 AI</el-checkbox>
        <p class="field-note">固定使用 GLM-4.6V-Flash，通过智谱官方接口调用。公告仅在用户选择并发送问题时交给模型处理。</p>
      </section>
      <section class="settings-card">
        <h3>并发与调用限额</h3>
        <p class="field-note">2 核、2 GiB 服务器建议保持并发 1。每个账号同时只处理一个问题，满载时立即提示稍后重试，不积压请求。24 小时限额采用滚动窗口，服务重启后计数重置。</p>
        <div class="settings-grid">
          <el-form-item label="全站同时处理数"><el-input-number v-model="form.max_concurrent" :min="1" :max="2" :precision="0" /></el-form-item>
          <el-form-item label="每人最小提问间隔（秒）"><el-input-number v-model="form.min_interval_seconds" :min="2" :max="60" :precision="0" /></el-form-item>
          <el-form-item label="每人每分钟最多提问"><el-input-number v-model="form.user_per_minute" :min="1" :max="6" :precision="0" /></el-form-item>
          <el-form-item label="每人最近 24 小时最多提问"><el-input-number v-model="form.user_per_day" :min="1" :max="200" :precision="0" /></el-form-item>
          <el-form-item label="全站每分钟最多调用"><el-input-number v-model="form.global_per_minute" :min="1" :max="30" :precision="0" /></el-form-item>
          <el-form-item label="全站最近 24 小时最多调用"><el-input-number v-model="form.global_per_day" :min="1" :max="2000" :precision="0" /></el-form-item>
          <el-form-item label="调用超时（秒）"><el-input-number v-model="form.timeout_seconds" :min="15" :max="90" :precision="0" /></el-form-item>
          <el-form-item label="每次最大回答 Token 数"><el-input-number v-model="form.max_tokens" :min="512" :max="4096" :step="256" :precision="0" /></el-form-item>
        </div>
        <p class="field-note">限额包含已开始但失败的调用及连接测试。智谱侧限流会触发全站短暂冷却；系统不自动重试扣费请求。每次最多关联 3 条公告、共 4 张图片；图片压缩至每张 160 KiB 以内。</p>
      </section>
      <div class="settings-actions"><el-button type="primary" native-type="submit" :loading="saving" :disabled="testing">保存设置</el-button><el-button :loading="testing" :disabled="saving || form.clear_api_key" @click="saveAndTest">保存并测试连接</el-button><el-button @click="router.push('/ai')">前往 AI 问答</el-button></div>
      <el-alert v-if="feedback" :title="feedback" :type="feedbackType" :closable="false" class="feedback" show-icon />
    </el-form>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
const router = useRouter()
const model = 'GLM-4.6V-Flash'
const loading = ref(false), saving = ref(false), testing = ref(false), configured = ref(false)
const feedback = ref(''), feedbackType = ref('info')
const form = reactive({ enabled: false, api_key: '', clear_api_key: false, max_concurrent: 1, min_interval_seconds: 5, user_per_minute: 3, user_per_day: 40, global_per_minute: 12, global_per_day: 300, timeout_seconds: 60, max_tokens: 2048 })
function applySettings(data) {
  for (const key of Object.keys(form)) if (key in data && key !== 'api_key') form[key] = data[key]
  form.api_key = ''; form.clear_api_key = false; configured.value = data.configured
}
function showFeedback(text, type) { feedback.value = text; feedbackType.value = type }
function clearKeyChanged(value) { if (value) { form.enabled = false; form.api_key = '' } }
async function save() {
  if (saving.value) return false
  saving.value = true; feedback.value = ''
  try { const response = await api.put('/api/ai/settings', { ...form }); applySettings(response.data); showFeedback('AI 设置已保存', 'success'); return true }
  catch (error) { showFeedback(error.response?.data?.detail || '保存失败，请稍后重试', 'error'); return false }
  finally { saving.value = false }
}
async function saveAndTest() {
  if (testing.value || !await save()) return
  testing.value = true
  try { const response = await api.post('/api/ai/test'); showFeedback(response.data.message, 'success') }
  catch (error) { showFeedback(error.response?.data?.detail || '连接失败，请检查密钥和网络', 'error') }
  finally { testing.value = false }
}
onMounted(async () => {
  loading.value = true
  try { applySettings((await api.get('/api/ai/settings')).data) }
  catch (error) { showFeedback(error.response?.data?.detail || '无法加载 AI 设置', 'error') }
  finally { loading.value = false }
})
</script>

<style scoped>
.ai-settings-page { max-width: 1000px; margin: 0 auto; min-width: 0; }
.settings-heading { display: flex; gap: 16px; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
h2 { margin: 0 0 8px; font-size: 24px; } h3 { margin: 0 0 18px; font-size: 18px; }
.settings-heading p, .field-note { color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.8; }
.settings-heading p { margin: 0; }
.settings-card { background: var(--el-bg-color); border: 1px solid var(--el-border-color-lighter); border-radius: 16px; padding: 24px; margin-top: 20px; }
.settings-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px 24px; }
.settings-grid :deep(.el-input-number) { width: 100%; }
.field-note { margin: 8px 0 16px; } span.field-note { margin: 0 0 0 12px; }
.settings-actions { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 20px; }
.settings-actions :deep(.el-button + .el-button) { margin-left: 0; }
.feedback { margin-top: 16px; }
@media (max-width: 600px) { h2 { font-size: 21px; } .settings-heading { flex-direction: column; } .settings-card { padding: 18px 16px; } .settings-grid { grid-template-columns: minmax(0, 1fr); } }
</style>
