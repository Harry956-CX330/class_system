<template>
  <el-button plain size="small" @click="visible = true">安装应用</el-button>
  <el-dialog v-model="visible" title="把班务系统装到桌面" width="460px" append-to-body>
    <p>安装后可从桌面打开，使用当前账号登录。查看公告、填写问卷和上传文件需要联网。</p>
    <el-alert v-if="!secure" title="请先通过 HTTPS 访问本站，才能启用安装功能。" type="warning" :closable="false" />
    <p><strong>Android / 电脑：</strong>使用 Chrome 或 Edge，在浏览器菜单选择「安装应用」或「添加到主屏幕」。</p>
    <p><strong>iPhone / iPad：</strong>使用 Safari 打开本站，点击分享按钮，选择「添加到主屏幕」。</p>
    <template #footer><el-button @click="visible = false">关闭</el-button><el-button v-if="prompt" type="primary" @click="install">立即安装</el-button></template>
  </el-dialog>
</template>
<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
const visible = ref(false), prompt = ref(window.__installPrompt || null), secure = window.isSecureContext
function capture(event) { event.preventDefault(); prompt.value = event }
async function install() { await prompt.value.prompt(); await prompt.value.userChoice; prompt.value = null; window.__installPrompt = null; visible.value = false }
onMounted(() => window.addEventListener('beforeinstallprompt', capture))
onBeforeUnmount(() => window.removeEventListener('beforeinstallprompt', capture))
</script>
