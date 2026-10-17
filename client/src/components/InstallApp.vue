<template>
  <el-button plain size="small" :loading="installing" @click="openInstall">{{ installed ? '安装说明' : '安装应用' }}</el-button>
  <el-dialog v-model="visible" title="把班务系统装到桌面" width="460px" append-to-body>
    <p v-if="installed">当前已在应用模式中打开，无需重复安装。</p>
    <p>安装后可从桌面打开，使用当前账号登录。查看公告、填写问卷和上传文件需要联网。</p>
    <el-alert v-if="!secure" title="请先通过 HTTPS 访问本站，才能启用安装功能。" type="warning" :closable="false" />
    <p v-if="!prompt">当前浏览器没有提供安装窗口。QQ、微信内请先选择「在浏览器打开」，再按以下方式安装。</p>
    <p><strong>Android / 电脑：</strong>使用 Chrome 或 Edge，在浏览器菜单选择「安装应用」或「添加到主屏幕」。若菜单没有安装项，请刷新页面后重试。</p>
    <p><strong>iPhone / iPad：</strong>使用 Safari 打开本站，点击分享按钮，选择「添加到主屏幕」。</p>
    <template #footer><el-button @click="copyAddress">复制网址</el-button><el-button @click="visible = false">关闭</el-button><el-button v-if="prompt" type="primary" :loading="installing" @click="install">立即安装</el-button></template>
  </el-dialog>
</template>
<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
const visible = ref(false), prompt = ref(window.__installPrompt || null), secure = window.isSecureContext
const installing = ref(false)
const installed = ref(window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true || window.Capacitor?.isNativePlatform?.() === true)
function capture(event) { event.preventDefault(); prompt.value = event }
function onInstalled() { installed.value = true; prompt.value = null; window.__installPrompt = null; visible.value = false }
function openInstall() {
  prompt.value = window.__installPrompt || prompt.value
  if (prompt.value && !installed.value) install()
  else visible.value = true
}
async function install() {
  const event = window.__installPrompt || prompt.value
  if (!event || installing.value) { visible.value = true; return }
  prompt.value = null; window.__installPrompt = null; installing.value = true
  try {
    await event.prompt()
    const choice = await event.userChoice
    if (choice?.outcome === 'accepted') { visible.value = false; ElMessage.success('已确认安装，请查看桌面应用') }
    else visible.value = true
  } catch { visible.value = true }
  finally { installing.value = false }
}
async function copyAddress() {
  try { await navigator.clipboard.writeText(window.location.origin); ElMessage.success('网址已复制') }
  catch { ElMessage.info('请复制浏览器地址栏中的网址') }
}
onMounted(() => { window.addEventListener('beforeinstallprompt', capture); window.addEventListener('appinstalled', onInstalled) })
onBeforeUnmount(() => { window.removeEventListener('beforeinstallprompt', capture); window.removeEventListener('appinstalled', onInstalled) })
</script>
